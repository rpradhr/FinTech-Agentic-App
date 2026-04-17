"""
Fraud Detection Analyst Agent.

Inputs:  Transaction, customer profile, device/merchant history, prior alerts
Outputs: FraudAlert with risk score, evidence, explanation, recommended action
Gate:    Analyst approval required before any action (HUMAN_IN_THE_LOOP P0)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from app.core.ids import new_audit_id, new_fraud_id, new_session_id, new_trace_id
from app.domain.models import (
    FraudAlert,
    FraudEvidence,
    FraudRiskLevel,
    FraudStatus,
    Transaction,
)
from app.domain.models.fraud import RecommendedAction
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import (
    AuditRepository,
    CustomerRepository,
    FraudRepository,
    TraceRepository,
    TransactionRepository,
)
from .base import BaseAgent

logger = logging.getLogger(__name__)

FRAUD_SYSTEM_PROMPT = """You are a fraud detection analyst at a mid-size retail bank.
You analyze transaction events to identify suspicious patterns and generate structured risk assessments.

Your output MUST be a valid JSON object with these fields:
{
  "risk_score": <float 0.0-1.0>,
  "risk_level": <"low"|"medium"|"high"|"critical">,
  "reasons": [<string>, ...],
  "evidence": [
    {"evidence_type": <string>, "description": <string>, "confidence": <float>}
  ],
  "ring_indicators": [<string>, ...],
  "recommended_action": <"monitor"|"soft_block"|"manual_hold_review"|"hard_block"|"escalate_to_compliance">,
  "explanation": <string — human-readable rationale for an analyst>
}

Be specific. Cite actual values from the transaction data in your evidence.
If data is insufficient to assess risk, set risk_score below 0.3 and explain why.
"""


class FraudAgent(BaseAgent):
    """Fraud Detection Analyst — scores transactions and produces structured alerts."""

    name = "fraud_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
        fraud_repo: FraudRepository,
        transaction_repo: TransactionRepository,
        customer_repo: CustomerRepository,
    ) -> None:
        super().__init__(llm, retrieval, audit_repo, trace_repo)
        self._fraud = fraud_repo
        self._transactions = transaction_repo
        self._customers = customer_repo

    async def analyze_transaction(
        self, txn: Transaction, session_id: Optional[str] = None
    ) -> FraudAlert:
        """
        Analyze a single transaction and produce a FraudAlert.

        This is the main entry point — called by the ingestion handler and
        the supervisor when a transaction event arrives.
        """
        session_id = session_id or new_session_id()
        step = 0

        # 1. Gather context
        customer = await self._customers.get_by_id(txn.customer_id)
        recent_txns = await self._transactions.get_recent_by_customer(txn.customer_id, limit=20)
        device_txns = (
            await self._transactions.get_by_device(txn.device_id, limit=10)
            if txn.device_id
            else []
        )
        merchant_txns = (
            await self._transactions.get_by_merchant(txn.merchant, limit=10)
            if txn.merchant
            else []
        )
        prior_alerts = await self._fraud.get_similar_patterns(
            txn.customer_id, txn.device_id, txn.merchant
        )

        # 2. Retrieve relevant policy context
        policy_ctx = await self._retrieve_context(
            f"fraud detection rules for {txn.channel} transactions amount {txn.amount}",
            collection="fraud_policies",
        )

        # 3. Build LLM prompt
        context_block = self._build_context_block(
            txn, customer, recent_txns, device_txns, merchant_txns, prior_alerts, policy_ctx
        )

        messages = [
            Message(role="system", content=FRAUD_SYSTEM_PROMPT),
            Message(role="user", content=context_block),
        ]

        # 4. Call LLM
        raw_output = await self._complete(messages, session_id, step)
        step += 1

        # 5. Parse output
        assessment = self._parse_assessment(raw_output)

        # 6. Build FraudAlert
        alert = FraudAlert(
            alert_id=new_fraud_id(),
            txn_id=txn.txn_id,
            customer_id=txn.customer_id,
            account_id=txn.account_id,
            household_id=customer.household_id if customer else None,
            risk_score=assessment["risk_score"],
            risk_level=FraudRiskLevel.from_score(assessment["risk_score"]),
            reasons=assessment.get("reasons", []),
            evidence=[FraudEvidence(**e) for e in assessment.get("evidence", [])],
            ring_indicators=assessment.get("ring_indicators", []),
            recommended_action=assessment.get(
                "recommended_action", RecommendedAction.MANUAL_HOLD_REVIEW
            ),
            ai_explanation=assessment.get("explanation", ""),
            status=FraudStatus.PENDING_ANALYST_REVIEW,
        )

        # 7. Persist alert
        saved_alert = await self._fraud.save_alert(alert)

        # 8. Emit audit event
        await self._emit_audit(
            event_id=new_audit_id(),
            action="fraud_alert_created",
            actor_id=self.name,
            related_object_id=alert.alert_id,
            related_object_type="fraud_alert",
            customer_id=txn.customer_id,
            session_id=session_id,
            input_summary=f"Transaction {txn.txn_id} amount={txn.amount} channel={txn.channel}",
            output_summary=f"Risk={alert.risk_level} score={alert.risk_score:.2f} action={alert.recommended_action}",
        )

        logger.info(
            "Fraud alert created",
            extra={
                "alert_id": alert.alert_id,
                "txn_id": txn.txn_id,
                "risk_level": alert.risk_level,
            },
        )
        return saved_alert

    def _build_context_block(
        self,
        txn: Transaction,
        customer,
        recent_txns: list,
        device_txns: list,
        merchant_txns: list,
        prior_alerts: list,
        policy_ctx: str,
    ) -> str:
        parts = [
            "## Transaction Under Review",
            f"- ID: {txn.txn_id}",
            f"- Customer: {txn.customer_id}",
            f"- Account: {txn.account_id}",
            f"- Amount: {txn.amount} {txn.currency}",
            f"- Merchant: {txn.merchant or 'N/A'}",
            f"- Channel: {txn.channel}",
            f"- Device: {txn.device_id or 'N/A'}",
            f"- Geo: {txn.geo.model_dump() if txn.geo else 'N/A'}",
            f"- Timestamp: {txn.event_ts.isoformat()}",
        ]
        if customer:
            parts += [
                "\n## Customer Profile",
                f"- Risk tolerance: {customer.risk_tolerance}",
                f"- Products: {customer.products}",
                f"- KYC: {customer.kyc_status}",
                f"- Last sentiment: {customer.last_sentiment_status}",
            ]
        parts.append(f"\n## Recent Transactions (last {len(recent_txns)})")
        for t in recent_txns[:10]:
            parts.append(f"  - {t.txn_id}: {t.amount} via {t.channel} at {t.event_ts.isoformat()}")
        parts.append(f"\n## Device Transaction History (last {len(device_txns)})")
        for t in device_txns[:5]:
            parts.append(f"  - {t.txn_id}: {t.amount} customer={t.customer_id}")
        parts.append(f"\n## Merchant History (last {len(merchant_txns)})")
        for t in merchant_txns[:5]:
            parts.append(f"  - {t.txn_id}: {t.amount} customer={t.customer_id}")
        if prior_alerts:
            parts.append(f"\n## Prior Alerts on Customer ({len(prior_alerts)})")
            for a in prior_alerts[:3]:
                parts.append(f"  - {a.alert_id}: score={a.risk_score:.2f} status={a.status}")
        if policy_ctx:
            parts.append(f"\n## Relevant Policy Context\n{policy_ctx}")
        return "\n".join(parts)

    def _parse_assessment(self, raw: str) -> dict:
        """Extract JSON from LLM output — tolerates markdown fences."""
        try:
            # Strip markdown fences if present
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse fraud agent JSON output, using defaults")
            return {
                "risk_score": 0.5,
                "risk_level": "medium",
                "reasons": ["parsing_error"],
                "evidence": [],
                "ring_indicators": [],
                "recommended_action": "manual_hold_review",
                "explanation": f"AI output could not be parsed. Raw: {raw[:200]}",
            }

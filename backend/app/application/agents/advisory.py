"""
Financial Advisory Companion Agent.

Inputs:  Customer profile, goals, cash flow, holdings, sentiment signal, service cases
Outputs: AdviceDraft with next-best actions and explainable advice
Gate:    Advisor MUST approve before any customer delivery (HUMAN_IN_THE_LOOP P0)
"""
from __future__ import annotations

import json
import logging
from typing import Optional

from app.core.ids import new_audit_id, new_draft_id, new_session_id
from app.domain.models import AdviceDraft
from app.domain.models.advisory import AdviceCategory, AdviceDraftStatus, NextBestAction
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import (
    AdvisoryRepository,
    AuditRepository,
    CaseRepository,
    CustomerRepository,
    FraudRepository,
    LoanRepository,
    TraceRepository,
)
from .base import BaseAgent

logger = logging.getLogger(__name__)

ADVISORY_SYSTEM_PROMPT = """You are a financial advisor assistant at a retail bank.
Synthesize the customer's full context (profile, goals, balances, sentiment, open cases)
to generate explainable, suitable next-best actions.

Return ONLY a valid JSON object:
{
  "next_best_actions": [
    {
      "action_id": <string>,
      "category": <"savings"|"budgeting"|"product_fit"|"debt_management"|"investment"|"service_recovery"|"follow_up">,
      "title": <string>,
      "rationale": <string — grounded in customer data>,
      "evidence": [<string>, ...],
      "suggested_script": <string or null>,
      "priority": <int 1-10>,
      "suitability_flags": [<string>, ...]
    }
  ],
  "customer_context_summary": <string>,
  "goals_summary": <string>,
  "product_gaps": [<string>, ...],
  "service_sentiment_note": <string or null>,
  "suppress_cross_sell": <boolean>,
  "full_advice_text": <string — complete advisor script>
}

CRITICAL:
- If the customer has recent negative sentiment or open complaints, put service_recovery first
  and set suppress_cross_sell=true if churn risk > 0.5.
- Every rationale MUST reference specific customer data (amounts, dates, products).
- suitability_flags should list any potential compliance or suitability concerns.
"""


class AdvisoryAgent(BaseAgent):
    """Financial Advisory Companion — generates advice drafts for advisor review."""

    name = "advisory_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
        advisory_repo: AdvisoryRepository,
        customer_repo: CustomerRepository,
        fraud_repo: FraudRepository,
        loan_repo: LoanRepository,
        case_repo: CaseRepository,
    ) -> None:
        super().__init__(llm, retrieval, audit_repo, trace_repo)
        self._advisory = advisory_repo
        self._customers = customer_repo
        self._fraud = fraud_repo
        self._loans = loan_repo
        self._cases = case_repo

    async def generate_advice_draft(
        self, customer_id: str, advisor_id: Optional[str] = None, session_id: Optional[str] = None
    ) -> AdviceDraft:
        """
        Generate an advice draft for a customer. Requires advisor approval before delivery.
        """
        session_id = session_id or new_session_id()
        step = 0

        # 1. Gather full customer context
        customer = await self._customers.get_by_id(customer_id)
        if customer is None:
            raise ValueError(f"Customer {customer_id} not found")

        customer_signal = await self._customers.get_customer_signal(customer_id)
        fraud_alerts = await self._fraud.get_alerts_by_customer(customer_id, limit=3)
        open_cases = await self._cases.get_cases_by_customer(customer_id)
        open_loan_reviews = await self._loans.list_pending_reviews(limit=5)
        customer_loan_reviews = [r for r in open_loan_reviews if r.customer_id == customer_id]

        # 2. Retrieve suitability and product guidelines
        product_ctx = await self._retrieve_context(
            f"financial product suitability rules savings investment {customer.risk_tolerance}",
            collection="advisory_policies",
        )

        # 3. Build prompt
        context = self._build_prompt(
            customer, customer_signal, fraud_alerts, open_cases,
            customer_loan_reviews, product_ctx
        )
        messages = [
            Message(role="system", content=ADVISORY_SYSTEM_PROMPT),
            Message(role="user", content=context),
        ]

        # 4. Call LLM
        raw_output = await self._complete(messages, session_id, step)
        step += 1

        # 5. Parse
        result = self._parse_result(raw_output)

        # 6. Build NextBestActions
        nba_list = []
        for i, action_data in enumerate(result.get("next_best_actions", []), start=1):
            nba = NextBestAction(
                action_id=action_data.get("action_id", f"NBA-{i:03d}"),
                category=action_data.get("category", AdviceCategory.FOLLOW_UP),
                title=action_data.get("title", ""),
                rationale=action_data.get("rationale", ""),
                evidence=action_data.get("evidence", []),
                suggested_script=action_data.get("suggested_script"),
                priority=action_data.get("priority", 5),
                suitability_flags=action_data.get("suitability_flags", []),
            )
            nba_list.append(nba)

        # 7. Build draft
        draft = AdviceDraft(
            draft_id=new_draft_id(),
            customer_id=customer_id,
            advisor_id=advisor_id,
            next_best_actions=sorted(nba_list, key=lambda x: x.priority),
            customer_context_summary=result.get("customer_context_summary", ""),
            goals_summary=result.get("goals_summary", ""),
            product_gaps=result.get("product_gaps", []),
            service_sentiment_note=result.get("service_sentiment_note"),
            suppress_cross_sell=result.get("suppress_cross_sell", False),
            full_advice_text=result.get("full_advice_text", ""),
            status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
        )

        # 8. Persist
        saved_draft = await self._advisory.save_draft(draft)

        # 9. Audit
        await self._emit_audit(
            event_id=new_audit_id(),
            action="advice_draft_created",
            actor_id=self.name,
            related_object_id=draft.draft_id,
            related_object_type="advice_draft",
            customer_id=customer_id,
            session_id=session_id,
            output_summary=(
                f"NBAs={len(nba_list)} suppress_cross_sell={draft.suppress_cross_sell} "
                f"advisor={advisor_id}"
            ),
        )

        return saved_draft

    def _build_prompt(
        self, customer, signal, fraud_alerts, open_cases, loan_reviews, product_ctx
    ) -> str:
        parts = [
            "## Customer Profile",
            f"- ID: {customer.customer_id}",
            f"- Name: {customer.name}",
            f"- Risk tolerance: {customer.risk_tolerance}",
            f"- Products: {customer.products}",
            f"- Goals: {customer.goals}",
            f"- KYC: {customer.kyc_status}",
        ]
        if signal:
            parts += [
                "\n## Customer Signal",
                f"- Overall sentiment: {signal.overall_sentiment}",
                f"- Churn risk: {signal.churn_risk:.2f}",
                f"- Recent complaint drivers: {signal.recent_drivers}",
                f"- Suppress cross-sell: {signal.suppress_cross_sell}",
            ]
        if fraud_alerts:
            parts.append(f"\n## Active Fraud Alerts: {len(fraud_alerts)}")
            for a in fraud_alerts[:2]:
                parts.append(f"  - {a.alert_id}: risk={a.risk_score:.2f} status={a.status}")
        if open_cases:
            parts.append(f"\n## Open Cases: {len(open_cases)}")
            for c in open_cases[:3]:
                parts.append(f"  - {c.case_id} ({c.case_type}): {c.title}")
        if loan_reviews:
            parts.append(f"\n## Open Loan Applications: {len(loan_reviews)}")
            for r in loan_reviews[:2]:
                parts.append(f"  - {r.review_id}: {r.recommended_status}")
        if product_ctx:
            parts.append(f"\n## Suitability & Product Policy\n{product_ctx}")
        return "\n".join(parts)

    def _parse_result(self, raw: str) -> dict:
        try:
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse advisory agent output")
            return {
                "next_best_actions": [],
                "customer_context_summary": "Unable to parse AI output.",
                "goals_summary": "",
                "product_gaps": [],
                "service_sentiment_note": None,
                "suppress_cross_sell": False,
                "full_advice_text": "",
            }

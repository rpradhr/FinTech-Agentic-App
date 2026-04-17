"""
Loan Reviewer Agent.

Inputs:  LoanApplication, customer profile, linked documents, fraud signals
Outputs: LoanReview with missing docs, policy exceptions, recommended status
Gate:    Underwriter approval required before any decision (HUMAN_IN_THE_LOOP P0)
"""

from __future__ import annotations

import json
import logging

from app.core.ids import new_audit_id, new_review_id, new_session_id
from app.domain.models import (
    LoanApplication,
    LoanException,
    LoanReview,
    LoanStatus,
)
from app.domain.models.loan import PolicyExceptionSeverity
from app.infrastructure.ai.interfaces import LLMService, Message, RetrievalService
from app.infrastructure.persistence.interfaces import (
    AuditRepository,
    CustomerRepository,
    FraudRepository,
    LoanRepository,
    TraceRepository,
)

from .base import BaseAgent

logger = logging.getLogger(__name__)

LOAN_SYSTEM_PROMPT = """You are a senior loan underwriting analyst at a retail bank.
Review loan application data and produce a structured review pack for the underwriter.

Return ONLY a valid JSON object:
{
  "summary": <string — 2-3 sentence overview of the applicant and application>,
  "missing_documents": [<string>, ...],
  "exceptions": [
    {
      "exception_type": <string>,
      "description": <string>,
      "severity": <"info"|"warning"|"critical">,
      "rule_reference": <string or null>
    }
  ],
  "fraud_context_summary": <string or null>,
  "recommended_status": <"under_review"|"pending_documents"|"approved"|"conditionally_approved"|"declined">,
  "confidence_score": <float 0.0-1.0>,
  "explanation": <string — rationale for the underwriter>
}

Required documents for most personal loans: pay stubs, bank statements (3 months),
government-issued ID. Missing items should be listed precisely.
"""

REQUIRED_DOCS = {
    "personal": ["paystub", "bank_statement", "id_doc"],
    "auto": ["paystub", "id_doc"],
    "home": ["paystub", "bank_statement", "id_doc", "tax_return"],
    "business": ["tax_return", "business_financials", "id_doc"],
}


class LoanAgent(BaseAgent):
    """Loan Reviewer — produces structured review packs for underwriter decision."""

    name = "loan_agent"

    def __init__(
        self,
        llm: LLMService,
        retrieval: RetrievalService,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
        loan_repo: LoanRepository,
        customer_repo: CustomerRepository,
        fraud_repo: FraudRepository,
    ) -> None:
        super().__init__(llm, retrieval, audit_repo, trace_repo)
        self._loans = loan_repo
        self._customers = customer_repo
        self._fraud = fraud_repo

    async def review_application(
        self, application: LoanApplication, session_id: str | None = None
    ) -> LoanReview:
        """
        Review a loan application and produce a LoanReview awaiting underwriter decision.
        """
        session_id = session_id or new_session_id()
        step = 0

        # 1. Gather context
        customer = await self._customers.get_by_id(application.customer_id)
        fraud_alerts = await self._fraud.get_alerts_by_customer(application.customer_id, limit=5)
        customer_signal = await self._customers.get_customer_signal(application.customer_id)

        # 2. Deterministic missing-doc check (does not require LLM)
        required = REQUIRED_DOCS.get(application.loan_type, ["paystub", "id_doc"])
        submitted_lower = [d.lower() for d in application.submitted_docs]
        missing_docs = [r for r in required if r not in submitted_lower]

        # 3. Retrieve policy docs
        policy_ctx = await self._retrieve_context(
            f"loan policy rules {application.loan_type} income verification exceptions",
            collection="loan_policies",
        )

        # 4. Build prompt
        context = self._build_prompt(
            application, customer, fraud_alerts, customer_signal, missing_docs, policy_ctx
        )
        messages = [
            Message(role="system", content=LOAN_SYSTEM_PROMPT),
            Message(role="user", content=context),
        ]

        # 5. Call LLM
        raw_output = await self._complete(messages, session_id, step)
        step += 1

        # 6. Parse
        result = self._parse_result(raw_output)

        # 7. Merge deterministic missing docs with LLM-detected ones
        all_missing = list(dict.fromkeys(missing_docs + result.get("missing_documents", [])))

        # 8. Persist exceptions
        exceptions = []
        for exc_data in result.get("exceptions", []):
            from app.core.ids import new_id

            exc = LoanException(
                exception_id=new_id("EXC-"),
                application_id=application.application_id,
                exception_type=exc_data.get("exception_type", "unknown"),
                description=exc_data.get("description", ""),
                severity=exc_data.get("severity", PolicyExceptionSeverity.WARNING),
                rule_reference=exc_data.get("rule_reference"),
            )
            await self._loans.save_exception(exc)
            exceptions.append(exc)

        # 9. Build review
        review = LoanReview(
            review_id=new_review_id(),
            application_id=application.application_id,
            customer_id=application.customer_id,
            summary=result.get("summary", ""),
            missing_documents=all_missing,
            exceptions=exceptions,
            fraud_context_summary=result.get("fraud_context_summary"),
            recommended_status=result.get("recommended_status", LoanStatus.UNDER_REVIEW),
            confidence_score=result.get("confidence_score", 0.5),
            ai_explanation=result.get("explanation", ""),
        )

        # 10. Persist review
        saved_review = await self._loans.save_review(review)

        # 11. Update application status
        if all_missing:
            await self._loans.update_application_status(
                application.application_id, LoanStatus.PENDING_DOCUMENTS
            )
        else:
            await self._loans.update_application_status(
                application.application_id, LoanStatus.UNDER_REVIEW
            )

        # 12. Audit
        await self._emit_audit(
            event_id=new_audit_id(),
            action="loan_review_created",
            actor_id=self.name,
            related_object_id=review.review_id,
            related_object_type="loan_review",
            customer_id=application.customer_id,
            session_id=session_id,
            input_summary=f"Application {application.application_id} type={application.loan_type}",
            output_summary=(
                f"Missing={len(all_missing)} exceptions={len(exceptions)} "
                f"recommended={review.recommended_status}"
            ),
        )

        return saved_review

    def _build_prompt(
        self, application, customer, fraud_alerts, customer_signal, missing_docs, policy_ctx
    ) -> str:
        parts = [
            "## Loan Application",
            f"- ID: {application.application_id}",
            f"- Type: {application.loan_type}",
            f"- Requested: {application.requested_amount}",
            f"- Term: {application.term_months} months",
            f"- Stated income: {application.stated_income}",
            f"- Employment: {application.stated_employment or 'N/A'}",
            f"- Credit score: {application.credit_score or 'N/A'}",
            f"- Submitted docs: {application.submitted_docs}",
            f"- DTI (estimated): {application.requested_amount / max(application.stated_income, 1):.2f}",
        ]
        if missing_docs:
            parts.append(f"\n## Deterministically Detected Missing Documents: {missing_docs}")
        if customer:
            parts += [
                "\n## Customer Profile",
                f"- Risk tolerance: {customer.risk_tolerance}",
                f"- Products: {customer.products}",
                f"- KYC: {customer.kyc_status}",
            ]
        if fraud_alerts:
            parts.append(f"\n## Fraud Alerts ({len(fraud_alerts)} total)")
            for a in fraud_alerts[:3]:
                parts.append(f"  - {a.alert_id}: score={a.risk_score:.2f} status={a.status}")
        if customer_signal:
            parts += [
                "\n## Customer Sentiment Signal",
                f"- Churn risk: {customer_signal.churn_risk:.2f}",
                f"- Recent drivers: {customer_signal.recent_drivers}",
            ]
        if policy_ctx:
            parts.append(f"\n## Policy Context\n{policy_ctx}")
        return "\n".join(parts)

    def _parse_result(self, raw: str) -> dict:
        try:
            text = raw.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1] if lines[-1].startswith("```") else lines[1:])
            return json.loads(text)
        except Exception:
            logger.warning("Failed to parse loan agent output")
            return {
                "summary": "Unable to parse AI output.",
                "missing_documents": [],
                "exceptions": [],
                "fraud_context_summary": None,
                "recommended_status": "under_review",
                "confidence_score": 0.5,
                "explanation": f"Parse error. Raw: {raw[:200]}",
            }

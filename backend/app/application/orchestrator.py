"""
Supervisor Orchestrator.

Routes incoming events to the appropriate specialist agent, enforces
policy guardrails (e.g., no autonomous action without human approval),
assembles shared customer context, and manages inter-agent handoffs.

Design pattern: supervisor-orchestrated, specialist-agent model (PRD §5).
"""
from __future__ import annotations

import logging
from typing import Optional

from app.application.agents import (
    AdvisoryAgent,
    BranchAgent,
    FraudAgent,
    LoanAgent,
    SentimentAgent,
)
from app.core.container import Container
from app.core.ids import new_audit_id, new_session_id
from app.domain.models import (
    Case,
    CaseType,
    FraudAlert,
    Interaction,
    LoanApplication,
    LoanReview,
    Transaction,
)
from app.domain.models.case import CasePriority, CaseStatus
from app.domain.models.fraud import FraudRiskLevel
from app.domain.models.interaction import SentimentLabel
from app.infrastructure.persistence.interfaces import (
    AuditRepository,
    CaseRepository,
    TraceRepository,
)

logger = logging.getLogger(__name__)


class Supervisor:
    """
    Central orchestration point.

    Responsibilities:
    - Route events to the correct agent
    - Assemble shared context before agent invocation
    - Open/link Cases when alerts are created
    - Trigger inter-agent handoffs based on signal thresholds
    - Enforce HUMAN_IN_THE_LOOP — no autonomous fraud/loan/advisory actions
    """

    def __init__(
        self,
        fraud_agent: FraudAgent,
        sentiment_agent: SentimentAgent,
        loan_agent: LoanAgent,
        branch_agent: BranchAgent,
        advisory_agent: AdvisoryAgent,
        case_repo: CaseRepository,
        audit_repo: AuditRepository,
        trace_repo: TraceRepository,
    ) -> None:
        self._fraud = fraud_agent
        self._sentiment = sentiment_agent
        self._loan = loan_agent
        self._branch = branch_agent
        self._advisory = advisory_agent
        self._cases = case_repo
        self._audit = audit_repo
        self._traces = trace_repo

    # ─────────────────────────────────────────────────────────────────────────
    # Transaction ingestion → Fraud Agent
    # ─────────────────────────────────────────────────────────────────────────

    async def process_transaction(
        self, txn: Transaction
    ) -> Optional[FraudAlert]:
        """
        Entry point for transaction events.
        Only creates a fraud alert; does NOT take any action autonomously.
        """
        session_id = new_session_id()
        logger.info("Supervisor: processing transaction %s", txn.txn_id)

        alert = await self._fraud.analyze_transaction(txn, session_id=session_id)

        if alert.risk_level in (FraudRiskLevel.HIGH, FraudRiskLevel.CRITICAL):
            await self._open_case(
                case_type=CaseType.FRAUD,
                title=f"Fraud alert: {alert.alert_id} — risk={alert.risk_level}",
                customer_id=txn.customer_id,
                linked_id=alert.alert_id,
                priority=(
                    CasePriority.CRITICAL
                    if alert.risk_level == FraudRiskLevel.CRITICAL
                    else CasePriority.HIGH
                ),
            )

        return alert

    # ─────────────────────────────────────────────────────────────────────────
    # Interaction ingestion → Sentiment Agent → optional Advisory handoff
    # ─────────────────────────────────────────────────────────────────────────

    async def process_interaction(self, interaction: Interaction) -> None:
        """
        Entry point for customer interactions (calls, emails, complaints).
        Runs sentiment analysis and may trigger an advisory handoff.
        """
        session_id = new_session_id()
        logger.info("Supervisor: processing interaction %s", interaction.interaction_id)

        analysis = await self._sentiment.analyze_interaction(interaction, session_id=session_id)

        # Open a case if escalation is recommended
        if analysis.escalation_recommended:
            await self._open_case(
                case_type=CaseType.COMPLAINT,
                title=f"Escalation: {analysis.analysis_id} — {analysis.sentiment}",
                customer_id=interaction.customer_id,
                linked_id=analysis.analysis_id,
                priority=CasePriority.HIGH if analysis.churn_risk > 0.7 else CasePriority.MEDIUM,
            )

    # ─────────────────────────────────────────────────────────────────────────
    # Loan application → Loan Agent
    # ─────────────────────────────────────────────────────────────────────────

    async def process_loan_application(
        self, application: LoanApplication
    ) -> LoanReview:
        """
        Entry point for loan application submissions.
        Review is created; underwriter must still make the final decision.
        """
        session_id = new_session_id()
        logger.info("Supervisor: processing loan application %s", application.application_id)

        review = await self._loan.review_application(application, session_id=session_id)

        await self._open_case(
            case_type=CaseType.LOAN_REVIEW,
            title=f"Loan review: {review.review_id}",
            customer_id=application.customer_id,
            linked_id=review.review_id,
            priority=CasePriority.MEDIUM,
        )
        return review

    # ─────────────────────────────────────────────────────────────────────────
    # Branch KPI refresh → Branch Agent
    # ─────────────────────────────────────────────────────────────────────────

    async def analyze_branch(self, branch_id: str):
        """
        Triggered by scheduler or anomaly threshold breach.
        """
        session_id = new_session_id()
        logger.info("Supervisor: analyzing branch %s", branch_id)
        return await self._branch.analyze_branch(branch_id, session_id=session_id)

    # ─────────────────────────────────────────────────────────────────────────
    # Advisor workspace open → Advisory Agent
    # ─────────────────────────────────────────────────────────────────────────

    async def generate_advice(
        self, customer_id: str, advisor_id: Optional[str] = None
    ):
        """
        Entry point when an advisor opens a customer workspace.
        Draft is created; advisor must approve before any delivery.
        """
        session_id = new_session_id()
        logger.info("Supervisor: generating advice for customer %s", customer_id)
        return await self._advisory.generate_advice_draft(
            customer_id, advisor_id=advisor_id, session_id=session_id
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────

    async def _open_case(
        self,
        case_type: CaseType,
        title: str,
        customer_id: Optional[str],
        linked_id: str,
        priority: CasePriority = CasePriority.MEDIUM,
    ) -> Case:
        from app.core.ids import new_case_id
        case = Case(
            case_id=new_case_id(),
            case_type=case_type,
            status=CaseStatus.OPEN,
            priority=priority,
            title=title,
            customer_id=customer_id,
            linked_entity_ids=[linked_id],
            linked_entity_types=[case_type.value],
        )
        saved = await self._cases.save(case)
        logger.info("Case opened: %s (%s)", saved.case_id, case_type)
        return saved


def build_supervisor(container: Container) -> Supervisor:
    """Wire all agents and return a ready Supervisor."""
    fraud_agent = FraudAgent(
        llm=container.llm,
        retrieval=container.retrieval,
        audit_repo=container.audit,
        trace_repo=container.traces,
        fraud_repo=container.fraud,
        transaction_repo=container.transactions,
        customer_repo=container.customers,
    )
    sentiment_agent = SentimentAgent(
        llm=container.llm,
        retrieval=container.retrieval,
        audit_repo=container.audit,
        trace_repo=container.traces,
        interaction_repo=container.interactions,
        customer_repo=container.customers,
    )
    loan_agent = LoanAgent(
        llm=container.llm,
        retrieval=container.retrieval,
        audit_repo=container.audit,
        trace_repo=container.traces,
        loan_repo=container.loans,
        customer_repo=container.customers,
        fraud_repo=container.fraud,
    )
    branch_agent = BranchAgent(
        llm=container.llm,
        retrieval=container.retrieval,
        audit_repo=container.audit,
        trace_repo=container.traces,
        branch_repo=container.branches,
        interaction_repo=container.interactions,
        transaction_repo=container.transactions,
    )
    advisory_agent = AdvisoryAgent(
        llm=container.llm,
        retrieval=container.retrieval,
        audit_repo=container.audit,
        trace_repo=container.traces,
        advisory_repo=container.advisory,
        customer_repo=container.customers,
        fraud_repo=container.fraud,
        loan_repo=container.loans,
        case_repo=container.cases,
    )
    return Supervisor(
        fraud_agent=fraud_agent,
        sentiment_agent=sentiment_agent,
        loan_agent=loan_agent,
        branch_agent=branch_agent,
        advisory_agent=advisory_agent,
        case_repo=container.cases,
        audit_repo=container.audit,
        trace_repo=container.traces,
    )

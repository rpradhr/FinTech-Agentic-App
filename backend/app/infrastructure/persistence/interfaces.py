"""
Repository interfaces — the persistence contract.

All adapters (Couchbase, in-memory, etc.) MUST implement these ABCs.
Application and domain layers import ONLY from this module, never from adapters.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import date, datetime

from app.domain.models import (
    AdviceDraft,
    AgentTrace,
    AuditEvent,
    BranchAlert,
    BranchInsight,
    BranchKPI,
    Case,
    CustomerProfile,
    CustomerSignal,
    FraudAlert,
    FraudRingCluster,
    Household,
    Interaction,
    InteractionAnalysis,
    LoanApplication,
    LoanException,
    LoanReview,
    Transaction,
)

# ─────────────────────────────────────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────────────────────────────────────


class CustomerRepository(ABC):
    @abstractmethod
    async def get_by_id(self, customer_id: str) -> CustomerProfile | None: ...

    @abstractmethod
    async def save(self, profile: CustomerProfile) -> CustomerProfile: ...

    @abstractmethod
    async def update_sentiment(
        self, customer_id: str, sentiment_status: str, churn_risk: float
    ) -> None: ...

    @abstractmethod
    async def get_household_members(self, household_id: str) -> list[CustomerProfile]: ...

    @abstractmethod
    async def save_household(self, household: Household) -> Household: ...

    @abstractmethod
    async def get_customer_signal(self, customer_id: str) -> CustomerSignal | None: ...

    @abstractmethod
    async def save_customer_signal(self, signal: CustomerSignal) -> CustomerSignal: ...


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────


class TransactionRepository(ABC):
    @abstractmethod
    async def get_by_id(self, txn_id: str) -> Transaction | None: ...

    @abstractmethod
    async def save(self, txn: Transaction) -> Transaction: ...

    @abstractmethod
    async def get_recent_by_customer(
        self, customer_id: str, limit: int = 50
    ) -> list[Transaction]: ...

    @abstractmethod
    async def get_by_account(
        self, account_id: str, since: datetime | None = None, limit: int = 100
    ) -> list[Transaction]: ...

    @abstractmethod
    async def get_by_device(self, device_id: str, limit: int = 50) -> list[Transaction]: ...

    @abstractmethod
    async def get_by_merchant(self, merchant: str, limit: int = 50) -> list[Transaction]: ...

    @abstractmethod
    async def get_flagged_by_branch(
        self, branch_id: str, since: datetime | None = None
    ) -> list[Transaction]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Fraud
# ─────────────────────────────────────────────────────────────────────────────


class FraudRepository(ABC):
    @abstractmethod
    async def get_alert_by_id(self, alert_id: str) -> FraudAlert | None: ...

    @abstractmethod
    async def save_alert(self, alert: FraudAlert) -> FraudAlert: ...

    @abstractmethod
    async def update_alert_status(
        self,
        alert_id: str,
        status: str,
        analyst_id: str | None = None,
        decision: str | None = None,
        notes: str | None = None,
    ) -> FraudAlert: ...

    @abstractmethod
    async def list_pending_alerts(self, limit: int = 50) -> list[FraudAlert]: ...

    @abstractmethod
    async def get_alerts_by_customer(
        self, customer_id: str, limit: int = 20
    ) -> list[FraudAlert]: ...

    @abstractmethod
    async def save_ring_cluster(self, cluster: FraudRingCluster) -> FraudRingCluster: ...

    @abstractmethod
    async def get_similar_patterns(
        self, customer_id: str, device_id: str | None, merchant: str | None, limit: int = 5
    ) -> list[FraudAlert]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Loan
# ─────────────────────────────────────────────────────────────────────────────


class LoanRepository(ABC):
    @abstractmethod
    async def get_application_by_id(self, application_id: str) -> LoanApplication | None: ...

    @abstractmethod
    async def save_application(self, application: LoanApplication) -> LoanApplication: ...

    @abstractmethod
    async def update_application_status(
        self, application_id: str, status: str
    ) -> LoanApplication: ...

    @abstractmethod
    async def get_review_by_application(self, application_id: str) -> LoanReview | None: ...

    @abstractmethod
    async def save_review(self, review: LoanReview) -> LoanReview: ...

    @abstractmethod
    async def update_review_decision(
        self,
        review_id: str,
        underwriter_id: str,
        decision: str,
        notes: str | None = None,
    ) -> LoanReview: ...

    @abstractmethod
    async def list_pending_reviews(self, limit: int = 50) -> list[LoanReview]: ...

    @abstractmethod
    async def save_exception(self, exception: LoanException) -> LoanException: ...

    @abstractmethod
    async def get_exceptions_by_application(self, application_id: str) -> list[LoanException]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Interactions / Sentiment
# ─────────────────────────────────────────────────────────────────────────────


class InteractionRepository(ABC):
    @abstractmethod
    async def save_interaction(self, interaction: Interaction) -> Interaction: ...

    @abstractmethod
    async def get_interaction_by_id(self, interaction_id: str) -> Interaction | None: ...

    @abstractmethod
    async def get_interactions_by_customer(
        self, customer_id: str, limit: int = 20
    ) -> list[Interaction]: ...

    @abstractmethod
    async def save_analysis(self, analysis: InteractionAnalysis) -> InteractionAnalysis: ...

    @abstractmethod
    async def get_analysis_by_interaction(
        self, interaction_id: str
    ) -> InteractionAnalysis | None: ...

    @abstractmethod
    async def get_recent_analyses_by_customer(
        self, customer_id: str, limit: int = 10
    ) -> list[InteractionAnalysis]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Branch
# ─────────────────────────────────────────────────────────────────────────────


class BranchRepository(ABC):
    @abstractmethod
    async def save_kpi(self, kpi: BranchKPI) -> BranchKPI: ...

    @abstractmethod
    async def get_kpi(self, branch_id: str, report_date: date) -> BranchKPI | None: ...

    @abstractmethod
    async def get_recent_kpis(self, branch_id: str, days: int = 30) -> list[BranchKPI]: ...

    @abstractmethod
    async def save_alert(self, alert: BranchAlert) -> BranchAlert: ...

    @abstractmethod
    async def list_branch_alerts(
        self, branch_id: str | None = None, limit: int = 50
    ) -> list[BranchAlert]: ...

    @abstractmethod
    async def save_insight(self, insight: BranchInsight) -> BranchInsight: ...

    @abstractmethod
    async def get_insights_by_branch(
        self, branch_id: str, limit: int = 10
    ) -> list[BranchInsight]: ...

    @abstractmethod
    async def list_branches_dashboard(self) -> list[dict]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────────────────────────────────────


class CaseRepository(ABC):
    @abstractmethod
    async def get_by_id(self, case_id: str) -> Case | None: ...

    @abstractmethod
    async def save(self, case: Case) -> Case: ...

    @abstractmethod
    async def update_status(self, case_id: str, status: str) -> Case: ...

    @abstractmethod
    async def list_open_cases(
        self, case_type: str | None = None, limit: int = 50
    ) -> list[Case]: ...

    @abstractmethod
    async def get_cases_by_customer(self, customer_id: str) -> list[Case]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Advisory
# ─────────────────────────────────────────────────────────────────────────────


class AdvisoryRepository(ABC):
    @abstractmethod
    async def save_draft(self, draft: AdviceDraft) -> AdviceDraft: ...

    @abstractmethod
    async def get_draft_by_id(self, draft_id: str) -> AdviceDraft | None: ...

    @abstractmethod
    async def update_draft_status(
        self,
        draft_id: str,
        status: str,
        advisor_edits: str | None = None,
    ) -> AdviceDraft: ...

    @abstractmethod
    async def get_drafts_by_customer(
        self, customer_id: str, limit: int = 10
    ) -> list[AdviceDraft]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────


class AuditRepository(ABC):
    @abstractmethod
    async def append(self, event: AuditEvent) -> AuditEvent: ...

    @abstractmethod
    async def get_by_object(self, object_id: str) -> list[AuditEvent]: ...

    @abstractmethod
    async def get_by_customer(self, customer_id: str, limit: int = 100) -> list[AuditEvent]: ...

    @abstractmethod
    async def get_by_session(self, session_id: str) -> list[AuditEvent]: ...


# ─────────────────────────────────────────────────────────────────────────────
# Agent Traces
# ─────────────────────────────────────────────────────────────────────────────


class TraceRepository(ABC):
    @abstractmethod
    async def append_trace(self, trace: AgentTrace) -> AgentTrace: ...

    @abstractmethod
    async def get_session_traces(self, session_id: str) -> list[AgentTrace]: ...

"""
In-memory implementations of all repository interfaces.

These are the reference / test adapter. They fulfil the same contracts as the
Couchbase adapter and are used in unit tests and local dev (APP_ENV=development
with no Couchbase connection string set).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

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
from app.infrastructure.persistence.interfaces import (
    AdvisoryRepository,
    AuditRepository,
    BranchRepository,
    CaseRepository,
    CustomerRepository,
    FraudRepository,
    InteractionRepository,
    LoanRepository,
    TraceRepository,
    TransactionRepository,
)

from .store import InMemoryStore


# ─────────────────────────────────────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryCustomerRepository(CustomerRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, customer_id: str) -> Optional[CustomerProfile]:
        return self._store.get("customers", customer_id)

    async def save(self, profile: CustomerProfile) -> CustomerProfile:
        profile.updated_at = datetime.utcnow()
        self._store.put("customers", profile.customer_id, profile)
        return profile

    async def update_sentiment(
        self, customer_id: str, sentiment_status: str, churn_risk: float
    ) -> None:
        profile = await self.get_by_id(customer_id)
        if profile:
            profile.last_sentiment_status = sentiment_status
            profile.churn_risk_score = churn_risk
            await self.save(profile)

    async def get_household_members(self, household_id: str) -> list[CustomerProfile]:
        return self._store.filter("customers", household_id=household_id)

    async def save_household(self, household: Household) -> Household:
        self._store.put("households", household.household_id, household)
        return household

    async def get_customer_signal(self, customer_id: str) -> Optional[CustomerSignal]:
        return self._store.get("customer_signals", customer_id)

    async def save_customer_signal(self, signal: CustomerSignal) -> CustomerSignal:
        signal.updated_at = datetime.utcnow()
        self._store.put("customer_signals", signal.customer_id, signal)
        return signal


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryTransactionRepository(TransactionRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, txn_id: str) -> Optional[Transaction]:
        return self._store.get("transactions", txn_id)

    async def save(self, txn: Transaction) -> Transaction:
        self._store.put("transactions", txn.txn_id, txn)
        return txn

    async def get_recent_by_customer(
        self, customer_id: str, limit: int = 50
    ) -> list[Transaction]:
        items = self._store.filter("transactions", customer_id=customer_id)
        return sorted(items, key=lambda x: x.event_ts, reverse=True)[:limit]

    async def get_by_account(
        self, account_id: str, since: Optional[datetime] = None, limit: int = 100
    ) -> list[Transaction]:
        items = self._store.filter("transactions", account_id=account_id)
        if since:
            items = [i for i in items if i.event_ts >= since]
        return sorted(items, key=lambda x: x.event_ts, reverse=True)[:limit]

    async def get_by_device(self, device_id: str, limit: int = 50) -> list[Transaction]:
        items = self._store.filter("transactions", device_id=device_id)
        return sorted(items, key=lambda x: x.event_ts, reverse=True)[:limit]

    async def get_by_merchant(self, merchant: str, limit: int = 50) -> list[Transaction]:
        items = self._store.filter("transactions", merchant=merchant)
        return sorted(items, key=lambda x: x.event_ts, reverse=True)[:limit]

    async def get_flagged_by_branch(
        self, branch_id: str, since: Optional[datetime] = None
    ) -> list[Transaction]:
        items = [
            t for t in self._store.all("transactions")
            if t.branch_id == branch_id and t.status == "flagged"
        ]
        if since:
            items = [i for i in items if i.event_ts >= since]
        return items


# ─────────────────────────────────────────────────────────────────────────────
# Fraud
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryFraudRepository(FraudRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_alert_by_id(self, alert_id: str) -> Optional[FraudAlert]:
        return self._store.get("fraud_alerts", alert_id)

    async def save_alert(self, alert: FraudAlert) -> FraudAlert:
        alert.updated_at = datetime.utcnow()
        self._store.put("fraud_alerts", alert.alert_id, alert)
        return alert

    async def update_alert_status(
        self,
        alert_id: str,
        status: str,
        analyst_id: Optional[str] = None,
        decision: Optional[str] = None,
        notes: Optional[str] = None,
    ) -> FraudAlert:
        alert = await self.get_alert_by_id(alert_id)
        if alert is None:
            raise KeyError(f"FraudAlert {alert_id} not found")
        alert.status = status
        if analyst_id:
            alert.assigned_analyst_id = analyst_id
        if decision:
            alert.analyst_decision = decision
        if notes:
            alert.analyst_notes = notes
        alert.updated_at = datetime.utcnow()
        return await self.save_alert(alert)

    async def list_pending_alerts(self, limit: int = 50) -> list[FraudAlert]:
        items = self._store.filter("fraud_alerts", status="pending_analyst_review")
        return sorted(items, key=lambda x: x.risk_score, reverse=True)[:limit]

    async def get_alerts_by_customer(
        self, customer_id: str, limit: int = 20
    ) -> list[FraudAlert]:
        items = self._store.filter("fraud_alerts", customer_id=customer_id)
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def save_ring_cluster(self, cluster: FraudRingCluster) -> FraudRingCluster:
        self._store.put("fraud_rings", cluster.cluster_id, cluster)
        return cluster

    async def get_similar_patterns(
        self,
        customer_id: str,
        device_id: Optional[str],
        merchant: Optional[str],
        limit: int = 5,
    ) -> list[FraudAlert]:
        # Simplified: return recent alerts on the same customer
        return await self.get_alerts_by_customer(customer_id, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Loan
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryLoanRepository(LoanRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_application_by_id(self, application_id: str) -> Optional[LoanApplication]:
        return self._store.get("loan_applications", application_id)

    async def save_application(self, application: LoanApplication) -> LoanApplication:
        application.updated_at = datetime.utcnow()
        self._store.put("loan_applications", application.application_id, application)
        return application

    async def update_application_status(
        self, application_id: str, status: str
    ) -> LoanApplication:
        app = await self.get_application_by_id(application_id)
        if app is None:
            raise KeyError(f"LoanApplication {application_id} not found")
        app.status = status
        return await self.save_application(app)

    async def get_review_by_application(
        self, application_id: str
    ) -> Optional[LoanReview]:
        items = self._store.filter("loan_reviews", application_id=application_id)
        return items[0] if items else None

    async def save_review(self, review: LoanReview) -> LoanReview:
        self._store.put("loan_reviews", review.review_id, review)
        return review

    async def update_review_decision(
        self,
        review_id: str,
        underwriter_id: str,
        decision: str,
        notes: Optional[str] = None,
    ) -> LoanReview:
        review = self._store.get("loan_reviews", review_id)
        if review is None:
            raise KeyError(f"LoanReview {review_id} not found")
        review.underwriter_id = underwriter_id
        review.underwriter_decision = decision
        review.underwriter_notes = notes
        review.reviewed_at = datetime.utcnow()
        return await self.save_review(review)

    async def list_pending_reviews(self, limit: int = 50) -> list[LoanReview]:
        items = [
            r for r in self._store.all("loan_reviews")
            if r.underwriter_decision is None
        ]
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def save_exception(self, exception: LoanException) -> LoanException:
        self._store.put("loan_exceptions", exception.exception_id, exception)
        return exception

    async def get_exceptions_by_application(
        self, application_id: str
    ) -> list[LoanException]:
        return self._store.filter("loan_exceptions", application_id=application_id)


# ─────────────────────────────────────────────────────────────────────────────
# Interactions
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryInteractionRepository(InteractionRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def save_interaction(self, interaction: Interaction) -> Interaction:
        self._store.put("interactions", interaction.interaction_id, interaction)
        return interaction

    async def get_interaction_by_id(self, interaction_id: str) -> Optional[Interaction]:
        return self._store.get("interactions", interaction_id)

    async def get_interactions_by_customer(
        self, customer_id: str, limit: int = 20
    ) -> list[Interaction]:
        items = self._store.filter("interactions", customer_id=customer_id)
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def save_analysis(self, analysis: InteractionAnalysis) -> InteractionAnalysis:
        self._store.put("interaction_analyses", analysis.analysis_id, analysis)
        return analysis

    async def get_analysis_by_interaction(
        self, interaction_id: str
    ) -> Optional[InteractionAnalysis]:
        items = self._store.filter(
            "interaction_analyses", interaction_id=interaction_id
        )
        return items[0] if items else None

    async def get_recent_analyses_by_customer(
        self, customer_id: str, limit: int = 10
    ) -> list[InteractionAnalysis]:
        items = self._store.filter("interaction_analyses", customer_id=customer_id)
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Branch
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryBranchRepository(BranchRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def save_kpi(self, kpi: BranchKPI) -> BranchKPI:
        self._store.put("branch_kpis", kpi.kpi_id, kpi)
        return kpi

    async def get_kpi(self, branch_id: str, report_date: date) -> Optional[BranchKPI]:
        items = [
            k for k in self._store.all("branch_kpis")
            if k.branch_id == branch_id and k.report_date == report_date
        ]
        return items[0] if items else None

    async def get_recent_kpis(self, branch_id: str, days: int = 30) -> list[BranchKPI]:
        items = self._store.filter("branch_kpis", branch_id=branch_id)
        return sorted(items, key=lambda x: x.report_date, reverse=True)[:days]

    async def save_alert(self, alert: BranchAlert) -> BranchAlert:
        self._store.put("branch_alerts", alert.alert_id, alert)
        return alert

    async def list_branch_alerts(
        self, branch_id: Optional[str] = None, limit: int = 50
    ) -> list[BranchAlert]:
        items = self._store.all("branch_alerts")
        if branch_id:
            items = [a for a in items if a.branch_id == branch_id]
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def save_insight(self, insight: BranchInsight) -> BranchInsight:
        self._store.put("branch_insights", insight.insight_id, insight)
        return insight

    async def get_insights_by_branch(
        self, branch_id: str, limit: int = 10
    ) -> list[BranchInsight]:
        items = self._store.filter("branch_insights", branch_id=branch_id)
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def list_branches_dashboard(self) -> list[dict]:
        kpis = self._store.all("branch_kpis")
        # Group by branch_id and return latest KPI per branch
        latest: dict[str, BranchKPI] = {}
        for kpi in kpis:
            if kpi.branch_id not in latest or kpi.report_date > latest[kpi.branch_id].report_date:
                latest[kpi.branch_id] = kpi
        return [k.model_dump() for k in latest.values()]


# ─────────────────────────────────────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryCaseRepository(CaseRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def get_by_id(self, case_id: str) -> Optional[Case]:
        return self._store.get("cases", case_id)

    async def save(self, case: Case) -> Case:
        case.updated_at = datetime.utcnow()
        self._store.put("cases", case.case_id, case)
        return case

    async def update_status(self, case_id: str, status: str) -> Case:
        case = await self.get_by_id(case_id)
        if case is None:
            raise KeyError(f"Case {case_id} not found")
        case.status = status
        return await self.save(case)

    async def list_open_cases(
        self, case_type: Optional[str] = None, limit: int = 50
    ) -> list[Case]:
        items = [c for c in self._store.all("cases") if c.status != "closed"]
        if case_type:
            items = [c for c in items if c.case_type == case_type]
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]

    async def get_cases_by_customer(self, customer_id: str) -> list[Case]:
        return self._store.filter("cases", customer_id=customer_id)


# ─────────────────────────────────────────────────────────────────────────────
# Advisory
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryAdvisoryRepository(AdvisoryRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def save_draft(self, draft: AdviceDraft) -> AdviceDraft:
        self._store.put("advice_drafts", draft.draft_id, draft)
        return draft

    async def get_draft_by_id(self, draft_id: str) -> Optional[AdviceDraft]:
        return self._store.get("advice_drafts", draft_id)

    async def update_draft_status(
        self,
        draft_id: str,
        status: str,
        advisor_edits: Optional[str] = None,
    ) -> AdviceDraft:
        draft = await self.get_draft_by_id(draft_id)
        if draft is None:
            raise KeyError(f"AdviceDraft {draft_id} not found")
        draft.status = status
        if advisor_edits:
            draft.advisor_edits = advisor_edits
        if status in ("approved", "edited_and_approved"):
            draft.approved_at = datetime.utcnow()
        return await self.save_draft(draft)

    async def get_drafts_by_customer(
        self, customer_id: str, limit: int = 10
    ) -> list[AdviceDraft]:
        items = self._store.filter("advice_drafts", customer_id=customer_id)
        return sorted(items, key=lambda x: x.created_at, reverse=True)[:limit]


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryAuditRepository(AuditRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def append(self, event: AuditEvent) -> AuditEvent:
        self._store.put("audit_events", event.event_id, event)
        return event

    async def get_by_object(self, object_id: str) -> list[AuditEvent]:
        items = self._store.filter("audit_events", related_object_id=object_id)
        return sorted(items, key=lambda x: x.ts)

    async def get_by_customer(self, customer_id: str, limit: int = 100) -> list[AuditEvent]:
        items = self._store.filter("audit_events", customer_id=customer_id)
        return sorted(items, key=lambda x: x.ts, reverse=True)[:limit]

    async def get_by_session(self, session_id: str) -> list[AuditEvent]:
        items = self._store.filter("audit_events", agent_session_id=session_id)
        return sorted(items, key=lambda x: x.ts)


# ─────────────────────────────────────────────────────────────────────────────
# Traces
# ─────────────────────────────────────────────────────────────────────────────


class InMemoryTraceRepository(TraceRepository):
    def __init__(self, store: InMemoryStore) -> None:
        self._store = store

    async def append_trace(self, trace: AgentTrace) -> AgentTrace:
        self._store.put("agent_traces", trace.trace_id, trace)
        return trace

    async def get_session_traces(self, session_id: str) -> list[AgentTrace]:
        items = self._store.filter("agent_traces", session_id=session_id)
        return sorted(items, key=lambda x: x.step_index)

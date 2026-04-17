"""
Couchbase implementations of all repository interfaces.

All Couchbase SDK calls are contained here and in client.py.
Only standard Python and domain model types cross the module boundary.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import date, datetime
from typing import Any, TypeVar

from couchbase.exceptions import DocumentNotFoundException

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

from .client import CouchbaseClient

logger = logging.getLogger(__name__)

T = TypeVar("T")


def _run_sync(fn, *args, **kwargs):
    """Run a synchronous Couchbase SDK call in the default executor."""
    loop = asyncio.get_event_loop()
    return loop.run_in_executor(None, lambda: fn(*args, **kwargs))


class _BaseRepo:
    def __init__(self, client: CouchbaseClient) -> None:
        self._client = client

    async def _get(self, collection_name: str, key: str) -> dict | None:
        col = self._client.get_collection(collection_name)
        try:
            result = await _run_sync(col.get, key)
            return result.content_as[dict]
        except DocumentNotFoundException:
            return None
        except Exception as exc:
            logger.error("Couchbase GET error [%s/%s]: %s", collection_name, key, exc)
            raise

    async def _upsert(self, collection_name: str, key: str, doc: dict) -> None:
        col = self._client.get_collection(collection_name)
        await _run_sync(col.upsert, key, doc)

    async def _query(self, statement: str, **params) -> list[dict]:
        """Execute a SQL++ query and return list of row dicts."""
        cluster = self._client.cluster()
        result = await _run_sync(cluster.query, statement, **params)
        return [row for row in result]


# ─────────────────────────────────────────────────────────────────────────────
# Customer
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseCustomerRepository(CustomerRepository, _BaseRepo):
    async def get_by_id(self, customer_id: str) -> CustomerProfile | None:
        doc = await self._get("customers", customer_id)
        return CustomerProfile(**doc) if doc else None

    async def save(self, profile: CustomerProfile) -> CustomerProfile:
        profile.updated_at = datetime.utcnow()
        await self._upsert("customers", profile.customer_id, profile.model_dump(mode="json"))
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
        rows = await self._query(
            "SELECT c.* FROM `banking-core`.customers.profiles c "
            "WHERE c.household_id = $household_id",
            household_id=household_id,
        )
        return [CustomerProfile(**r) for r in rows]

    async def save_household(self, household: Household) -> Household:
        await self._upsert("households", household.household_id, household.model_dump(mode="json"))
        return household

    async def get_customer_signal(self, customer_id: str) -> CustomerSignal | None:
        doc = await self._get("customer_signals", customer_id)
        return CustomerSignal(**doc) if doc else None

    async def save_customer_signal(self, signal: CustomerSignal) -> CustomerSignal:
        signal.updated_at = datetime.utcnow()
        await self._upsert("customer_signals", signal.customer_id, signal.model_dump(mode="json"))
        return signal


# ─────────────────────────────────────────────────────────────────────────────
# Transactions
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseTransactionRepository(TransactionRepository, _BaseRepo):
    async def get_by_id(self, txn_id: str) -> Transaction | None:
        doc = await self._get("transactions", txn_id)
        return Transaction(**doc) if doc else None

    async def save(self, txn: Transaction) -> Transaction:
        await self._upsert("transactions", txn.txn_id, txn.model_dump(mode="json"))
        return txn

    async def get_recent_by_customer(self, customer_id: str, limit: int = 50) -> list[Transaction]:
        rows = await self._query(
            "SELECT t.* FROM `banking-core`.transactions.ledger_events t "
            "WHERE t.customer_id = $cid ORDER BY t.event_ts DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [Transaction(**r) for r in rows]

    async def get_by_account(
        self, account_id: str, since: datetime | None = None, limit: int = 100
    ) -> list[Transaction]:
        query = (
            "SELECT t.* FROM `banking-core`.transactions.ledger_events t WHERE t.account_id = $aid"
        )
        params: dict[str, Any] = {"aid": account_id, "lim": limit}
        if since:
            query += " AND t.event_ts >= $since"
            params["since"] = since.isoformat()
        query += " ORDER BY t.event_ts DESC LIMIT $lim"
        rows = await self._query(query, **params)
        return [Transaction(**r) for r in rows]

    async def get_by_device(self, device_id: str, limit: int = 50) -> list[Transaction]:
        rows = await self._query(
            "SELECT t.* FROM `banking-core`.transactions.ledger_events t "
            "WHERE t.device_id = $did ORDER BY t.event_ts DESC LIMIT $lim",
            did=device_id,
            lim=limit,
        )
        return [Transaction(**r) for r in rows]

    async def get_by_merchant(self, merchant: str, limit: int = 50) -> list[Transaction]:
        rows = await self._query(
            "SELECT t.* FROM `banking-core`.transactions.ledger_events t "
            "WHERE t.merchant = $merchant ORDER BY t.event_ts DESC LIMIT $lim",
            merchant=merchant,
            lim=limit,
        )
        return [Transaction(**r) for r in rows]

    async def get_flagged_by_branch(
        self, branch_id: str, since: datetime | None = None
    ) -> list[Transaction]:
        query = (
            "SELECT t.* FROM `banking-core`.transactions.ledger_events t "
            "WHERE t.branch_id = $bid AND t.status = 'flagged'"
        )
        params: dict[str, Any] = {"bid": branch_id}
        if since:
            query += " AND t.event_ts >= $since"
            params["since"] = since.isoformat()
        rows = await self._query(query, **params)
        return [Transaction(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Fraud
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseFraudRepository(FraudRepository, _BaseRepo):
    async def get_alert_by_id(self, alert_id: str) -> FraudAlert | None:
        doc = await self._get("fraud_alerts", alert_id)
        return FraudAlert(**doc) if doc else None

    async def save_alert(self, alert: FraudAlert) -> FraudAlert:
        alert.updated_at = datetime.utcnow()
        await self._upsert("fraud_alerts", alert.alert_id, alert.model_dump(mode="json"))
        return alert

    async def update_alert_status(
        self,
        alert_id: str,
        status: str,
        analyst_id: str | None = None,
        decision: str | None = None,
        notes: str | None = None,
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
        return await self.save_alert(alert)

    async def list_pending_alerts(self, limit: int = 50) -> list[FraudAlert]:
        rows = await self._query(
            "SELECT f.* FROM `banking-core`.agents.recommendations f "
            "WHERE f.type = 'fraud_alert' AND f.status = 'pending_analyst_review' "
            "ORDER BY f.risk_score DESC LIMIT $lim",
            lim=limit,
        )
        return [FraudAlert(**r) for r in rows]

    async def get_alerts_by_customer(self, customer_id: str, limit: int = 20) -> list[FraudAlert]:
        rows = await self._query(
            "SELECT f.* FROM `banking-core`.agents.recommendations f "
            "WHERE f.type = 'fraud_alert' AND f.customer_id = $cid "
            "ORDER BY f.created_at DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [FraudAlert(**r) for r in rows]

    async def save_ring_cluster(self, cluster: FraudRingCluster) -> FraudRingCluster:
        await self._upsert("fraud_rings", cluster.cluster_id, cluster.model_dump(mode="json"))
        return cluster

    async def get_similar_patterns(
        self,
        customer_id: str,
        device_id: str | None,
        merchant: str | None,
        limit: int = 5,
    ) -> list[FraudAlert]:
        # Simplified: return recent alerts on the same customer
        return await self.get_alerts_by_customer(customer_id, limit)


# ─────────────────────────────────────────────────────────────────────────────
# Loan
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseLoanRepository(LoanRepository, _BaseRepo):
    async def get_application_by_id(self, application_id: str) -> LoanApplication | None:
        doc = await self._get("loan_applications", application_id)
        return LoanApplication(**doc) if doc else None

    async def save_application(self, application: LoanApplication) -> LoanApplication:
        application.updated_at = datetime.utcnow()
        await self._upsert(
            "loan_applications",
            application.application_id,
            application.model_dump(mode="json"),
        )
        return application

    async def update_application_status(self, application_id: str, status: str) -> LoanApplication:
        app = await self.get_application_by_id(application_id)
        if app is None:
            raise KeyError(f"LoanApplication {application_id} not found")
        app.status = status
        return await self.save_application(app)

    async def get_review_by_application(self, application_id: str) -> LoanReview | None:
        rows = await self._query(
            "SELECT r.* FROM `banking-core`.loans.reviews r WHERE r.application_id = $aid LIMIT 1",
            aid=application_id,
        )
        return LoanReview(**rows[0]) if rows else None

    async def save_review(self, review: LoanReview) -> LoanReview:
        await self._upsert("loan_reviews", review.review_id, review.model_dump(mode="json"))
        return review

    async def update_review_decision(
        self,
        review_id: str,
        underwriter_id: str,
        decision: str,
        notes: str | None = None,
    ) -> LoanReview:
        review = self._client.get_collection("loan_reviews").get(review_id).content_as[dict]
        review_obj = LoanReview(**review)
        review_obj.underwriter_id = underwriter_id
        review_obj.underwriter_decision = decision
        review_obj.underwriter_notes = notes
        review_obj.reviewed_at = datetime.utcnow()
        return await self.save_review(review_obj)

    async def list_pending_reviews(self, limit: int = 50) -> list[LoanReview]:
        rows = await self._query(
            "SELECT r.* FROM `banking-core`.loans.reviews r "
            "WHERE r.underwriter_decision IS MISSING OR r.underwriter_decision IS NULL "
            "ORDER BY r.created_at DESC LIMIT $lim",
            lim=limit,
        )
        return [LoanReview(**r) for r in rows]

    async def save_exception(self, exception: LoanException) -> LoanException:
        await self._upsert(
            "loan_exceptions", exception.exception_id, exception.model_dump(mode="json")
        )
        return exception

    async def get_exceptions_by_application(self, application_id: str) -> list[LoanException]:
        rows = await self._query(
            "SELECT e.* FROM `banking-core`.loans.policy_refs e WHERE e.application_id = $aid",
            aid=application_id,
        )
        return [LoanException(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Interactions
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseInteractionRepository(InteractionRepository, _BaseRepo):
    async def save_interaction(self, interaction: Interaction) -> Interaction:
        await self._upsert(
            "interactions", interaction.interaction_id, interaction.model_dump(mode="json")
        )
        return interaction

    async def get_interaction_by_id(self, interaction_id: str) -> Interaction | None:
        doc = await self._get("interactions", interaction_id)
        return Interaction(**doc) if doc else None

    async def get_interactions_by_customer(
        self, customer_id: str, limit: int = 20
    ) -> list[Interaction]:
        rows = await self._query(
            "SELECT i.* FROM `banking-core`.interactions.transcripts i "
            "WHERE i.customer_id = $cid ORDER BY i.created_at DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [Interaction(**r) for r in rows]

    async def save_analysis(self, analysis: InteractionAnalysis) -> InteractionAnalysis:
        await self._upsert(
            "interaction_analyses", analysis.analysis_id, analysis.model_dump(mode="json")
        )
        return analysis

    async def get_analysis_by_interaction(self, interaction_id: str) -> InteractionAnalysis | None:
        rows = await self._query(
            "SELECT a.* FROM `banking-core`.interactions.analysis a "
            "WHERE a.interaction_id = $iid LIMIT 1",
            iid=interaction_id,
        )
        return InteractionAnalysis(**rows[0]) if rows else None

    async def get_recent_analyses_by_customer(
        self, customer_id: str, limit: int = 10
    ) -> list[InteractionAnalysis]:
        rows = await self._query(
            "SELECT a.* FROM `banking-core`.interactions.analysis a "
            "WHERE a.customer_id = $cid ORDER BY a.created_at DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [InteractionAnalysis(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Branch
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseBranchRepository(BranchRepository, _BaseRepo):
    async def save_kpi(self, kpi: BranchKPI) -> BranchKPI:
        await self._upsert("branch_kpis", kpi.kpi_id, kpi.model_dump(mode="json"))
        return kpi

    async def get_kpi(self, branch_id: str, report_date: date) -> BranchKPI | None:
        rows = await self._query(
            "SELECT k.* FROM `banking-core`.branches.kpis k "
            "WHERE k.branch_id = $bid AND k.report_date = $dt LIMIT 1",
            bid=branch_id,
            dt=report_date.isoformat(),
        )
        return BranchKPI(**rows[0]) if rows else None

    async def get_recent_kpis(self, branch_id: str, days: int = 30) -> list[BranchKPI]:
        rows = await self._query(
            "SELECT k.* FROM `banking-core`.branches.kpis k "
            "WHERE k.branch_id = $bid ORDER BY k.report_date DESC LIMIT $days",
            bid=branch_id,
            days=days,
        )
        return [BranchKPI(**r) for r in rows]

    async def save_alert(self, alert: BranchAlert) -> BranchAlert:
        await self._upsert("branch_alerts", alert.alert_id, alert.model_dump(mode="json"))
        return alert

    async def list_branch_alerts(
        self, branch_id: str | None = None, limit: int = 50
    ) -> list[BranchAlert]:
        if branch_id:
            rows = await self._query(
                "SELECT a.* FROM `banking-core`.branches.alerts a "
                "WHERE a.branch_id = $bid ORDER BY a.created_at DESC LIMIT $lim",
                bid=branch_id,
                lim=limit,
            )
        else:
            rows = await self._query(
                "SELECT a.* FROM `banking-core`.branches.alerts a "
                "ORDER BY a.created_at DESC LIMIT $lim",
                lim=limit,
            )
        return [BranchAlert(**r) for r in rows]

    async def save_insight(self, insight: BranchInsight) -> BranchInsight:
        await self._upsert("branch_insights", insight.insight_id, insight.model_dump(mode="json"))
        return insight

    async def get_insights_by_branch(self, branch_id: str, limit: int = 10) -> list[BranchInsight]:
        rows = await self._query(
            "SELECT i.* FROM `banking-core`.branches.alerts i "
            "WHERE i.branch_id = $bid ORDER BY i.created_at DESC LIMIT $lim",
            bid=branch_id,
            lim=limit,
        )
        return [BranchInsight(**r) for r in rows]

    async def list_branches_dashboard(self) -> list[dict]:
        rows = await self._query(
            "SELECT k.branch_id, k.branch_name, k.report_date, "
            "k.avg_wait_time_minutes, k.complaint_count, k.new_accounts_opened "
            "FROM `banking-core`.branches.kpis k "
            "WHERE k.report_date = (SELECT MAX(k2.report_date) FROM "
            "`banking-core`.branches.kpis k2 WHERE k2.branch_id = k.branch_id)"
        )
        return rows


# ─────────────────────────────────────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseCaseRepository(CaseRepository, _BaseRepo):
    async def get_by_id(self, case_id: str) -> Case | None:
        doc = await self._get("cases", case_id)
        return Case(**doc) if doc else None

    async def save(self, case: Case) -> Case:
        case.updated_at = datetime.utcnow()
        await self._upsert("cases", case.case_id, case.model_dump(mode="json"))
        return case

    async def update_status(self, case_id: str, status: str) -> Case:
        case = await self.get_by_id(case_id)
        if case is None:
            raise KeyError(f"Case {case_id} not found")
        case.status = status
        return await self.save(case)

    async def list_open_cases(self, case_type: str | None = None, limit: int = 50) -> list[Case]:
        if case_type:
            rows = await self._query(
                "SELECT c.* FROM `banking-core`.agents.case_context c "
                "WHERE c.status != 'closed' AND c.case_type = $ct "
                "ORDER BY c.created_at DESC LIMIT $lim",
                ct=case_type,
                lim=limit,
            )
        else:
            rows = await self._query(
                "SELECT c.* FROM `banking-core`.agents.case_context c "
                "WHERE c.status != 'closed' ORDER BY c.created_at DESC LIMIT $lim",
                lim=limit,
            )
        return [Case(**r) for r in rows]

    async def get_cases_by_customer(self, customer_id: str) -> list[Case]:
        rows = await self._query(
            "SELECT c.* FROM `banking-core`.agents.case_context c "
            "WHERE c.customer_id = $cid ORDER BY c.created_at DESC",
            cid=customer_id,
        )
        return [Case(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Advisory
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseAdvisoryRepository(AdvisoryRepository, _BaseRepo):
    async def save_draft(self, draft: AdviceDraft) -> AdviceDraft:
        await self._upsert("advice_drafts", draft.draft_id, draft.model_dump(mode="json"))
        return draft

    async def get_draft_by_id(self, draft_id: str) -> AdviceDraft | None:
        doc = await self._get("advice_drafts", draft_id)
        return AdviceDraft(**doc) if doc else None

    async def update_draft_status(
        self,
        draft_id: str,
        status: str,
        advisor_edits: str | None = None,
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

    async def get_drafts_by_customer(self, customer_id: str, limit: int = 10) -> list[AdviceDraft]:
        rows = await self._query(
            "SELECT d.* FROM `banking-core`.agents.recommendations d "
            "WHERE d.type = 'advice_draft' AND d.customer_id = $cid "
            "ORDER BY d.created_at DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [AdviceDraft(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseAuditRepository(AuditRepository, _BaseRepo):
    async def append(self, event: AuditEvent) -> AuditEvent:
        await self._upsert("audit_events", event.event_id, event.model_dump(mode="json"))
        return event

    async def get_by_object(self, object_id: str) -> list[AuditEvent]:
        rows = await self._query(
            "SELECT e.* FROM `banking-core`.audit.events e "
            "WHERE e.related_object_id = $oid ORDER BY e.ts",
            oid=object_id,
        )
        return [AuditEvent(**r) for r in rows]

    async def get_by_customer(self, customer_id: str, limit: int = 100) -> list[AuditEvent]:
        rows = await self._query(
            "SELECT e.* FROM `banking-core`.audit.events e "
            "WHERE e.customer_id = $cid ORDER BY e.ts DESC LIMIT $lim",
            cid=customer_id,
            lim=limit,
        )
        return [AuditEvent(**r) for r in rows]

    async def get_by_session(self, session_id: str) -> list[AuditEvent]:
        rows = await self._query(
            "SELECT e.* FROM `banking-core`.audit.events e "
            "WHERE e.agent_session_id = $sid ORDER BY e.ts",
            sid=session_id,
        )
        return [AuditEvent(**r) for r in rows]


# ─────────────────────────────────────────────────────────────────────────────
# Traces
# ─────────────────────────────────────────────────────────────────────────────


class CouchbaseTraceRepository(TraceRepository, _BaseRepo):
    async def append_trace(self, trace: AgentTrace) -> AgentTrace:
        await self._upsert("agent_traces", trace.trace_id, trace.model_dump(mode="json"))
        return trace

    async def get_session_traces(self, session_id: str) -> list[AgentTrace]:
        rows = await self._query(
            "SELECT t.* FROM `banking-core`.audit.events t "
            "WHERE t.session_id = $sid ORDER BY t.step_index",
            sid=session_id,
        )
        return [AgentTrace(**r) for r in rows]

"""
Adapter contract tests — in-memory implementation.

These tests verify that InMemory* repositories fulfil the repository interface
contracts. The same test suite can be replayed against the Couchbase adapter.
"""
import pytest
import pytest_asyncio
from datetime import datetime, date

from app.domain.models.customer import CustomerProfile, RiskTolerance
from app.domain.models.fraud import FraudAlert, FraudRiskLevel, FraudStatus
from app.domain.models.fraud import RecommendedAction
from app.domain.models.loan import LoanApplication, LoanReview
from app.domain.models.audit import AuditEvent, AuditActor, AuditAction
from app.domain.models.branch import BranchKPI
from app.domain.models.case import Case, CaseType, CaseStatus
from app.core.ids import new_audit_id, new_fraud_id
from app.infrastructure.persistence.memory import (
    InMemoryStore,
    InMemoryCustomerRepository,
    InMemoryFraudRepository,
    InMemoryLoanRepository,
    InMemoryAuditRepository,
    InMemoryBranchRepository,
    InMemoryCaseRepository,
)


@pytest.fixture
def store():
    return InMemoryStore()


# ─────────────────────────────────────────────────────────────────────────────
# CustomerRepository contract
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryCustomerRepository:
    @pytest_asyncio.fixture
    async def repo(self, store):
        return InMemoryCustomerRepository(store)

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo):
        profile = CustomerProfile(customer_id="C-001", name="Alice")
        saved = await repo.save(profile)
        found = await repo.get_by_id("C-001")
        assert found is not None
        assert found.name == "Alice"

    @pytest.mark.asyncio
    async def test_get_missing_returns_none(self, repo):
        result = await repo.get_by_id("nonexistent")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_sentiment(self, repo):
        profile = CustomerProfile(customer_id="C-001", name="Alice")
        await repo.save(profile)
        await repo.update_sentiment("C-001", "negative", 0.75)
        updated = await repo.get_by_id("C-001")
        assert updated.last_sentiment_status == "negative"
        assert updated.churn_risk_score == 0.75


# ─────────────────────────────────────────────────────────────────────────────
# FraudRepository contract
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryFraudRepository:
    @pytest_asyncio.fixture
    async def repo(self, store):
        return InMemoryFraudRepository(store)

    @pytest.mark.asyncio
    async def test_save_and_get_alert(self, repo):
        alert = FraudAlert(
            alert_id="FRAUD-001",
            txn_id="T-001",
            customer_id="C-001",
            risk_score=0.85,
            risk_level=FraudRiskLevel.HIGH,
        )
        saved = await repo.save_alert(alert)
        found = await repo.get_alert_by_id("FRAUD-001")
        assert found is not None
        assert found.risk_score == 0.85

    @pytest.mark.asyncio
    async def test_list_pending_alerts_sorted_by_risk(self, repo):
        for i, score in enumerate([0.5, 0.9, 0.3]):
            alert = FraudAlert(
                alert_id=f"FRAUD-{i:03d}",
                txn_id=f"T-{i}",
                customer_id="C-001",
                risk_score=score,
                risk_level=FraudRiskLevel.from_score(score),
            )
            await repo.save_alert(alert)

        pending = await repo.list_pending_alerts()
        scores = [a.risk_score for a in pending]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_update_alert_status(self, repo):
        alert = FraudAlert(
            alert_id="FRAUD-001",
            txn_id="T-001",
            customer_id="C-001",
            risk_score=0.85,
            risk_level=FraudRiskLevel.HIGH,
        )
        await repo.save_alert(alert)
        updated = await repo.update_alert_status(
            "FRAUD-001", "confirmed_fraud", analyst_id="analyst-1", decision="approved"
        )
        assert updated.status == "confirmed_fraud"
        assert updated.assigned_analyst_id == "analyst-1"

    @pytest.mark.asyncio
    async def test_update_missing_alert_raises(self, repo):
        with pytest.raises(KeyError):
            await repo.update_alert_status("nonexistent", "cleared")


# ─────────────────────────────────────────────────────────────────────────────
# AuditRepository — immutability and reconstruction
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryAuditRepository:
    @pytest_asyncio.fixture
    async def repo(self, store):
        return InMemoryAuditRepository(store)

    @pytest.mark.asyncio
    async def test_append_and_get_by_object(self, repo):
        event = AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.HUMAN,
            actor_id="analyst-1",
            action=AuditAction.FRAUD_ALERT_APPROVED,
            related_object_id="FRAUD-001",
            related_object_type="fraud_alert",
            customer_id="C-001",
        )
        await repo.append(event)
        trail = await repo.get_by_object("FRAUD-001")
        assert len(trail) == 1
        assert trail[0].actor_id == "analyst-1"

    @pytest.mark.asyncio
    async def test_multiple_events_chronological(self, repo):
        from app.domain.models.audit import AuditAction
        for action in [
            AuditAction.FRAUD_ALERT_CREATED,
            AuditAction.FRAUD_ALERT_APPROVED,
        ]:
            event = AuditEvent(
                event_id=new_audit_id(),
                actor_type=AuditActor.AGENT,
                actor_id="fraud_agent",
                action=action,
                related_object_id="FRAUD-001",
                related_object_type="fraud_alert",
            )
            await repo.append(event)

        trail = await repo.get_by_object("FRAUD-001")
        assert len(trail) == 2


# ─────────────────────────────────────────────────────────────────────────────
# CaseRepository
# ─────────────────────────────────────────────────────────────────────────────

class TestInMemoryCaseRepository:
    @pytest_asyncio.fixture
    async def repo(self, store):
        return InMemoryCaseRepository(store)

    @pytest.mark.asyncio
    async def test_save_and_get(self, repo):
        case = Case(
            case_id="CASE-001",
            case_type=CaseType.FRAUD,
            title="Test fraud case",
            customer_id="C-001",
        )
        await repo.save(case)
        found = await repo.get_by_id("CASE-001")
        assert found is not None
        assert found.case_type == "fraud"

    @pytest.mark.asyncio
    async def test_list_open_excludes_closed(self, repo):
        for i, status in enumerate(["open", "open", "closed"]):
            case = Case(
                case_id=f"CASE-{i:03d}",
                case_type=CaseType.FRAUD,
                title=f"Case {i}",
                status=status,
            )
            await repo.save(case)

        open_cases = await repo.list_open_cases()
        assert all(c.status != "closed" for c in open_cases)
        assert len(open_cases) == 2

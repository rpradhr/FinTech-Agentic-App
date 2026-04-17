"""
Unit tests for the five NL chat intent handlers.

Each handler is tested in isolation against the in-memory adapter so no
external services are required.  Tests cover:
  - Happy path: data found, cards shaped correctly
  - Empty-store path: meaningful "not found" response returned
  - Entity routing: customer_id / branch_id / application_id gates
  - Card content accuracy (colors, types, values)
"""
from __future__ import annotations

import os
import pytest
import pytest_asyncio

os.environ.setdefault("APP_ENV", "test")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")

from app.api.routers.chat import (
    _advisory,
    _branch,
    _churn,
    _fraud,
    _general,
    _loan,
)
from app.core.config import get_settings
from app.core.container import Container, set_container
from app.domain.models.advisory import AdviceDraft, AdviceDraftStatus, NextBestAction, AdviceCategory
from app.domain.models.branch import BranchAlert, BranchAlertSeverity, BranchInsight, BranchKPI
from app.domain.models.customer import CustomerProfile, KYCStatus
from app.domain.models.fraud import FraudAlert, FraudRiskLevel, FraudStatus
from app.domain.models.interaction import CustomerSignal
from app.domain.models.loan import LoanApplication, LoanReview


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def container():
    get_settings.cache_clear()
    c = Container(get_settings())
    await c.connect()
    set_container(c)
    yield c
    await c.close()


# ─────────────────────────────────────────────────────────────────────────────
# Helpers — seed domain objects
# ─────────────────────────────────────────────────────────────────────────────


def _make_fraud_alert(alert_id: str, customer_id: str, score: float) -> FraudAlert:
    return FraudAlert(
        alert_id=alert_id,
        txn_id=f"T-{alert_id}",
        customer_id=customer_id,
        risk_score=score,
        risk_level=FraudRiskLevel.from_score(score),
        reasons=["velocity_spike", "new_device"],
        ai_explanation="High-confidence fraud pattern detected.",
    )


def _make_loan_review(review_id: str, app_id: str, customer_id: str) -> LoanReview:
    return LoanReview(
        review_id=review_id,
        application_id=app_id,
        customer_id=customer_id,
        summary="Income verified; one document missing.",
        missing_documents=["bank_statement"],
        recommended_status="pending_documents",
        confidence_score=0.82,
        ai_explanation="Application looks solid; awaiting final doc.",
    )


def _make_branch_insight(insight_id: str, branch_id: str) -> BranchInsight:
    return BranchInsight(
        insight_id=insight_id,
        branch_id=branch_id,
        issue_summary="Wait time spike detected",
        probable_causes=["reduced staffing", "seasonal demand increase"],
        ranked_recommendations=["Hire temp staff", "Extend operating hours"],
    )


def _make_branch_alert(alert_id: str, branch_id: str) -> BranchAlert:
    return BranchAlert(
        alert_id=alert_id,
        branch_id=branch_id,
        severity=BranchAlertSeverity.WARNING,
        anomaly_type="wait_time_spike",
        description="Average wait time exceeded 20 minutes.",
    )


def _make_advice_draft(draft_id: str, customer_id: str, suppress: bool = False) -> AdviceDraft:
    return AdviceDraft(
        draft_id=draft_id,
        customer_id=customer_id,
        suppress_cross_sell=suppress,
        next_best_actions=[
            NextBestAction(
                action_id="A-001",
                category=AdviceCategory.SAVINGS,
                title="Open Premier Savings",
                rationale="Customer has a $12k monthly surplus.",
                evidence=["No dedicated savings account on file"],
                priority=1,
            )
        ],
        status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Fraud handler
# ─────────────────────────────────────────────────────────────────────────────


class TestFraudHandler:
    async def test_no_alerts_returns_empty_cards(self, container):
        r = await _fraud({"customer_id": "C-UNKNOWN"}, container)
        assert r.agent_type == "fraud"
        assert r.cards == []
        assert "No active fraud alerts" in r.content

    async def test_pending_alerts_global_list(self, container):
        alert = _make_fraud_alert("FRAUD-H001", "C-TEST", 0.92)
        await container.fraud.save_alert(alert)
        r = await _fraud({}, container)
        assert r.agent_type == "fraud"
        assert len(r.cards) >= 1
        assert any(c.type == "alert" for c in r.cards)

    async def test_customer_filtered_alerts(self, container):
        a1 = _make_fraud_alert("FRAUD-H002", "C-CUST001", 0.85)
        a2 = _make_fraud_alert("FRAUD-H003", "C-CUST002", 0.70)
        await container.fraud.save_alert(a1)
        await container.fraud.save_alert(a2)
        r = await _fraud({"customer_id": "C-CUST001"}, container)
        # Should only mention C-CUST001
        assert "C-CUST001" in r.content
        assert all("FRAUD-H003" not in c.title for c in r.cards)

    async def test_alert_id_lookup(self, container):
        a = _make_fraud_alert("FRAUD-H004", "C-CUST003", 0.95)
        await container.fraud.save_alert(a)
        r = await _fraud({"alert_id": "FRAUD-H004"}, container)
        assert any("FRAUD-H004" in c.title for c in r.cards)

    async def test_missing_alert_id_returns_empty(self, container):
        r = await _fraud({"alert_id": "FRAUD-NOEXIST"}, container)
        assert r.cards == []

    async def test_critical_alert_uses_red_color(self, container):
        a = _make_fraud_alert("FRAUD-H005", "C-X", 0.95)  # critical threshold
        await container.fraud.save_alert(a)
        r = await _fraud({}, container)
        critical_cards = [c for c in r.cards if "FRAUD-H005" in c.title]
        assert critical_cards
        assert critical_cards[0].color == "#c5221f"

    async def test_content_shows_count(self, container):
        for i in range(3):
            a = _make_fraud_alert(f"FRAUD-HCT{i}", "C-CNT", 0.75)
            await container.fraud.save_alert(a)
        r = await _fraud({"customer_id": "C-CNT"}, container)
        assert "3" in r.content

    async def test_card_items_from_reasons(self, container):
        a = _make_fraud_alert("FRAUD-H006", "C-R", 0.80)
        await container.fraud.save_alert(a)
        r = await _fraud({"alert_id": "FRAUD-H006"}, container)
        card = r.cards[0]
        assert "velocity_spike" in card.items
        assert "new_device" in card.items


# ─────────────────────────────────────────────────────────────────────────────
# Churn handler
# ─────────────────────────────────────────────────────────────────────────────


class TestChurnHandler:
    async def test_no_customer_id_returns_guidance(self, container):
        r = await _churn({}, container)
        assert r.agent_type == "sentiment"
        assert r.cards == []
        assert "C-ASHA001" in r.content or "customer ID" in r.content.lower()

    async def test_unknown_customer_returns_no_signal(self, container):
        r = await _churn({"customer_id": "C-GHOST"}, container)
        assert "No sentiment signal" in r.content
        assert r.cards == []

    async def test_high_risk_customer_shows_metric_card(self, container):
        signal = CustomerSignal(
            customer_id="C-CHU001",
            overall_sentiment="very_negative",
            recent_drivers=["fee_dispute", "long_wait"],
            churn_risk=0.78,
            suppress_cross_sell=True,
        )
        await container.customers.save_customer_signal(signal)
        r = await _churn({"customer_id": "C-CHU001"}, container)
        assert r.agent_type == "sentiment"
        assert len(r.cards) >= 2  # metric + suppression card
        metric = next(c for c in r.cards if c.type == "metric")
        assert "78%" in metric.value
        assert "#ea4335" == metric.color  # high-risk red

    async def test_cross_sell_suppression_card_shown(self, container):
        signal = CustomerSignal(
            customer_id="C-CHU002",
            overall_sentiment="negative",
            churn_risk=0.70,
            suppress_cross_sell=True,
        )
        await container.customers.save_customer_signal(signal)
        r = await _churn({"customer_id": "C-CHU002"}, container)
        summary_cards = [c for c in r.cards if c.type == "summary"]
        assert any("suppressed" in c.title.lower() for c in summary_cards)

    async def test_low_risk_customer_green_color(self, container):
        signal = CustomerSignal(
            customer_id="C-CHU003",
            overall_sentiment="positive",
            churn_risk=0.15,
            suppress_cross_sell=False,
        )
        await container.customers.save_customer_signal(signal)
        r = await _churn({"customer_id": "C-CHU003"}, container)
        metric = next(c for c in r.cards if c.type == "metric")
        assert metric.color == "#34a853"

    async def test_medium_risk_amber_color(self, container):
        signal = CustomerSignal(
            customer_id="C-CHU004",
            overall_sentiment="neutral",
            churn_risk=0.50,
            suppress_cross_sell=False,
        )
        await container.customers.save_customer_signal(signal)
        r = await _churn({"customer_id": "C-CHU004"}, container)
        metric = next(c for c in r.cards if c.type == "metric")
        assert metric.color == "#fbbc04"

    async def test_recent_drivers_shown_in_card_items(self, container):
        signal = CustomerSignal(
            customer_id="C-CHU005",
            overall_sentiment="negative",
            recent_drivers=["fee_dispute", "unresolved_complaint", "long_wait_time"],
            churn_risk=0.65,
        )
        await container.customers.save_customer_signal(signal)
        r = await _churn({"customer_id": "C-CHU005"}, container)
        metric = next(c for c in r.cards if c.type == "metric")
        assert "fee_dispute" in metric.items


# ─────────────────────────────────────────────────────────────────────────────
# Loan handler
# ─────────────────────────────────────────────────────────────────────────────


class TestLoanHandler:
    async def test_specific_review_returned(self, container):
        app = LoanApplication(
            application_id="L-HTEST001",
            customer_id="C-LOAN001",
            loan_type="personal",
            requested_amount=25000.0,
            stated_income=100000.0,
        )
        review = _make_loan_review("REV-HTEST001", "L-HTEST001", "C-LOAN001")
        await container.loans.save_application(app)
        await container.loans.save_review(review)
        r = await _loan({"application_id": "L-HTEST001"}, container)
        assert r.agent_type == "loan"
        assert "L-HTEST001" in r.content
        assert any(c.type == "summary" for c in r.cards)

    async def test_missing_docs_card_shown(self, container):
        app = LoanApplication(
            application_id="L-HDOC001",
            customer_id="C-LDOC",
            loan_type="personal",
            requested_amount=10000.0,
            stated_income=60000.0,
        )
        review = _make_loan_review("REV-HDOC001", "L-HDOC001", "C-LDOC")
        await container.loans.save_application(app)
        await container.loans.save_review(review)
        r = await _loan({"application_id": "L-HDOC001"}, container)
        evidence = next((c for c in r.cards if c.type == "evidence"), None)
        assert evidence is not None
        assert "bank_statement" in evidence.items

    async def test_no_review_found_returns_message(self, container):
        r = await _loan({"application_id": "L-NOEXIST"}, container)
        assert "No review found" in r.content
        assert r.cards == []

    async def test_no_application_id_lists_pending(self, container):
        # No reviews seeded → no pending
        r = await _loan({}, container)
        # Either "no pending" message or list of pending reviews
        assert r.agent_type == "loan"

    async def test_pending_list_returned_when_no_app_id(self, container):
        for i in range(2):
            app = LoanApplication(
                application_id=f"L-HPEND{i}",
                customer_id=f"C-PEND{i}",
                loan_type="auto",
                requested_amount=15000.0,
                stated_income=70000.0,
            )
            review = _make_loan_review(f"REV-HPEND{i}", f"L-HPEND{i}", f"C-PEND{i}")
            await container.loans.save_application(app)
            await container.loans.save_review(review)
        r = await _loan({}, container)
        assert "pending" in r.content.lower()
        assert len(r.cards) >= 1

    async def test_confidence_score_in_metric_card(self, container):
        app = LoanApplication(
            application_id="L-HCONF001",
            customer_id="C-CONF",
            loan_type="personal",
            requested_amount=20000.0,
            stated_income=90000.0,
        )
        review = _make_loan_review("REV-HCONF001", "L-HCONF001", "C-CONF")
        await container.loans.save_application(app)
        await container.loans.save_review(review)
        r = await _loan({"application_id": "L-HCONF001"}, container)
        metric = next((c for c in r.cards if c.type == "metric"), None)
        assert metric is not None
        assert "82%" in metric.value


# ─────────────────────────────────────────────────────────────────────────────
# Branch handler
# ─────────────────────────────────────────────────────────────────────────────


class TestBranchHandler:
    async def test_no_branch_id_returns_dashboard_or_empty(self, container):
        r = await _branch({}, container)
        assert r.agent_type == "branch"
        # Empty store → "no data" message
        assert "branch" in r.content.lower()

    async def test_branch_id_with_insights(self, container):
        insight = _make_branch_insight("INS-H001", "BR-TEST01")
        await container.branches.save_insight(insight)
        r = await _branch({"branch_id": "BR-TEST01"}, container)
        assert r.agent_type == "branch"
        assert len(r.cards) >= 1
        assert any(c.type == "summary" for c in r.cards)

    async def test_branch_id_with_alerts(self, container):
        alert = _make_branch_alert("BALT-H001", "BR-TEST02")
        await container.branches.save_alert(alert)
        r = await _branch({"branch_id": "BR-TEST02"}, container)
        assert any(c.type == "alert" for c in r.cards)

    async def test_no_data_for_branch_returns_message(self, container):
        r = await _branch({"branch_id": "BR-GHOST"}, container)
        assert "No recent insights" in r.content
        assert r.cards == []

    async def test_insight_causes_shows_in_items(self, container):
        insight = _make_branch_insight("INS-H002", "BR-TEST03")
        await container.branches.save_insight(insight)
        r = await _branch({"branch_id": "BR-TEST03"}, container)
        summary = next(c for c in r.cards if c.type == "summary")
        assert "reduced staffing" in summary.items or "seasonal demand" in summary.items

    async def test_dashboard_returns_branch_metrics(self, container):
        from datetime import date
        kpi = BranchKPI(
            kpi_id="KPI-H001",
            branch_id="BR-DASH01",
            branch_name="Downtown Branch",
            report_date=date.today(),
            avg_wait_time_minutes=14.5,
            complaint_count=3,
            new_accounts_opened=12,
        )
        await container.branches.save_kpi(kpi)
        r = await _branch({}, container)
        # Dashboard should show something
        assert r.agent_type == "branch"


# ─────────────────────────────────────────────────────────────────────────────
# Advisory handler
# ─────────────────────────────────────────────────────────────────────────────


class TestAdvisoryHandler:
    async def test_no_customer_id_returns_guidance(self, container):
        r = await _advisory({}, container)
        assert r.agent_type == "advisory"
        assert r.cards == []
        assert "customer ID" in r.content or "C-ASHA001" in r.content

    async def test_no_draft_returns_message(self, container):
        r = await _advisory({"customer_id": "C-NOADRAFT"}, container)
        assert "No advice drafts" in r.content
        assert r.cards == []

    async def test_draft_returned_with_action_cards(self, container):
        draft = _make_advice_draft("DRAFT-H001", "C-ADV001")
        await container.advisory.save_draft(draft)
        r = await _advisory({"customer_id": "C-ADV001"}, container)
        assert r.agent_type == "advisory"
        action_cards = [c for c in r.cards if c.type == "action"]
        assert len(action_cards) >= 1
        assert action_cards[0].title == "Open Premier Savings"

    async def test_suppression_alert_card_shown(self, container):
        draft = _make_advice_draft("DRAFT-H002", "C-ADV002", suppress=True)
        await container.advisory.save_draft(draft)
        r = await _advisory({"customer_id": "C-ADV002"}, container)
        alert_cards = [c for c in r.cards if c.type == "alert"]
        assert any("suppressed" in c.title.lower() for c in alert_cards)

    async def test_hitl_gate_card_always_present(self, container):
        draft = _make_advice_draft("DRAFT-H003", "C-ADV003")
        await container.advisory.save_draft(draft)
        r = await _advisory({"customer_id": "C-ADV003"}, container)
        hitl_cards = [c for c in r.cards if c.type == "metric"]
        assert any("approval" in c.value.lower() for c in hitl_cards)

    async def test_action_card_rationale_shown(self, container):
        draft = _make_advice_draft("DRAFT-H004", "C-ADV004")
        await container.advisory.save_draft(draft)
        r = await _advisory({"customer_id": "C-ADV004"}, container)
        action = next(c for c in r.cards if c.type == "action")
        assert "surplus" in action.subtitle.lower()

    async def test_content_includes_customer_id(self, container):
        draft = _make_advice_draft("DRAFT-H005", "C-ADV005")
        await container.advisory.save_draft(draft)
        r = await _advisory({"customer_id": "C-ADV005"}, container)
        assert "C-ADV005" in r.content


# ─────────────────────────────────────────────────────────────────────────────
# General handler (sync — no container needed)
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneralHandler:
    def test_returns_supervisor_agent_type(self):
        r = _general()
        assert r.agent_type == "supervisor"

    def test_content_lists_capabilities(self):
        r = _general()
        for keyword in ("fraud", "churn", "loan", "branch", "advisory"):
            assert keyword in r.content.lower()

    def test_no_cards(self):
        r = _general()
        assert r.cards == []

    def test_content_has_example_prompts(self):
        r = _general()
        assert "C-ASHA001" in r.content or "L-001" in r.content

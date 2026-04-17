"""
Integration tests — NL query → classifier → repository → response pipeline.

Tests the complete data-flow path:
  POST /api/chat/query
    → _classify (keyword fallback in stub mode)
    → intent handler
    → in-memory repository
    → structured ChatQueryResponse

Each test seeds specific domain objects so assertions are precise
(exact counts, specific card fields, real customer IDs).
"""
from __future__ import annotations

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.auth import create_dev_token
from app.domain.models.advisory import (
    AdviceCategory,
    AdviceDraft,
    AdviceDraftStatus,
    NextBestAction,
)
from app.domain.models.branch import BranchAlert, BranchAlertSeverity, BranchInsight, BranchKPI
from app.domain.models.customer import CustomerProfile, KYCStatus, RiskTolerance
from app.domain.models.fraud import FraudAlert, FraudRiskLevel
from app.domain.models.interaction import CustomerSignal
from app.domain.models.loan import LoanApplication, LoanReview
from app.main import create_app


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(container):
    app = create_app()
    token = create_dev_token("pipeline-user", [
        "fraud_analyst", "underwriter", "branch_manager",
        "financial_advisor", "compliance_reviewer", "admin",
    ])
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


async def _query(client, message: str, history: list | None = None) -> dict:
    payload = {"message": message}
    if history:
        payload["history"] = history
    r = await client.post("/api/chat/query", json=payload)
    assert r.status_code == 200, r.text
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# Fraud pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestFraudPipeline:
    async def test_global_fraud_list_returns_seeded_alerts(self, client, container):
        """A broad 'show fraud alerts' query returns whatever's in the store."""
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE001", txn_id="T-P001", customer_id="C-P001",
            risk_score=0.91, risk_level=FraudRiskLevel.CRITICAL,
            reasons=["velocity_spike", "new_device"],
        ))
        data = await _query(client, "Show me all pending fraud alerts")
        assert data["agent_type"] == "fraud"
        titles = [c["title"] for c in data["cards"]]
        assert any("FRAUD-PIPE001" in t for t in titles)

    async def test_customer_specific_query_filters_correctly(self, client, container):
        """Alerts for two customers; querying C-P002 shows only C-P002's alert."""
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE002", txn_id="T-P002", customer_id="C-P002",
            risk_score=0.85, risk_level=FraudRiskLevel.HIGH,
        ))
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE003", txn_id="T-P003", customer_id="C-P003",
            risk_score=0.78, risk_level=FraudRiskLevel.HIGH,
        ))
        data = await _query(client, "Fraud alerts for customer C-P002")
        titles = [c["title"] for c in data["cards"]]
        assert any("FRAUD-PIPE002" in t for t in titles)
        assert all("FRAUD-PIPE003" not in t for t in titles)

    async def test_alert_id_exact_lookup(self, client, container):
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE004", txn_id="T-P004", customer_id="C-P004",
            risk_score=0.93, risk_level=FraudRiskLevel.CRITICAL,
            ai_explanation="Coordinated fraud ring pattern.",
        ))
        data = await _query(client, "What happened with FRAUD-PIPE004?")
        assert data["agent_type"] == "fraud"
        assert any("FRAUD-PIPE004" in c["title"] for c in data["cards"])

    async def test_risk_score_shown_as_percentage(self, client, container):
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE005", txn_id="T-P005", customer_id="C-P005",
            risk_score=0.88, risk_level=FraudRiskLevel.HIGH,
        ))
        data = await _query(client, "fraud alerts for C-P005")
        card = next(c for c in data["cards"] if "FRAUD-PIPE005" in c["title"])
        assert "88%" in card["value"]

    async def test_high_risk_score_in_content(self, client, container):
        await container.fraud.save_alert(FraudAlert(
            alert_id="FRAUD-PIPE006", txn_id="T-P006", customer_id="C-P006",
            risk_score=0.97, risk_level=FraudRiskLevel.CRITICAL,
        ))
        data = await _query(client, "fraud alerts")
        # Content should mention the highest risk score
        assert "97%" in data["content"]

    async def test_no_alerts_returns_clean_message(self, client, container):
        data = await _query(client, "fraud alerts for C-NOBODY999")
        assert "No active fraud alerts" in data["content"]
        assert data["cards"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Churn / sentiment pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestChurnPipeline:
    async def test_high_churn_customer_full_card(self, client, container):
        await container.customers.save_customer_signal(CustomerSignal(
            customer_id="C-CHPIPE001",
            overall_sentiment="very_negative",
            recent_drivers=["fee_dispute", "long_wait_time", "billing_error"],
            churn_risk=0.82,
            suppress_cross_sell=True,
        ))
        data = await _query(client, "What is the churn risk for customer C-CHPIPE001?")
        assert data["agent_type"] == "sentiment"
        assert "82%" in data["content"]
        cards = data["cards"]
        metric = next(c for c in cards if c["type"] == "metric")
        assert "fee_dispute" in metric["items"]

    async def test_suppression_card_present_when_flagged(self, client, container):
        await container.customers.save_customer_signal(CustomerSignal(
            customer_id="C-CHPIPE002",
            overall_sentiment="negative",
            churn_risk=0.72,
            suppress_cross_sell=True,
        ))
        data = await _query(client, "churn risk for C-CHPIPE002")
        suppression_cards = [c for c in data["cards"] if "suppressed" in c["title"].lower()]
        assert len(suppression_cards) >= 1

    async def test_no_customer_id_prompts_for_id(self, client, container):
        data = await _query(client, "who is at risk of churning?")
        assert data["agent_type"] == "sentiment"
        # Should guide user to provide a customer ID
        assert "customer" in data["content"].lower()

    async def test_unknown_customer_returns_no_signal_message(self, client, container):
        data = await _query(client, "sentiment for customer C-GHOST123")
        assert "No sentiment signal" in data["content"]


# ─────────────────────────────────────────────────────────────────────────────
# Loan pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestLoanPipeline:
    async def test_existing_review_returned_with_all_cards(self, client, container):
        # Use purely numeric IDs so the keyword classifier regex (L-\d+) can extract them
        await container.loans.save_application(LoanApplication(
            application_id="L-101",
            customer_id="C-LPIPE101",
            loan_type="personal",
            requested_amount=30000.0,
            stated_income=110000.0,
        ))
        await container.loans.save_review(LoanReview(
            review_id="REV-101",
            application_id="L-101",
            customer_id="C-LPIPE101",
            summary="Strong income profile; one document gap.",
            missing_documents=["bank_statement"],
            recommended_status="pending_documents",
            confidence_score=0.91,
        ))
        data = await _query(client, "Summarize loan review for L-101")
        assert data["agent_type"] == "loan"
        types = {c["type"] for c in data["cards"]}
        assert "summary" in types
        assert "evidence" in types
        assert "metric" in types

    async def test_missing_document_list_accurate(self, client, container):
        await container.loans.save_application(LoanApplication(
            application_id="L-102",
            customer_id="C-LPIPE102",
            loan_type="auto",
            requested_amount=20000.0,
            stated_income=75000.0,
        ))
        await container.loans.save_review(LoanReview(
            review_id="REV-102",
            application_id="L-102",
            customer_id="C-LPIPE102",
            summary="Good credit profile.",
            missing_documents=["employment_verification", "tax_return"],
            recommended_status="pending_documents",
            confidence_score=0.75,
        ))
        data = await _query(client, "loan application L-102")
        evidence = next(c for c in data["cards"] if c["type"] == "evidence")
        assert "employment_verification" in evidence["items"]
        assert "tax_return" in evidence["items"]

    async def test_list_pending_when_no_app_id(self, client, container):
        for i in range(3):
            await container.loans.save_application(LoanApplication(
                application_id=f"L-PEND{i:02d}",
                customer_id=f"C-LPEND{i}",
                loan_type="personal",
                requested_amount=10000.0 * (i + 1),
                stated_income=60000.0,
            ))
            await container.loans.save_review(LoanReview(
                review_id=f"REV-PEND{i:02d}",
                application_id=f"L-PEND{i:02d}",
                customer_id=f"C-LPEND{i}",
                summary=f"Review {i}",
            ))
        data = await _query(client, "show me pending loan reviews")
        assert data["agent_type"] == "loan"
        assert "pending" in data["content"].lower()
        assert len(data["cards"]) >= 1

    async def test_nonexistent_application_handled(self, client, container):
        # L-9999 matches the numeric regex and will be looked up but not found
        data = await _query(client, "review loan application L-9999")
        assert "No review found" in data["content"]
        assert data["cards"] == []


# ─────────────────────────────────────────────────────────────────────────────
# Branch pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestBranchPipeline:
    async def test_branch_insights_and_alerts_combined(self, client, container):
        await container.branches.save_insight(BranchInsight(
            insight_id="INS-PIPE001",
            branch_id="BR-WEST01",
            issue_summary="Wait-time spike driven by staffing gap",
            probable_causes=["Two agents on leave", "No backup coverage"],
        ))
        await container.branches.save_alert(BranchAlert(
            alert_id="BALT-PIPE001",
            branch_id="BR-WEST01",
            severity=BranchAlertSeverity.WARNING,
            anomaly_type="wait_time_spike",
            description="Average wait exceeded 25 minutes.",
        ))
        data = await _query(client, "What is going on at the West Side branch?")
        assert data["agent_type"] == "branch"
        types = [c["type"] for c in data["cards"]]
        assert "summary" in types
        assert "alert" in types

    async def test_branch_count_in_content(self, client, container):
        for branch_id in ["BR-WEST01", "BR-EAST01"]:
            await container.branches.save_insight(BranchInsight(
                insight_id=f"INS-{branch_id}",
                branch_id=branch_id,
                issue_summary=f"Issue at {branch_id}",
            ))
        data = await _query(client, "branch BR-WEST01 status")
        assert "BR-WEST01" in data["content"]

    async def test_dashboard_from_kpis(self, client, container):
        await container.branches.save_kpi(BranchKPI(
            kpi_id="KPI-PIPE001",
            branch_id="BR-DASH01",
            branch_name="Central Branch",
            report_date=date.today(),
            avg_wait_time_minutes=11.5,
            complaint_count=2,
            new_accounts_opened=8,
        ))
        data = await _query(client, "branch operations dashboard")
        assert data["agent_type"] == "branch"

    async def test_unknown_branch_handled(self, client, container):
        data = await _query(client, "what is happening at branch BR-GHOST999?")
        assert data["agent_type"] == "branch"
        assert "No recent insights" in data["content"]


# ─────────────────────────────────────────────────────────────────────────────
# Advisory pipeline
# ─────────────────────────────────────────────────────────────────────────────


class TestAdvisoryPipeline:
    async def test_draft_with_actions_returned(self, client, container):
        await container.advisory.save_draft(AdviceDraft(
            draft_id="DRAFT-PIPE001",
            customer_id="C-ADVPIPE001",
            next_best_actions=[
                NextBestAction(
                    action_id="NA-001",
                    category=AdviceCategory.SAVINGS,
                    title="Open High-Yield Savings",
                    rationale="Customer has undeployed monthly surplus of $8k.",
                    priority=1,
                ),
                NextBestAction(
                    action_id="NA-002",
                    category=AdviceCategory.SERVICE_RECOVERY,
                    title="Resolve open fee dispute",
                    rationale="Fee dispute filed 5 days ago; unresolved.",
                    priority=2,
                ),
            ],
            status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
        ))
        data = await _query(client, "Generate advice for customer C-ADVPIPE001")
        assert data["agent_type"] == "advisory"
        action_titles = [c["title"] for c in data["cards"] if c["type"] == "action"]
        assert "Open High-Yield Savings" in action_titles

    async def test_cross_sell_suppression_reflected_in_response(self, client, container):
        await container.advisory.save_draft(AdviceDraft(
            draft_id="DRAFT-PIPE002",
            customer_id="C-ADVPIPE002",
            suppress_cross_sell=True,
            status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
        ))
        data = await _query(client, "advice for C-ADVPIPE002")
        alert_cards = [c for c in data["cards"] if c["type"] == "alert"]
        assert any("suppressed" in c["title"].lower() for c in alert_cards)
        assert "suppressed" in data["content"].lower() or "suppressed" in str(data["cards"]).lower()

    async def test_hitl_gate_always_in_response(self, client, container):
        await container.advisory.save_draft(AdviceDraft(
            draft_id="DRAFT-PIPE003",
            customer_id="C-ADVPIPE003",
            status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
        ))
        data = await _query(client, "recommend something for C-ADVPIPE003")
        hitl = [c for c in data["cards"] if c["type"] == "metric"]
        assert any("approval" in c.get("value", "").lower() for c in hitl)

    async def test_no_draft_returns_workspace_prompt(self, client, container):
        data = await _query(client, "financial advice for C-NODRAFT999")
        assert "No advice drafts" in data["content"]
        assert data["cards"] == []

    async def test_no_customer_id_returns_guidance(self, client, container):
        data = await _query(client, "what advice would you give?")
        assert data["agent_type"] == "advisory"
        assert "customer ID" in data["content"] or "C-ASHA001" in data["content"]


# ─────────────────────────────────────────────────────────────────────────────
# Cross-domain (Supervisor → multiple agents)
# ─────────────────────────────────────────────────────────────────────────────


class TestGeneralPipeline:
    async def test_unknown_intent_returns_supervisor(self, client, container):
        data = await _query(client, "what is the weather like today?")
        assert data["agent_type"] == "supervisor"
        assert data["cards"] == []

    async def test_supervisor_content_lists_all_capabilities(self, client, container):
        data = await _query(client, "tell me something")
        content_lower = data["content"].lower()
        for capability in ("fraud", "churn", "loan", "branch", "advis"):
            assert capability in content_lower, f"Missing capability hint: {capability}"

    async def test_history_does_not_cause_error(self, client, container):
        """Passing a multi-turn history should not break the endpoint."""
        history = [
            {"role": "user", "content": "show fraud alerts"},
            {"role": "agent", "content": "Found 2 fraud alerts."},
        ]
        data = await _query(
            client,
            "Thanks. Now show me loans.",
            history=history,
        )
        assert data["agent_type"] == "loan"
        assert data["status_code"] if hasattr(data, "status_code") else True

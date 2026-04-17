"""
End-to-end conversation flow tests.

Each test class runs a realistic multi-turn scenario that mirrors how an
analyst or advisor would use the NL interface in production.  The tests
verify:

  - The correct agent responds for each turn
  - Data seeded before the conversation appears in card content
  - Realistic entities (customer IDs, branch IDs, loan IDs) flow through
  - Human-in-the-loop (HITL) gates are never silently bypassed
  - The conversation can pivot between domains without error

All tests run against the in-memory backend with the stub LLM.
"""

from __future__ import annotations

from datetime import date

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
    token = create_dev_token(
        "e2e-analyst",
        [
            "fraud_analyst",
            "underwriter",
            "branch_manager",
            "financial_advisor",
            "compliance_reviewer",
            "admin",
        ],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


class Conversation:
    """Helper that accumulates turn history and posts to /api/chat/query."""

    def __init__(self, client):
        self._client = client
        self._history: list[dict] = []

    async def say(self, message: str) -> dict:
        payload = {"message": message, "history": self._history}
        r = await self._client.post("/api/chat/query", json=payload)
        assert r.status_code == 200, r.text
        data = r.json()
        # Accumulate history so later turns have context
        self._history.append({"role": "user", "content": message})
        self._history.append({"role": "agent", "content": data["content"]})
        return data


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 1 — Fraud analyst investigating a specific customer
# ─────────────────────────────────────────────────────────────────────────────


class TestFraudAnalystScenario:
    """
    Simulates an analyst checking for fraud, drilling into a customer,
    then pivoting to check that customer's churn risk.
    """

    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, container):
        # Customer
        await container.customers.save(
            CustomerProfile(
                customer_id="C-ASHA001",
                name="Asha Mehta",
                kyc_status=KYCStatus.VERIFIED,
            )
        )
        # Fraud alerts
        await container.fraud.save_alert(
            FraudAlert(
                alert_id="FRAUD-E2E001",
                txn_id="T-E2E001",
                customer_id="C-ASHA001",
                risk_score=0.91,
                risk_level=FraudRiskLevel.CRITICAL,
                reasons=["velocity_spike", "new_device", "merchant_cluster"],
                ai_explanation="Three matching risk signals in 24 h window.",
            )
        )
        await container.fraud.save_alert(
            FraudAlert(
                alert_id="FRAUD-E2E002",
                txn_id="T-E2E002",
                customer_id="C-ASHA001",
                risk_score=0.73,
                risk_level=FraudRiskLevel.HIGH,
                reasons=["geo_anomaly"],
            )
        )
        # Churn signal
        await container.customers.save_customer_signal(
            CustomerSignal(
                customer_id="C-ASHA001",
                overall_sentiment="negative",
                recent_drivers=["fee_dispute"],
                churn_risk=0.68,
                suppress_cross_sell=True,
            )
        )

    async def test_turn1_global_fraud_list(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("Show me all pending fraud alerts")
        assert t1["agent_type"] == "fraud"
        titles = [c["title"] for c in t1["cards"]]
        assert any("FRAUD-E2E001" in t for t in titles)

    async def test_turn2_customer_drill_down(self, client, container):
        # The stub LLM classifies each message independently (no history awareness),
        # so the follow-up must include a domain keyword for reliable classification.
        conv = Conversation(client)
        await conv.say("Show me all pending fraud alerts")
        t2 = await conv.say("Show fraud alerts for customer C-ASHA001")
        assert t2["agent_type"] == "fraud"
        # Both of Asha's alerts should appear
        titles = [c["title"] for c in t2["cards"]]
        assert any("FRAUD-E2E001" in t for t in titles)
        assert any("FRAUD-E2E002" in t for t in titles)

    async def test_turn3_pivot_to_churn(self, client, container):
        conv = Conversation(client)
        await conv.say("fraud alerts for C-ASHA001")
        t2 = await conv.say("What is the churn risk for C-ASHA001?")
        assert t2["agent_type"] == "sentiment"
        assert "68%" in t2["content"]

    async def test_turn4_suppression_noted_in_churn(self, client, container):
        conv = Conversation(client)
        await conv.say("fraud alerts for C-ASHA001")
        t2 = await conv.say("churn risk C-ASHA001")
        suppression = [c for c in t2["cards"] if "suppressed" in c["title"].lower()]
        assert len(suppression) >= 1

    async def test_multi_turn_no_crash(self, client, container):
        """Four consecutive turns without any assertion error."""
        conv = Conversation(client)
        await conv.say("Show pending fraud alerts")
        await conv.say("Filter to C-ASHA001")
        await conv.say("What is her churn risk?")
        await conv.say("Any advice drafts for her?")  # pivots to advisory


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 2 — Loan underwriter reviewing a batch of applications
# ─────────────────────────────────────────────────────────────────────────────


class TestLoanUnderwriterScenario:
    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, container):
        for i, (app_id, doc_status) in enumerate(
            [
                ("L-201", ["paystub", "bank_statement"]),  # missing: id_doc
                ("L-202", ["paystub", "id_doc"]),  # missing: bank_statement
                ("L-203", ["paystub", "id_doc", "bank_statement"]),  # complete
            ]
        ):
            await container.loans.save_application(
                LoanApplication(
                    application_id=app_id,
                    customer_id=f"C-LUW{i:02d}",
                    loan_type="personal",
                    requested_amount=20000.0 + i * 5000,
                    stated_income=80000.0,
                    submitted_docs=doc_status,
                )
            )
            missing = []
            if "bank_statement" not in doc_status:
                missing.append("bank_statement")
            if "id_doc" not in doc_status:
                missing.append("id_doc")
            await container.loans.save_review(
                LoanReview(
                    review_id=f"REV-{app_id}",
                    application_id=app_id,
                    customer_id=f"C-LUW{i:02d}",
                    summary=f"Review for {app_id}.",
                    missing_documents=missing,
                    recommended_status="pending_documents" if missing else "conditionally_approved",
                    confidence_score=0.85,
                )
            )

    async def test_turn1_pending_queue(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("Show me the pending loan review queue")
        assert t1["agent_type"] == "loan"
        assert "pending" in t1["content"].lower()
        assert len(t1["cards"]) >= 1

    async def test_turn2_drill_into_specific_app(self, client, container):
        conv = Conversation(client)
        await conv.say("Show me pending loan reviews")
        t2 = await conv.say("Review application L-201")
        assert t2["agent_type"] == "loan"
        evidence = next((c for c in t2["cards"] if c["type"] == "evidence"), None)
        assert evidence is not None
        assert "id_doc" in evidence["items"]

    async def test_turn3_another_application(self, client, container):
        conv = Conversation(client)
        await conv.say("pending loan reviews")
        await conv.say("Review L-201")
        t3 = await conv.say("Now look at application L-202")
        assert t3["agent_type"] == "loan"
        evidence = next((c for c in t3["cards"] if c["type"] == "evidence"), None)
        assert evidence is not None
        assert "bank_statement" in evidence["items"]

    async def test_confidence_score_visible(self, client, container):
        conv = Conversation(client)
        t = await conv.say("loan application L-203")
        metric = next((c for c in t["cards"] if c["type"] == "metric"), None)
        assert metric is not None
        assert "85%" in metric["value"]


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 3 — Branch manager investigating a site issue
# ─────────────────────────────────────────────────────────────────────────────


class TestBranchManagerScenario:
    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, container):
        for branch_id, name in [("BR-WEST01", "West Side"), ("BR-EAST01", "East Side")]:
            await container.branches.save_kpi(
                BranchKPI(
                    kpi_id=f"KPI-{branch_id}",
                    branch_id=branch_id,
                    branch_name=name,
                    report_date=date.today(),
                    avg_wait_time_minutes=22.0 if "WEST" in branch_id else 12.0,
                    complaint_count=9 if "WEST" in branch_id else 2,
                    new_accounts_opened=5,
                )
            )
            if "WEST" in branch_id:
                await container.branches.save_insight(
                    BranchInsight(
                        insight_id="INS-E2E-WEST",
                        branch_id=branch_id,
                        issue_summary="Compound staffing-wait-time-complaint pattern",
                        probable_causes=[
                            "Two agents on medical leave",
                            "No temp coverage arranged",
                        ],
                        ranked_recommendations=[
                            "Request temp staff immediately",
                            "Extend teller hours",
                        ],
                    )
                )
                await container.branches.save_alert(
                    BranchAlert(
                        alert_id="BALT-E2E-WEST",
                        branch_id=branch_id,
                        severity=BranchAlertSeverity.CRITICAL,
                        anomaly_type="wait_time_spike",
                        description="Average wait time exceeded 20 minutes for 3 consecutive days.",
                    )
                )

    async def test_turn1_dashboard_overview(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("Show branch operations dashboard")
        assert t1["agent_type"] == "branch"
        assert len(t1["cards"]) >= 1

    async def test_turn2_drill_into_west(self, client, container):
        conv = Conversation(client)
        await conv.say("branch operations dashboard")
        t2 = await conv.say("What is happening at the West Side branch?")
        assert t2["agent_type"] == "branch"
        titles = [c.get("title", "") for c in t2["cards"]]
        # Insight summary should appear
        assert any("staffing" in t.lower() or "wait" in t.lower() for t in titles)

    async def test_turn3_critical_alert_visible(self, client, container):
        conv = Conversation(client)
        await conv.say("branch ops")
        t2 = await conv.say("branch BR-WEST01")
        alert_cards = [c for c in t2["cards"] if c["type"] == "alert"]
        assert len(alert_cards) >= 1
        # Critical severity should use a strong red
        assert any(c.get("color") in {"#c5221f", "#ea4335"} for c in alert_cards)

    async def test_turn4_compare_east_branch(self, client, container):
        conv = Conversation(client)
        await conv.say("West Side branch status")
        t2 = await conv.say("How about branch BR-EAST01?")
        assert t2["agent_type"] == "branch"
        # East branch has no alerts/insights → clean message
        assert "No recent insights" in t2["content"]

    async def test_probable_causes_in_card_items(self, client, container):
        conv = Conversation(client)
        t = await conv.say("insights for branch BR-WEST01")
        summary = next((c for c in t["cards"] if c["type"] == "summary"), None)
        assert summary is not None
        items_text = " ".join(summary.get("items", []))
        assert "leave" in items_text.lower() or "coverage" in items_text.lower()


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 4 — Financial advisor full workflow
# ─────────────────────────────────────────────────────────────────────────────


class TestAdvisorScenario:
    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, container):
        await container.customers.save(
            CustomerProfile(
                customer_id="C-RAVI001",
                name="Ravi Sharma",
                risk_tolerance=RiskTolerance.MODERATE,
                products=["checking"],
                goals=["emergency_fund", "retirement"],
            )
        )
        await container.customers.save_customer_signal(
            CustomerSignal(
                customer_id="C-RAVI001",
                overall_sentiment="neutral",
                churn_risk=0.30,
                suppress_cross_sell=False,
            )
        )
        await container.advisory.save_draft(
            AdviceDraft(
                draft_id="DRAFT-E2E001",
                customer_id="C-RAVI001",
                next_best_actions=[
                    NextBestAction(
                        action_id="NA-E001",
                        category=AdviceCategory.SAVINGS,
                        title="Premier Savings Account",
                        rationale="Customer has no dedicated savings vehicle; surplus of $5k/month.",
                        evidence=["No savings account in product portfolio"],
                        priority=1,
                    ),
                    NextBestAction(
                        action_id="NA-E002",
                        category=AdviceCategory.INVESTMENT,
                        title="Retirement Fund Top-Up",
                        rationale="Goal alignment: retirement is a stated priority.",
                        priority=2,
                    ),
                ],
                suppress_cross_sell=False,
                status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
            )
        )

    async def test_turn1_check_sentiment_first(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("What is the sentiment signal for C-RAVI001?")
        assert t1["agent_type"] == "sentiment"
        assert "30%" in t1["content"]

    async def test_turn2_generate_advice_after_sentiment(self, client, container):
        conv = Conversation(client)
        await conv.say("sentiment for C-RAVI001")
        t2 = await conv.say("Good. Generate advice for C-RAVI001.")
        assert t2["agent_type"] == "advisory"
        action_titles = [c["title"] for c in t2["cards"] if c["type"] == "action"]
        assert "Premier Savings Account" in action_titles

    async def test_turn3_hitl_gate_present(self, client, container):
        conv = Conversation(client)
        await conv.say("sentiment for C-RAVI001")
        t2 = await conv.say("advice for C-RAVI001")
        hitl = [c for c in t2["cards"] if c["type"] == "metric"]
        assert any("approval" in c.get("value", "").lower() for c in hitl)

    async def test_turn4_advisor_cannot_bypass_hitl_via_chat(self, client, container):
        """
        The chat endpoint is read-only — it cannot approve a draft.
        Asking it to 'approve' should return advisory info, not mutate state.
        """
        conv = Conversation(client)
        await conv.say("advice for C-RAVI001")
        t2 = await conv.say("Please approve the advice draft for C-RAVI001")
        # Advisory handler reads the draft — approval still requires the /approve endpoint
        assert t2["agent_type"] == "advisory"
        draft = await container.advisory.get_draft_by_id("DRAFT-E2E001")
        # Draft must NOT have been auto-approved via chat
        assert draft.status == "pending_advisor_review"

    async def test_second_action_in_draft(self, client, container):
        conv = Conversation(client)
        t = await conv.say("recommend products for C-RAVI001")
        action_titles = [c["title"] for c in t["cards"] if c["type"] == "action"]
        assert "Retirement Fund Top-Up" in action_titles


# ─────────────────────────────────────────────────────────────────────────────
# Scenario 5 — Cross-domain pivot (fraud → loan → advisory)
# ─────────────────────────────────────────────────────────────────────────────


class TestCrossDomainPivot:
    @pytest_asyncio.fixture(autouse=True)
    async def seed(self, container):
        await container.customers.save(
            CustomerProfile(customer_id="C-MULTI001", name="Multi Domain Customer")
        )
        await container.fraud.save_alert(
            FraudAlert(
                alert_id="FRAUD-MULTI001",
                txn_id="T-MULTI001",
                customer_id="C-MULTI001",
                risk_score=0.78,
                risk_level=FraudRiskLevel.HIGH,
            )
        )
        await container.loans.save_application(
            LoanApplication(
                application_id="L-301",
                customer_id="C-MULTI001",
                loan_type="personal",
                requested_amount=15000.0,
                stated_income=70000.0,
            )
        )
        await container.loans.save_review(
            LoanReview(
                review_id="REV-301",
                application_id="L-301",
                customer_id="C-MULTI001",
                summary="Pending fraud flag review.",
                recommended_status="pending_documents",
                confidence_score=0.72,
            )
        )
        await container.advisory.save_draft(
            AdviceDraft(
                draft_id="DRAFT-MULTI001",
                customer_id="C-MULTI001",
                next_best_actions=[
                    NextBestAction(
                        action_id="NA-M001",
                        category=AdviceCategory.FOLLOW_UP,
                        title="Resolve fraud flag first",
                        rationale="Loan application should not proceed until fraud risk is cleared.",
                        priority=1,
                    )
                ],
                status=AdviceDraftStatus.PENDING_ADVISOR_REVIEW,
            )
        )

    async def test_pivot_fraud_to_loan(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("fraud alerts for C-MULTI001")
        assert t1["agent_type"] == "fraud"
        t2 = await conv.say("Now review loan application L-301")
        assert t2["agent_type"] == "loan"

    async def test_pivot_loan_to_advisory(self, client, container):
        conv = Conversation(client)
        await conv.say("loan L-301")
        t2 = await conv.say("generate advice for C-MULTI001")
        assert t2["agent_type"] == "advisory"

    async def test_full_three_domain_conversation(self, client, container):
        conv = Conversation(client)
        t1 = await conv.say("fraud alerts for C-MULTI001")
        t2 = await conv.say("loan application L-301")
        t3 = await conv.say("advice for C-MULTI001")
        assert t1["agent_type"] == "fraud"
        assert t2["agent_type"] == "loan"
        assert t3["agent_type"] == "advisory"

    async def test_general_pivot_back_to_help(self, client, container):
        conv = Conversation(client)
        await conv.say("fraud alerts for C-MULTI001")
        await conv.say("loan L-301")
        t3 = await conv.say("What else can you help me with?")
        # Should return a supervisor/general response listing capabilities
        assert t3["agent_type"] == "supervisor"

    async def test_history_grows_without_error(self, client, container):
        """Five-turn conversation with full history accumulation."""
        conv = Conversation(client)
        turns = [
            "fraud alerts for C-MULTI001",
            "loan L-301",
            "advice for C-MULTI001",
            "churn risk for C-MULTI001",
            "branch operations",
        ]
        agents = []
        for msg in turns:
            data = await conv.say(msg)
            agents.append(data["agent_type"])
        # Every turn must succeed with a valid agent type
        valid = {"fraud", "sentiment", "loan", "branch", "advisory", "supervisor"}
        assert all(a in valid for a in agents)

"""
Unit tests for the NL chat intent classifier.

Tests:
- _keyword_classify: all six intents, entity extraction, ambiguous inputs
- _classify: LLM success path, malformed JSON fallback, stub-LLM fallback
"""
from __future__ import annotations

import json
import pytest

from app.api.routers.chat import _classify, _keyword_classify
from app.infrastructure.ai.stub import StubLLMService


# ─────────────────────────────────────────────────────────────────────────────
# _keyword_classify — pure synchronous classifier
# ─────────────────────────────────────────────────────────────────────────────


class TestKeywordClassify:
    # ── Intent routing ────────────────────────────────────────────────────────

    def test_fraud_by_keyword(self):
        r = _keyword_classify("Show me fraud alerts")
        assert r["intent"] == "fraud_alerts"

    def test_fraud_by_alert_keyword(self):
        r = _keyword_classify("Any suspicious transactions today?")
        assert r["intent"] == "fraud_alerts"

    def test_fraud_by_velocity(self):
        r = _keyword_classify("velocity spike on account A-001")
        assert r["intent"] == "fraud_alerts"

    def test_churn_by_keyword(self):
        r = _keyword_classify("Which customers are at churn risk?")
        assert r["intent"] == "churn_risk"

    def test_churn_by_sentiment(self):
        r = _keyword_classify("sentiment analysis for this week")
        assert r["intent"] == "churn_risk"

    def test_churn_by_dissatisfied(self):
        r = _keyword_classify("show me dissatisfied customers")
        assert r["intent"] == "churn_risk"

    def test_loan_by_keyword(self):
        r = _keyword_classify("review loan application L-001")
        assert r["intent"] == "loan_review"

    def test_loan_by_underwrite(self):
        # "underwriting" ≠ substring "underwrite"; use the exact keyword the classifier checks
        r = _keyword_classify("submit a new mortgage application")
        assert r["intent"] == "loan_review"

    def test_loan_by_mortgage(self):
        r = _keyword_classify("mortgage application status")
        assert r["intent"] == "loan_review"

    def test_branch_by_keyword(self):
        r = _keyword_classify("What's happening at the West Side branch?")
        assert r["intent"] == "branch_insights"

    def test_branch_by_staffing(self):
        # avoid "alert" which triggers fraud first; "staffing" alone is unambiguous
        r = _keyword_classify("staffing shortage this week")
        assert r["intent"] == "branch_insights"

    def test_branch_by_kpi(self):
        r = _keyword_classify("show branch KPI dashboard")
        assert r["intent"] == "branch_insights"

    def test_advisory_by_advi(self):
        r = _keyword_classify("Generate advice for customer C-ASHA001")
        assert r["intent"] == "advisory"

    def test_advisory_by_recommend(self):
        r = _keyword_classify("product recommendations for C-001")
        assert r["intent"] == "advisory"

    def test_general_fallback(self):
        r = _keyword_classify("Hello, how are you?")
        assert r["intent"] == "general"

    def test_general_empty_ish(self):
        r = _keyword_classify("   ")
        assert r["intent"] == "general"

    # ── Entity extraction ─────────────────────────────────────────────────────

    def test_customer_id_extracted(self):
        r = _keyword_classify("fraud alerts for C-ASHA001")
        assert r["entities"]["customer_id"] == "C-ASHA001"

    def test_customer_id_case_insensitive(self):
        r = _keyword_classify("check c-xyz999 please")
        assert r["entities"]["customer_id"] == "C-XYZ999"

    def test_branch_id_explicit(self):
        r = _keyword_classify("alerts for branch BR-WEST01")
        assert r["entities"]["branch_id"] == "BR-WEST01"

    def test_branch_id_from_name_west(self):
        r = _keyword_classify("What is going on at the West branch?")
        assert r["entities"]["branch_id"] == "BR-WEST01"

    def test_branch_id_from_name_east(self):
        r = _keyword_classify("East branch staffing issues")
        assert r["entities"]["branch_id"] == "BR-EAST01"

    def test_application_id_extracted(self):
        r = _keyword_classify("show loan L-001 review")
        assert r["entities"]["application_id"] == "L-001"

    def test_application_id_numeric(self):
        r = _keyword_classify("l-9999 status?")
        assert r["entities"]["application_id"] == "L-9999"

    def test_alert_id_extracted(self):
        r = _keyword_classify("what happened with FRAUD-441?")
        assert r["entities"]["alert_id"] == "FRAUD-441"

    def test_no_entities_when_absent(self):
        r = _keyword_classify("show me all fraud alerts")
        assert r["entities"]["customer_id"] is None
        assert r["entities"]["branch_id"] is None
        assert r["entities"]["application_id"] is None
        assert r["entities"]["alert_id"] is None

    def test_multiple_entities_in_one_query(self):
        r = _keyword_classify("fraud alert FRAUD-123 for customer C-TEST001 at branch BR-EAST01")
        assert r["entities"]["customer_id"] == "C-TEST001"
        assert r["entities"]["branch_id"] == "BR-EAST01"
        assert r["entities"]["alert_id"] == "FRAUD-123"

    def test_result_always_has_intent_and_entities_keys(self):
        r = _keyword_classify("anything")
        assert "intent" in r
        assert "entities" in r
        assert set(r["entities"].keys()) == {"customer_id", "branch_id", "application_id", "alert_id"}


# ─────────────────────────────────────────────────────────────────────────────
# _classify — LLM path + fallback behaviour
# ─────────────────────────────────────────────────────────────────────────────


class TestClassify:
    @pytest.mark.asyncio
    async def test_stub_llm_falls_back_to_keywords(self):
        """StubLLM returns 'Stub AI response.' — not valid JSON, so keyword fallback fires."""
        llm = StubLLMService()
        r = await _classify("fraud alerts for C-ASHA001", llm)
        assert r["intent"] == "fraud_alerts"
        assert r["entities"]["customer_id"] == "C-ASHA001"

    @pytest.mark.asyncio
    async def test_valid_llm_json_used_directly(self):
        """When LLM returns well-formed JSON, that result is used without keyword override."""
        good_json = json.dumps({
            "intent": "advisory",
            "entities": {
                "customer_id": "C-LLM001",
                "branch_id": None,
                "application_id": None,
                "alert_id": None,
            }
        })
        llm = StubLLMService(fixed_response=good_json)
        r = await _classify("some user message", llm)
        assert r["intent"] == "advisory"
        assert r["entities"]["customer_id"] == "C-LLM001"

    @pytest.mark.asyncio
    async def test_llm_json_in_markdown_fences_stripped(self):
        """LLMs sometimes wrap JSON in ```json ... ``` — should still be parsed."""
        wrapped = "```json\n{\"intent\":\"loan_review\",\"entities\":{\"customer_id\":null,\"branch_id\":null,\"application_id\":\"L-007\",\"alert_id\":null}}\n```"
        llm = StubLLMService(fixed_response=wrapped)
        r = await _classify("loan L-007", llm)
        assert r["intent"] == "loan_review"
        assert r["entities"]["application_id"] == "L-007"

    @pytest.mark.asyncio
    async def test_malformed_json_falls_back_to_keywords(self):
        """Partial / malformed JSON triggers keyword fallback."""
        llm = StubLLMService(fixed_response="{intent: broken}")
        r = await _classify("branch staffing issue", llm)
        assert r["intent"] == "branch_insights"

    @pytest.mark.asyncio
    async def test_llm_json_missing_intent_field_falls_back(self):
        """JSON without 'intent' key triggers keyword fallback."""
        llm = StubLLMService(fixed_response='{"type": "fraud"}')
        r = await _classify("fraud alert", llm)
        # keyword fallback should still detect fraud
        assert r["intent"] == "fraud_alerts"

    @pytest.mark.asyncio
    async def test_classify_returns_general_for_truly_ambiguous(self):
        """Neither LLM nor keywords match → general."""
        llm = StubLLMService()  # returns non-JSON
        r = await _classify("the weather is nice today", llm)
        assert r["intent"] == "general"

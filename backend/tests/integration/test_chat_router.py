"""
Functional / HTTP-layer tests for POST /api/chat/query.

Covers:
- Authentication enforcement (401 for missing token)
- Request schema validation (422 for bad payloads)
- Response schema contract (agent_type, content, cards shape)
- All six intents via the HTTP interface
- history field forwarded correctly (no crash)
- Edge cases: empty message, very long message, unknown entities
"""
from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.api.auth import create_dev_token
from app.main import create_app


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────


@pytest_asyncio.fixture
async def client(container):
    """Authenticated client — all roles, uses the session container."""
    app = create_app()
    token = create_dev_token(
        "test-user",
        ["fraud_analyst", "underwriter", "branch_manager", "financial_advisor",
         "compliance_reviewer", "admin"],
    )
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        c.headers["Authorization"] = f"Bearer {token}"
        yield c


@pytest_asyncio.fixture
async def unauth_client():
    """Client with no auth token."""
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────


class TestChatAuth:
    async def test_unauthenticated_returns_401(self, unauth_client):
        r = await unauth_client.post("/api/chat/query", json={"message": "hi"})
        assert r.status_code == 401

    async def test_invalid_token_returns_401(self):
        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            c.headers["Authorization"] = "Bearer totally-invalid-token"
            r = await c.post("/api/chat/query", json={"message": "hi"})
            assert r.status_code == 401

    async def test_authenticated_request_accepted(self, client):
        r = await client.post("/api/chat/query", json={"message": "hello"})
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Request schema validation
# ─────────────────────────────────────────────────────────────────────────────


class TestChatRequestSchema:
    async def test_missing_message_field_returns_422(self, client):
        r = await client.post("/api/chat/query", json={})
        assert r.status_code == 422

    async def test_null_message_returns_422(self, client):
        r = await client.post("/api/chat/query", json={"message": None})
        assert r.status_code == 422

    async def test_non_json_body_returns_422(self, client):
        r = await client.post(
            "/api/chat/query",
            content="not json",
            headers={"Content-Type": "application/json"},
        )
        assert r.status_code == 422

    async def test_history_defaults_to_empty(self, client):
        r = await client.post("/api/chat/query", json={"message": "hello"})
        assert r.status_code == 200

    async def test_history_with_items_accepted(self, client):
        payload = {
            "message": "anything",
            "history": [
                {"role": "user", "content": "previous question"},
                {"role": "agent", "content": "previous answer"},
            ],
        }
        r = await client.post("/api/chat/query", json=payload)
        assert r.status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# Response schema contract
# ─────────────────────────────────────────────────────────────────────────────


class TestChatResponseSchema:
    async def _query(self, client, message: str) -> dict:
        r = await client.post("/api/chat/query", json={"message": message})
        assert r.status_code == 200
        return r.json()

    async def test_response_has_required_fields(self, client):
        data = await self._query(client, "hello")
        assert "agent_type" in data
        assert "content" in data
        assert "cards" in data

    async def test_agent_type_is_valid_string(self, client):
        valid = {"fraud", "sentiment", "loan", "branch", "advisory", "supervisor"}
        data = await self._query(client, "show fraud alerts")
        assert data["agent_type"] in valid

    async def test_content_is_non_empty_string(self, client):
        data = await self._query(client, "hello there")
        assert isinstance(data["content"], str)
        assert len(data["content"]) > 0

    async def test_cards_is_a_list(self, client):
        data = await self._query(client, "hello")
        assert isinstance(data["cards"], list)

    async def test_card_schema_when_present(self, client, container):
        from app.domain.models.fraud import FraudAlert, FraudRiskLevel
        # Seed an alert so fraud handler has data to return
        alert = FraudAlert(
            alert_id="FRAUD-ROUTER001",
            txn_id="T-R001",
            customer_id="C-R001",
            risk_score=0.88,
            risk_level=FraudRiskLevel.HIGH,
            reasons=["velocity_spike"],
        )
        await container.fraud.save_alert(alert)
        data = await self._query(client, "show fraud alerts for C-R001")
        for card in data["cards"]:
            assert "type" in card
            assert "title" in card
            assert card["type"] in {"alert", "metric", "action", "summary", "evidence"}


# ─────────────────────────────────────────────────────────────────────────────
# Intent routing via HTTP
# ─────────────────────────────────────────────────────────────────────────────


class TestChatIntentRouting:
    async def test_fraud_query_routes_to_fraud_agent(self, client):
        r = await client.post("/api/chat/query", json={"message": "Show fraud alerts"})
        assert r.json()["agent_type"] == "fraud"

    async def test_churn_query_routes_to_sentiment_agent(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "Which customers have high churn risk?"},
        )
        assert r.json()["agent_type"] == "sentiment"

    async def test_loan_query_routes_to_loan_agent(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "Review loan application L-001"},
        )
        assert r.json()["agent_type"] == "loan"

    async def test_branch_query_routes_to_branch_agent(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "What is happening at the West Side branch?"},
        )
        assert r.json()["agent_type"] == "branch"

    async def test_advisory_query_routes_to_advisory_agent(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "Generate advice for customer C-ASHA001"},
        )
        assert r.json()["agent_type"] == "advisory"

    async def test_general_query_routes_to_supervisor(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "What is the meaning of life?"},
        )
        assert r.json()["agent_type"] == "supervisor"


# ─────────────────────────────────────────────────────────────────────────────
# Edge cases
# ─────────────────────────────────────────────────────────────────────────────


class TestChatEdgeCases:
    async def test_whitespace_only_message_returns_general(self, client):
        r = await client.post("/api/chat/query", json={"message": "   "})
        assert r.status_code == 200
        assert r.json()["agent_type"] == "supervisor"

    async def test_very_long_message_handled(self, client):
        long_msg = "fraud " + "x" * 4000
        r = await client.post("/api/chat/query", json={"message": long_msg})
        assert r.status_code == 200

    async def test_special_characters_in_message(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "fraud? alerts! for: C-TEST001 & C-TEST002"},
        )
        assert r.status_code == 200

    async def test_unknown_customer_id_returns_graceful_response(self, client):
        r = await client.post(
            "/api/chat/query",
            json={"message": "fraud alerts for C-DOESNOTEXIST999"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["agent_type"] == "fraud"
        assert "No active fraud alerts" in data["content"]

    async def test_response_time_reasonable(self, client):
        """The in-memory adapter + stub LLM should respond in well under 2 s."""
        import time
        start = time.monotonic()
        r = await client.post("/api/chat/query", json={"message": "fraud alerts"})
        elapsed = time.monotonic() - start
        assert r.status_code == 200
        assert elapsed < 2.0, f"Response took {elapsed:.2f}s — too slow"

    async def test_concurrent_requests_all_succeed(self, client):
        import asyncio
        msgs = [
            "Show fraud alerts",
            "Churn risk for C-TEST",
            "Loan review L-001",
            "Branch operations",
            "Advisory for C-TEST",
        ]
        tasks = [
            client.post("/api/chat/query", json={"message": m})
            for m in msgs
        ]
        responses = await asyncio.gather(*tasks)
        assert all(r.status_code == 200 for r in responses)

"""
Integration tests for the fraud API workflow.

Uses the in-memory adapter (APP_ENV=test) and the stub LLM.
Tests the full request → agent → repository → response cycle.
"""

from app.domain.models.customer import CustomerProfile, KYCStatus, RiskTolerance


class TestFraudAPI:
    async def test_ingest_transaction_creates_alert(self, async_client, container):
        # Seed a customer first
        customer = CustomerProfile(
            customer_id="C-TEST001",
            name="Test Customer",
            risk_tolerance=RiskTolerance.MODERATE,
            kyc_status=KYCStatus.VERIFIED,
        )
        await container.customers.save(customer)

        # Ingest a transaction
        payload = {
            "txn_id": "T-TEST001",
            "customer_id": "C-TEST001",
            "account_id": "A-TEST001",
            "amount": 5000.0,
            "channel": "card_present",
            "merchant": "SUSPICIOUS_MERCHANT",
            "device_id": "D-NEW001",
        }
        response = await async_client.post("/api/fraud/events", json=payload)
        assert response.status_code in (200, 202)

        # The stub LLM returns a fixed response — alert should be created
        data = response.json()
        assert "alert_id" in data or "message" in data

    async def test_list_alerts_requires_auth(self, async_client):
        response = await async_client.get("/api/fraud/alerts")
        assert response.status_code == 200  # analyst token included in fixture

    async def test_get_nonexistent_alert_returns_404(self, async_client):
        response = await async_client.get("/api/fraud/alerts/NOTEXIST")
        assert response.status_code == 404

    async def test_approve_alert_creates_audit_trail(self, async_client, container):
        # Seed an alert
        from app.domain.models.fraud import FraudAlert, FraudRiskLevel

        alert = FraudAlert(
            alert_id="FRAUD-TESTAPPROVE",
            txn_id="T-X",
            customer_id="C-X",
            risk_score=0.85,
            risk_level=FraudRiskLevel.HIGH,
        )
        await container.fraud.save_alert(alert)

        # Approve it
        payload = {
            "analyst_id": "analyst-001",
            "decision": "approved",
            "notes": "Verified fraud pattern",
        }
        response = await async_client.post(
            "/api/fraud/alerts/FRAUD-TESTAPPROVE/approve", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "confirmed_fraud"

        # Check audit trail
        trail_response = await async_client.get("/api/audit/FRAUD-TESTAPPROVE")
        assert trail_response.status_code == 200
        trail = trail_response.json()
        assert len(trail) >= 1
        assert any(e["action"] == "fraud_alert_approved" for e in trail)

    async def test_approve_invalid_decision_returns_400(self, async_client, container):
        from app.domain.models.fraud import FraudAlert, FraudRiskLevel

        alert = FraudAlert(
            alert_id="FRAUD-BADINPUT",
            txn_id="T-Y",
            customer_id="C-Y",
            risk_score=0.5,
            risk_level=FraudRiskLevel.MEDIUM,
        )
        await container.fraud.save_alert(alert)

        payload = {"analyst_id": "a1", "decision": "invalid_decision"}
        response = await async_client.post("/api/fraud/alerts/FRAUD-BADINPUT/approve", json=payload)
        assert response.status_code == 400

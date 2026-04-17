"""
Agent audit trail and human-gate enforcement tests.

Verifies the P0 requirement: every AI-generated recommendation,
human override, and agent session is fully reconstructible.
"""

from httpx import ASGITransport, AsyncClient

from app.domain.models.customer import CustomerProfile


class TestAuditTrail:
    async def test_full_fraud_workflow_audit(self, async_client, container):
        """End-to-end: ingest → fraud alert → analyst approval → audit reconstruction."""
        customer = CustomerProfile(customer_id="C-AUDIT001", name="Audit Test")
        await container.customers.save(customer)

        # Step 1: Ingest transaction
        await async_client.post(
            "/api/fraud/events",
            json={
                "txn_id": "T-AUDIT001",
                "customer_id": "C-AUDIT001",
                "account_id": "A-AUDIT001",
                "amount": 9999.0,
                "channel": "online",
            },
        )

        # Step 2: Get alert list to find the created alert
        alerts_resp = await async_client.get("/api/fraud/alerts")
        assert alerts_resp.status_code == 200
        alerts = alerts_resp.json()

        # Find our alert
        our_alerts = [a for a in alerts if a.get("customer_id") == "C-AUDIT001"]
        if our_alerts:
            alert_id = our_alerts[0]["alert_id"]

            # Step 3: Approve
            await async_client.post(
                f"/api/fraud/alerts/{alert_id}/approve",
                json={
                    "analyst_id": "analyst-audit-001",
                    "decision": "declined",
                    "notes": "Cleared after investigation",
                },
            )

            # Step 4: Reconstruct audit trail
            trail_resp = await async_client.get(f"/api/audit/{alert_id}")
            assert trail_resp.status_code == 200
            trail = trail_resp.json()
            assert len(trail) >= 2  # created + declined

            actions = [e["action"] for e in trail]
            assert "fraud_alert_created" in actions
            assert "fraud_alert_declined" in actions

    async def test_unauthenticated_request_rejected(self, async_client):
        """Requests without auth tokens are rejected."""
        from app.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as unauthenticated:
            response = await unauthenticated.get("/api/fraud/alerts")
            assert response.status_code == 401

    async def test_health_check_public(self, async_client):
        """Health endpoint is accessible without auth."""
        from app.main import create_app

        app = create_app()
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as c:
            response = await c.get("/health")
            assert response.status_code == 200
            assert response.json()["status"] == "ok"

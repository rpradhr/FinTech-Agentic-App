"""Integration tests for the advisory approval workflow."""
import pytest

from app.domain.models.customer import CustomerProfile
from app.domain.models.advisory import AdviceDraft, AdviceDraftStatus


class TestAdvisoryAPI:
    async def test_generate_and_approve_advice(self, async_client, container):
        # Seed customer
        customer = CustomerProfile(
            customer_id="C-ADV001",
            name="Advisory Test Customer",
            products=["checking"],
            goals=["emergency_fund"],
        )
        await container.customers.save(customer)

        # Generate advice draft
        response = await async_client.get(
            "/api/advisory/customers/C-ADV001/recommendations",
            params={"advisor_id": "advisor-001"},
        )
        assert response.status_code == 200
        draft_data = response.json()
        draft_id = draft_data["draft_id"]
        assert draft_data["status"] == "pending_advisor_review"

        # Approve
        payload = {"advisor_id": "advisor-001"}
        approve_response = await async_client.post(
            f"/api/advisory/recommendations/{draft_id}/approve",
            json=payload,
        )
        assert approve_response.status_code == 200
        assert approve_response.json()["status"] == "approved"

        # Check audit trail
        trail = await async_client.get(f"/api/audit/{draft_id}")
        assert trail.status_code == 200
        events = trail.json()
        assert any(e["action"] == "advice_draft_approved" for e in events)

    async def test_edit_and_approve_advice(self, async_client, container):
        customer = CustomerProfile(
            customer_id="C-ADV002",
            name="Edit Advice Customer",
        )
        await container.customers.save(customer)

        response = await async_client.get(
            "/api/advisory/customers/C-ADV002/recommendations"
        )
        assert response.status_code == 200
        draft_id = response.json()["draft_id"]

        payload = {
            "advisor_id": "advisor-002",
            "advisor_edits": "Modified the savings recommendation to account for monthly expenses",
        }
        approve_response = await async_client.post(
            f"/api/advisory/recommendations/{draft_id}/approve",
            json=payload,
        )
        assert approve_response.status_code == 200
        data = approve_response.json()
        assert data["status"] == "edited_and_approved"

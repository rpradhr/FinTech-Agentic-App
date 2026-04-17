"""Integration tests for the loan review workflow."""
import pytest

from app.domain.models.customer import CustomerProfile, RiskTolerance, KYCStatus


class TestLoanAPI:
    async def test_submit_and_review_loan(self, async_client, container):
        # Seed customer
        customer = CustomerProfile(
            customer_id="C-LOAN001",
            name="Loan Customer",
            kyc_status=KYCStatus.VERIFIED,
        )
        await container.customers.save(customer)

        # Submit loan application
        payload = {
            "application_id": "L-APITEST001",
            "customer_id": "C-LOAN001",
            "loan_type": "personal",
            "requested_amount": 20000.0,
            "stated_income": 80000.0,
            "submitted_docs": ["paystub", "id_doc"],  # missing bank_statement
        }
        response = await async_client.post("/api/loans/applications", json=payload)
        assert response.status_code in (200, 202)

        # Fetch review
        review_response = await async_client.get(
            "/api/loans/applications/L-APITEST001/review"
        )
        assert review_response.status_code == 200
        review = review_response.json()
        assert "bank_statement" in review["missing_documents"]

    async def test_underwriter_decision_creates_audit(self, async_client, container):
        from app.domain.models.loan import LoanApplication, LoanReview

        # Seed application and review
        app = LoanApplication(
            application_id="L-DECISION001",
            customer_id="C-DEC001",
            loan_type="personal",
            requested_amount=10000.0,
            stated_income=60000.0,
        )
        review = LoanReview(
            review_id="REV-DECISION001",
            application_id="L-DECISION001",
            customer_id="C-DEC001",
            summary="Test review",
        )
        await container.loans.save_application(app)
        await container.loans.save_review(review)

        payload = {
            "underwriter_id": "uw-001",
            "decision": "approved",
            "notes": "All checks passed",
        }
        response = await async_client.post(
            "/api/loans/applications/L-DECISION001/decision", json=payload
        )
        assert response.status_code == 200
        data = response.json()
        assert data["underwriter_decision"] == "approved"

        # Check audit
        trail = await async_client.get("/api/audit/REV-DECISION001")
        assert trail.status_code == 200
        events = trail.json()
        assert any(e["action"] == "loan_decision_approved" for e in events)

    async def test_invalid_decision_returns_400(self, async_client, container):
        from app.domain.models.loan import LoanApplication, LoanReview

        app = LoanApplication(
            application_id="L-INVALID001",
            customer_id="C-INV001",
            loan_type="auto",
            requested_amount=5000.0,
            stated_income=40000.0,
        )
        review = LoanReview(
            review_id="REV-INVALID001",
            application_id="L-INVALID001",
            customer_id="C-INV001",
            summary="Test",
        )
        await container.loans.save_application(app)
        await container.loans.save_review(review)

        payload = {"underwriter_id": "uw-001", "decision": "definitely_yes_please"}
        response = await async_client.post(
            "/api/loans/applications/L-INVALID001/decision", json=payload
        )
        assert response.status_code == 400

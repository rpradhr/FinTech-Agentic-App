"""Unit tests for domain model validation and business logic."""
import pytest
from datetime import datetime

from app.domain.models.fraud import FraudRiskLevel, FraudAlert, FraudStatus
from app.domain.models.fraud import RecommendedAction
from app.domain.models.customer import CustomerProfile, KYCStatus, RiskTolerance
from app.domain.models.loan import LoanApplication, LoanReview, LoanStatus
from app.domain.models.audit import AuditEvent, AuditActor, AuditAction
from app.domain.models.interaction import InteractionAnalysis, SentimentLabel, UrgencyLevel
from app.domain.models.interaction import InteractionSource
from app.core.ids import new_fraud_id, new_audit_id


class TestFraudRiskLevel:
    def test_from_score_critical(self):
        assert FraudRiskLevel.from_score(0.95) == FraudRiskLevel.CRITICAL

    def test_from_score_high(self):
        assert FraudRiskLevel.from_score(0.75) == FraudRiskLevel.HIGH

    def test_from_score_medium(self):
        assert FraudRiskLevel.from_score(0.55) == FraudRiskLevel.MEDIUM

    def test_from_score_low(self):
        assert FraudRiskLevel.from_score(0.2) == FraudRiskLevel.LOW

    def test_boundary_critical(self):
        assert FraudRiskLevel.from_score(0.90) == FraudRiskLevel.CRITICAL

    def test_boundary_high(self):
        assert FraudRiskLevel.from_score(0.70) == FraudRiskLevel.HIGH


class TestFraudAlert:
    def test_create_valid_alert(self):
        alert = FraudAlert(
            alert_id="FRAUD-001",
            txn_id="T-001",
            customer_id="C-001",
            risk_score=0.85,
            risk_level=FraudRiskLevel.HIGH,
            reasons=["velocity_spike"],
            recommended_action=RecommendedAction.MANUAL_HOLD_REVIEW,
            status=FraudStatus.PENDING_ANALYST_REVIEW,
        )
        assert alert.risk_score == 0.85
        assert alert.status == FraudStatus.PENDING_ANALYST_REVIEW

    def test_risk_score_bounds(self):
        with pytest.raises(Exception):
            FraudAlert(
                alert_id="X",
                txn_id="X",
                customer_id="X",
                risk_score=1.5,  # invalid
                risk_level=FraudRiskLevel.HIGH,
            )


class TestCustomerProfile:
    def test_default_values(self):
        profile = CustomerProfile(
            customer_id="C-001",
            name="Test User",
        )
        assert profile.risk_tolerance == RiskTolerance.MODERATE
        assert profile.kyc_status == KYCStatus.PENDING
        assert profile.churn_risk_score == 0.0
        assert profile.products == []

    def test_churn_risk_bounds(self):
        with pytest.raises(Exception):
            CustomerProfile(
                customer_id="C-001",
                name="X",
                churn_risk_score=1.5,  # invalid
            )


class TestAuditEvent:
    def test_immutable(self):
        event = AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.HUMAN,
            actor_id="user-1",
            action=AuditAction.FRAUD_ALERT_APPROVED,
            related_object_id="FRAUD-001",
            related_object_type="fraud_alert",
        )
        with pytest.raises(Exception):
            event.actor_id = "modified"  # AuditEvent is frozen

    def test_has_timestamp(self):
        event = AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.AGENT,
            actor_id="fraud_agent",
            action=AuditAction.FRAUD_ALERT_CREATED,
            related_object_id="FRAUD-001",
            related_object_type="fraud_alert",
        )
        assert event.ts is not None
        assert isinstance(event.ts, datetime)


class TestLoanReview:
    def test_review_without_decision(self):
        review = LoanReview(
            review_id="REV-001",
            application_id="L-001",
            customer_id="C-001",
            summary="Test summary",
        )
        assert review.underwriter_decision is None
        assert review.underwriter_id is None

    def test_confidence_score_bounds(self):
        with pytest.raises(Exception):
            LoanReview(
                review_id="R",
                application_id="L",
                customer_id="C",
                summary="X",
                confidence_score=2.0,  # invalid
            )

"""Fraud domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class FraudRiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @classmethod
    def from_score(cls, score: float) -> "FraudRiskLevel":
        if score >= 0.90:
            return cls.CRITICAL
        if score >= 0.70:
            return cls.HIGH
        if score >= 0.40:
            return cls.MEDIUM
        return cls.LOW


class FraudStatus(str, Enum):
    PENDING_ANALYST_REVIEW = "pending_analyst_review"
    UNDER_INVESTIGATION = "under_investigation"
    CONFIRMED_FRAUD = "confirmed_fraud"
    CLEARED = "cleared"
    ESCALATED = "escalated"


class RecommendedAction(str, Enum):
    MONITOR = "monitor"
    SOFT_BLOCK = "soft_block"
    MANUAL_HOLD_REVIEW = "manual_hold_review"
    HARD_BLOCK = "hard_block"
    ESCALATE_TO_COMPLIANCE = "escalate_to_compliance"


class FraudEvidence(BaseModel):
    """Structured evidence item linked to a fraud alert."""

    evidence_type: str  # velocity_spike | geo_anomaly | device_mismatch | merchant_cluster | etc.
    description: str
    linked_entity_id: Optional[str] = None
    linked_entity_type: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)


class FraudAlert(BaseModel):
    """Fraud detection output — always requires analyst review before action."""

    alert_id: str
    txn_id: str
    customer_id: str
    account_id: Optional[str] = None
    household_id: Optional[str] = None
    risk_score: float = Field(ge=0.0, le=1.0)
    risk_level: FraudRiskLevel
    reasons: list[str] = Field(default_factory=list)
    evidence: list[FraudEvidence] = Field(default_factory=list)
    ring_indicators: list[str] = Field(default_factory=list)
    recommended_action: RecommendedAction = RecommendedAction.MANUAL_HOLD_REVIEW
    ai_explanation: Optional[str] = None
    status: FraudStatus = FraudStatus.PENDING_ANALYST_REVIEW
    assigned_analyst_id: Optional[str] = None
    analyst_decision: Optional[str] = None
    analyst_notes: Optional[str] = None
    related_alert_ids: list[str] = Field(default_factory=list)
    case_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    class Config:
        use_enum_values = True


class FraudRingCluster(BaseModel):
    """Cross-account fraud ring detected by graph analysis."""

    cluster_id: str
    customer_ids: list[str]
    account_ids: list[str]
    device_ids: list[str]
    merchant_ids: list[str]
    branch_ids: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    summary: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)

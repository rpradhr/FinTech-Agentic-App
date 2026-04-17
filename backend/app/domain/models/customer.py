"""Customer domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class RiskTolerance(StrEnum):
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"


class KYCStatus(StrEnum):
    PENDING = "pending"
    VERIFIED = "verified"
    FAILED = "failed"
    EXPIRED = "expired"


class SentimentStatus(StrEnum):
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    UNKNOWN = "unknown"


class GeoLocation(BaseModel):
    lat: float
    lon: float


class CustomerPreferences(BaseModel):
    preferred_channel: str = "email"
    language: str = "en"
    marketing_opt_in: bool = False
    paperless: bool = True


class CustomerProfile(BaseModel):
    """Core customer record — the shared context anchor for all agents."""

    customer_id: str
    household_id: str | None = None
    name: str
    email: str | None = None
    phone: str | None = None
    risk_tolerance: RiskTolerance = RiskTolerance.MODERATE
    products: list[str] = Field(default_factory=list)
    goals: list[str] = Field(default_factory=list)
    kyc_status: KYCStatus = KYCStatus.PENDING
    last_sentiment_status: SentimentStatus = SentimentStatus.UNKNOWN
    churn_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    relationship_manager_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class Household(BaseModel):
    """Household groups related customers for cross-entity fraud and advisory analysis."""

    household_id: str
    member_customer_ids: list[str] = Field(default_factory=list)
    primary_customer_id: str | None = None
    total_relationship_value: float = 0.0
    created_at: datetime = Field(default_factory=datetime.utcnow)

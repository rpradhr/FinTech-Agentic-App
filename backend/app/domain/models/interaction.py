"""Customer interaction and sentiment domain models."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class InteractionSource(StrEnum):
    CALL_TRANSCRIPT = "call_transcript"
    EMAIL = "email"
    COMPLAINT = "complaint"
    SURVEY = "survey"
    SECURE_MESSAGE = "secure_message"
    CHAT = "chat"
    BRANCH_NOTE = "branch_note"


class SentimentLabel(StrEnum):
    VERY_POSITIVE = "very_positive"
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    VERY_NEGATIVE = "very_negative"


class UrgencyLevel(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Interaction(BaseModel):
    """Raw interaction record — input to the Sentiment Agent."""

    interaction_id: str
    customer_id: str
    source: InteractionSource
    content: str  # transcript text, email body, complaint text, etc.
    agent_id: str | None = None  # branch rep or call agent handling the interaction
    branch_id: str | None = None
    channel_metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class InteractionAnalysis(BaseModel):
    """Sentiment and signal analysis output from the Sentiment Agent."""

    analysis_id: str
    interaction_id: str
    customer_id: str
    source: InteractionSource
    sentiment: SentimentLabel
    sentiment_score: float = Field(ge=-1.0, le=1.0)  # -1 very negative, +1 very positive
    urgency: UrgencyLevel
    drivers: list[str] = Field(default_factory=list)  # fee_dispute | long_wait | product_issue
    churn_risk: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_recommended: bool = False
    summary: str = ""
    entities_mentioned: list[str] = Field(default_factory=list)
    linked_case_id: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class CustomerSignal(BaseModel):
    """Aggregated customer signal across interactions — updated by Sentiment Agent."""

    customer_id: str
    overall_sentiment: SentimentLabel = SentimentLabel.NEUTRAL
    recent_drivers: list[str] = Field(default_factory=list)
    churn_risk: float = 0.0
    open_complaint_count: int = 0
    last_interaction_at: datetime | None = None
    suppress_cross_sell: bool = False
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True

"""Financial advisory domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AdviceCategory(str, Enum):
    SAVINGS = "savings"
    BUDGETING = "budgeting"
    PRODUCT_FIT = "product_fit"
    DEBT_MANAGEMENT = "debt_management"
    INVESTMENT = "investment"
    SERVICE_RECOVERY = "service_recovery"
    FOLLOW_UP = "follow_up"


class AdviceDraftStatus(str, Enum):
    DRAFT = "draft"
    PENDING_ADVISOR_REVIEW = "pending_advisor_review"
    APPROVED = "approved"
    EDITED_AND_APPROVED = "edited_and_approved"
    REJECTED = "rejected"
    DELIVERED = "delivered"


class NextBestAction(BaseModel):
    action_id: str
    category: AdviceCategory
    title: str
    rationale: str
    evidence: list[str] = Field(default_factory=list)
    suggested_script: Optional[str] = None
    priority: int = 5  # 1 = highest
    suitability_flags: list[str] = Field(default_factory=list)

    class Config:
        use_enum_values = True


class AdviceDraft(BaseModel):
    """Advisory agent output — advisor must approve before any customer delivery."""

    draft_id: str
    customer_id: str
    advisor_id: Optional[str] = None
    next_best_actions: list[NextBestAction] = Field(default_factory=list)
    customer_context_summary: str = ""
    goals_summary: str = ""
    product_gaps: list[str] = Field(default_factory=list)
    service_sentiment_note: Optional[str] = None
    suppress_cross_sell: bool = False
    full_advice_text: str = ""
    status: AdviceDraftStatus = AdviceDraftStatus.DRAFT
    advisor_edits: Optional[str] = None
    approved_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True

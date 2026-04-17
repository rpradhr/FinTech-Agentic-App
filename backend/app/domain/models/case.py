"""Case management domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class CaseType(str, Enum):
    FRAUD = "fraud"
    COMPLAINT = "complaint"
    LOAN_REVIEW = "loan_review"
    ADVISORY = "advisory"
    BRANCH = "branch"


class CaseStatus(str, Enum):
    OPEN = "open"
    PENDING_REVIEW = "pending_review"
    UNDER_INVESTIGATION = "under_investigation"
    PENDING_APPROVAL = "pending_approval"
    RESOLVED = "resolved"
    ESCALATED = "escalated"
    CLOSED = "closed"


class CasePriority(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class CaseEvent(BaseModel):
    """Immutable timeline event within a case."""

    event_id: str
    event_type: str  # created | updated | assigned | approved | escalated | closed
    actor_id: Optional[str] = None
    actor_type: str = "system"  # system | human
    description: str
    metadata: dict = Field(default_factory=dict)
    ts: datetime = Field(default_factory=datetime.utcnow)


class Case(BaseModel):
    """Unified case workspace shared across agents and analysts."""

    case_id: str
    case_type: CaseType
    status: CaseStatus = CaseStatus.OPEN
    priority: CasePriority = CasePriority.MEDIUM
    title: str
    description: Optional[str] = None
    customer_id: Optional[str] = None
    branch_id: Optional[str] = None
    assigned_to_id: Optional[str] = None
    linked_entity_ids: list[str] = Field(default_factory=list)  # alert/application/review IDs
    linked_entity_types: list[str] = Field(default_factory=list)
    timeline: list[CaseEvent] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    resolved_at: Optional[datetime] = None

    class Config:
        use_enum_values = True

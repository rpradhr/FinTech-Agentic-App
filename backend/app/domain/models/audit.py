"""Audit log domain models — immutable event records for compliance."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AuditActor(str, Enum):
    HUMAN = "human"
    AGENT = "agent"
    SYSTEM = "system"


class AuditAction(str, Enum):
    # Fraud actions
    FRAUD_ALERT_CREATED = "fraud_alert_created"
    FRAUD_ALERT_APPROVED = "fraud_alert_approved"
    FRAUD_ALERT_DECLINED = "fraud_alert_declined"
    FRAUD_ALERT_ESCALATED = "fraud_alert_escalated"
    # Loan actions
    LOAN_REVIEW_CREATED = "loan_review_created"
    LOAN_DECISION_APPROVED = "loan_decision_approved"
    LOAN_DECISION_DECLINED = "loan_decision_declined"
    # Sentiment / advisory
    SENTIMENT_ANALYSIS_CREATED = "sentiment_analysis_created"
    ADVICE_DRAFT_CREATED = "advice_draft_created"
    ADVICE_DRAFT_APPROVED = "advice_draft_approved"
    ADVICE_DRAFT_EDITED_AND_SAVED = "advice_draft_edited_and_saved"
    # Branch
    BRANCH_INSIGHT_CREATED = "branch_insight_created"
    BRANCH_ALERT_REVIEWED = "branch_alert_reviewed"
    # Generic
    RECOMMENDATION_APPROVED = "recommendation_approved"
    RECOMMENDATION_OVERRIDDEN = "recommendation_overridden"
    HUMAN_OVERRIDE = "human_override"
    AGENT_HANDOFF = "agent_handoff"
    # System
    DATA_INGESTED = "data_ingested"
    AGENT_SESSION_STARTED = "agent_session_started"
    AGENT_SESSION_COMPLETED = "agent_session_completed"


class AuditEvent(BaseModel):
    """
    Immutable audit record.
    Never update — only append. Provides full reconstruction for compliance.
    """

    event_id: str
    actor_type: AuditActor
    actor_id: str  # user ID, agent name, or "system"
    action: AuditAction
    related_object_id: str
    related_object_type: str  # fraud_alert | loan_review | advice_draft | case | etc.
    customer_id: Optional[str] = None
    reason_code: Optional[str] = None
    notes: Optional[str] = None
    prompt_version: Optional[str] = None  # prompt version used in this action
    agent_session_id: Optional[str] = None
    input_summary: Optional[str] = None  # brief summary of agent inputs
    output_summary: Optional[str] = None  # brief summary of agent outputs
    metadata: dict = Field(default_factory=dict)
    ts: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True
        frozen = True  # Immutable after creation


class AgentTrace(BaseModel):
    """Single trace step within an agent session — maps to Agent Tracer structure."""

    trace_id: str
    session_id: str
    agent_name: str
    step_type: str  # user | internal | llm_call | tool_call | tool_result | handoff | assistant
    step_index: int
    input_data: Optional[dict] = None
    output_data: Optional[dict] = None
    tool_name: Optional[str] = None
    model_id: Optional[str] = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: Optional[float] = None
    ts: datetime = Field(default_factory=datetime.utcnow)

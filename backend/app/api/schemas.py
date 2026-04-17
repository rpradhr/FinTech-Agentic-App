"""
Request/response schemas for all API endpoints.
Kept separate from domain models — API shape can evolve independently.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

# ─────────────────────────────────────────────────────────────────────────────
# Common
# ─────────────────────────────────────────────────────────────────────────────


class ErrorResponse(BaseModel):
    detail: str
    code: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────


class DevTokenRequest(BaseModel):
    user_id: str
    roles: list[str] = ["fraud_analyst"]


class DevTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


# ─────────────────────────────────────────────────────────────────────────────
# Fraud
# ─────────────────────────────────────────────────────────────────────────────


class TransactionIngestRequest(BaseModel):
    txn_id: str
    customer_id: str
    account_id: str
    amount: float
    currency: str = "USD"
    merchant: str | None = None
    channel: str
    device_id: str | None = None
    geo: dict | None = None
    branch_id: str | None = None
    event_ts: datetime | None = None
    metadata: dict = Field(default_factory=dict)


class FraudAlertApproveRequest(BaseModel):
    analyst_id: str
    decision: str  # approved | declined | escalated
    notes: str | None = None


class FraudAlertResponse(BaseModel):
    alert_id: str
    txn_id: str
    customer_id: str
    risk_score: float
    risk_level: str
    reasons: list[str]
    recommended_action: str
    ai_explanation: str | None
    status: str
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Loan
# ─────────────────────────────────────────────────────────────────────────────


class LoanApplicationRequest(BaseModel):
    application_id: str | None = None
    customer_id: str
    loan_type: str
    requested_amount: float
    term_months: int = 60
    stated_income: float
    stated_employment: str | None = None
    credit_score: int | None = None
    submitted_docs: list[str] = Field(default_factory=list)


class LoanDecisionRequest(BaseModel):
    underwriter_id: str
    decision: str  # approved | conditionally_approved | declined | pending_documents
    notes: str | None = None


class LoanReviewResponse(BaseModel):
    review_id: str
    application_id: str
    customer_id: str
    summary: str
    missing_documents: list[str]
    recommended_status: str
    confidence_score: float
    ai_explanation: str | None
    underwriter_decision: str | None
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Interactions / Sentiment
# ─────────────────────────────────────────────────────────────────────────────


class InteractionIngestRequest(BaseModel):
    interaction_id: str | None = None
    customer_id: str
    source: str
    content: str
    branch_id: str | None = None
    channel_metadata: dict = Field(default_factory=dict)


class CustomerSignalResponse(BaseModel):
    customer_id: str
    overall_sentiment: str
    recent_drivers: list[str]
    churn_risk: float
    suppress_cross_sell: bool
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Branch
# ─────────────────────────────────────────────────────────────────────────────


class BranchInsightResponse(BaseModel):
    insight_id: str
    branch_id: str
    issue_summary: str
    probable_causes: list[str]
    ranked_recommendations: list[str]
    created_at: datetime


class BranchDashboardEntry(BaseModel):
    branch_id: str
    branch_name: str | None
    report_date: Any
    avg_wait_time_minutes: float | None
    complaint_count: int
    new_accounts_opened: int


# ─────────────────────────────────────────────────────────────────────────────
# Advisory
# ─────────────────────────────────────────────────────────────────────────────


class AdviceApproveRequest(BaseModel):
    advisor_id: str
    advisor_edits: str | None = None  # if non-null, status becomes edited_and_approved


class AdviceDraftResponse(BaseModel):
    draft_id: str
    customer_id: str
    advisor_id: str | None
    next_best_actions: list[dict]
    customer_context_summary: str
    goals_summary: str
    service_sentiment_note: str | None
    suppress_cross_sell: bool
    full_advice_text: str
    status: str
    created_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Cases
# ─────────────────────────────────────────────────────────────────────────────


class CaseResponse(BaseModel):
    case_id: str
    case_type: str
    status: str
    priority: str
    title: str
    customer_id: str | None
    created_at: datetime
    updated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Audit
# ─────────────────────────────────────────────────────────────────────────────


class AuditEventResponse(BaseModel):
    event_id: str
    actor_type: str
    actor_id: str
    action: str
    related_object_id: str
    related_object_type: str
    customer_id: str | None
    notes: str | None
    ts: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Chat / NL interface
# ─────────────────────────────────────────────────────────────────────────────


class ChatCard(BaseModel):
    type: str  # alert | metric | action | summary | evidence
    title: str
    value: str | None = None
    subtitle: str | None = None
    status: str | None = None
    items: list[str] | None = None
    color: str | None = None


class ChatHistoryMessage(BaseModel):
    role: str  # user | agent
    content: str


class ChatQueryRequest(BaseModel):
    message: str
    history: list[ChatHistoryMessage] = Field(default_factory=list)


class ChatQueryResponse(BaseModel):
    agent_type: str
    content: str
    cards: list[ChatCard] = Field(default_factory=list)

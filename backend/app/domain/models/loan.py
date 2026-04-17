"""Loan domain models."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class LoanType(str, Enum):
    PERSONAL = "personal"
    AUTO = "auto"
    HOME = "home"
    BUSINESS = "business"
    STUDENT = "student"
    CREDIT_CARD = "credit_card"


class LoanStatus(str, Enum):
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    PENDING_DOCUMENTS = "pending_documents"
    APPROVED = "approved"
    CONDITIONALLY_APPROVED = "conditionally_approved"
    DECLINED = "declined"
    WITHDRAWN = "withdrawn"


class PolicyExceptionSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class LoanDocument(BaseModel):
    doc_id: str
    doc_type: str  # paystub | bank_statement | id_doc | tax_return | etc.
    uploaded_at: datetime
    verified: bool = False
    verification_notes: Optional[str] = None


class LoanApplication(BaseModel):
    """Loan application — the primary input to the Loan Reviewer Agent."""

    application_id: str
    customer_id: str
    loan_type: LoanType
    requested_amount: float
    term_months: int = 60
    stated_income: float
    stated_employment: Optional[str] = None
    credit_score: Optional[int] = None
    submitted_docs: list[str] = Field(default_factory=list)
    documents: list[LoanDocument] = Field(default_factory=list)
    status: LoanStatus = LoanStatus.SUBMITTED
    fraud_flag: bool = False
    fraud_alert_ids: list[str] = Field(default_factory=list)
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class LoanException(BaseModel):
    """Policy exception detected during loan review."""

    exception_id: str
    application_id: str
    exception_type: str
    description: str
    severity: PolicyExceptionSeverity = PolicyExceptionSeverity.WARNING
    rule_reference: Optional[str] = None
    detected_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True


class LoanReview(BaseModel):
    """AI-generated review summary — requires underwriter decision before actioning."""

    review_id: str
    application_id: str
    customer_id: str
    summary: str
    missing_documents: list[str] = Field(default_factory=list)
    exceptions: list[LoanException] = Field(default_factory=list)
    fraud_context_summary: Optional[str] = None
    recommended_status: LoanStatus = LoanStatus.UNDER_REVIEW
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0)
    ai_explanation: Optional[str] = None
    underwriter_id: Optional[str] = None
    underwriter_decision: Optional[str] = None
    underwriter_notes: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        use_enum_values = True

"""Loan review workbench API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import UserRole, require_roles
from app.api.schemas import (
    LoanApplicationRequest,
    LoanDecisionRequest,
    LoanReviewResponse,
)
from app.application.orchestrator import build_supervisor
from app.core.container import get_container
from app.core.ids import new_audit_id, new_id
from app.domain.models import LoanApplication
from app.domain.models.audit import AuditAction, AuditActor, AuditEvent

router = APIRouter(prefix="/api/loans", tags=["loans"])


@router.post("/applications", status_code=status.HTTP_202_ACCEPTED)
async def submit_loan_application(
    body: LoanApplicationRequest,
    _user=Depends(require_roles(UserRole.UNDERWRITER, UserRole.SERVICE_ACCOUNT, UserRole.ADMIN)),
):
    """Submit a new loan application and trigger automated review."""
    container = get_container()
    supervisor = build_supervisor(container)

    application = LoanApplication(
        application_id=body.application_id or new_id("L-"),
        customer_id=body.customer_id,
        loan_type=body.loan_type,
        requested_amount=body.requested_amount,
        term_months=body.term_months,
        stated_income=body.stated_income,
        stated_employment=body.stated_employment,
        credit_score=body.credit_score,
        submitted_docs=body.submitted_docs,
    )

    await container.loans.save_application(application)
    review = await supervisor.process_loan_application(application)

    return {
        "message": "Application submitted and review started",
        "application_id": application.application_id,
        "review_id": review.review_id,
    }


@router.get(
    "/applications/{application_id}/review",
    response_model=LoanReviewResponse,
)
async def get_loan_review(
    application_id: str,
    _user=Depends(require_roles(UserRole.UNDERWRITER, UserRole.COMPLIANCE_REVIEWER)),
):
    """Return the automated review for a loan application."""
    container = get_container()
    review = await container.loans.get_review_by_application(application_id)
    if review is None:
        raise HTTPException(
            status_code=404,
            detail=f"No review found for application {application_id}",
        )
    return LoanReviewResponse(
        review_id=review.review_id,
        application_id=review.application_id,
        customer_id=review.customer_id,
        summary=review.summary,
        missing_documents=review.missing_documents,
        recommended_status=review.recommended_status,
        confidence_score=review.confidence_score,
        ai_explanation=review.ai_explanation,
        underwriter_decision=review.underwriter_decision,
        created_at=review.created_at,
    )


@router.post(
    "/applications/{application_id}/decision",
    response_model=LoanReviewResponse,
)
async def record_loan_decision(
    application_id: str,
    body: LoanDecisionRequest,
    _user=Depends(require_roles(UserRole.UNDERWRITER)),
):
    """
    Human-in-the-loop gate: underwriter records their final decision.
    This is the ONLY path that advances a loan from review to decision.
    """
    container = get_container()

    review = await container.loans.get_review_by_application(application_id)
    if review is None:
        raise HTTPException(status_code=404, detail="Review not found")

    valid_decisions = {"approved", "conditionally_approved", "declined", "pending_documents"}
    if body.decision not in valid_decisions:
        raise HTTPException(
            status_code=400,
            detail=f"decision must be one of {valid_decisions}",
        )

    updated_review = await container.loans.update_review_decision(
        review_id=review.review_id,
        underwriter_id=body.underwriter_id,
        decision=body.decision,
        notes=body.notes,
    )

    # Update application status
    await container.loans.update_application_status(application_id, body.decision)

    # Audit
    await container.audit.append(
        AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.HUMAN,
            actor_id=body.underwriter_id,
            action=(
                AuditAction.LOAN_DECISION_APPROVED
                if body.decision in ("approved", "conditionally_approved")
                else AuditAction.LOAN_DECISION_DECLINED
            ),
            related_object_id=review.review_id,
            related_object_type="loan_review",
            customer_id=review.customer_id,
            notes=body.notes,
            reason_code=body.decision,
        )
    )

    return LoanReviewResponse(
        review_id=updated_review.review_id,
        application_id=updated_review.application_id,
        customer_id=updated_review.customer_id,
        summary=updated_review.summary,
        missing_documents=updated_review.missing_documents,
        recommended_status=updated_review.recommended_status,
        confidence_score=updated_review.confidence_score,
        ai_explanation=updated_review.ai_explanation,
        underwriter_decision=updated_review.underwriter_decision,
        created_at=updated_review.created_at,
    )

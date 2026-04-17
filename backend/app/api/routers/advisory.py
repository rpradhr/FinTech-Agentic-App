"""Financial advisory API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth import UserRole, require_roles
from app.api.schemas import AdviceApproveRequest, AdviceDraftResponse
from app.application.orchestrator import build_supervisor
from app.core.container import get_container
from app.core.ids import new_audit_id
from app.domain.models.audit import AuditAction, AuditActor, AuditEvent

router = APIRouter(prefix="/api/advisory", tags=["advisory"])


@router.get(
    "/customers/{customer_id}/recommendations",
    response_model=AdviceDraftResponse,
)
async def get_advice_draft(
    customer_id: str,
    advisor_id: str | None = None,
    _user=Depends(require_roles(UserRole.FINANCIAL_ADVISOR, UserRole.ADMIN)),
):
    """
    Generate (or retrieve latest) advice draft for a customer.
    Draft requires advisor approval before any customer delivery.
    """
    container = get_container()
    supervisor = build_supervisor(container)

    # Generate fresh draft
    draft = await supervisor.generate_advice(customer_id, advisor_id=advisor_id)

    return AdviceDraftResponse(
        draft_id=draft.draft_id,
        customer_id=draft.customer_id,
        advisor_id=draft.advisor_id,
        next_best_actions=[nba.model_dump() for nba in draft.next_best_actions],
        customer_context_summary=draft.customer_context_summary,
        goals_summary=draft.goals_summary,
        service_sentiment_note=draft.service_sentiment_note,
        suppress_cross_sell=draft.suppress_cross_sell,
        full_advice_text=draft.full_advice_text,
        status=draft.status,
        created_at=draft.created_at,
    )


@router.post(
    "/recommendations/{draft_id}/approve",
    response_model=AdviceDraftResponse,
)
async def approve_advice_draft(
    draft_id: str,
    body: AdviceApproveRequest,
    _user=Depends(require_roles(UserRole.FINANCIAL_ADVISOR)),
):
    """
    Human-in-the-loop gate: advisor approves (or edits and saves) the advice draft.
    No customer-facing content can be delivered without this step.
    """
    container = get_container()

    new_status = "edited_and_approved" if body.advisor_edits else "approved"

    draft = await container.advisory.update_draft_status(
        draft_id=draft_id,
        status=new_status,
        advisor_edits=body.advisor_edits,
    )

    # Audit
    await container.audit.append(
        AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.HUMAN,
            actor_id=body.advisor_id,
            action=(
                AuditAction.ADVICE_DRAFT_EDITED_AND_SAVED
                if body.advisor_edits
                else AuditAction.ADVICE_DRAFT_APPROVED
            ),
            related_object_id=draft_id,
            related_object_type="advice_draft",
            customer_id=draft.customer_id,
        )
    )

    return AdviceDraftResponse(
        draft_id=draft.draft_id,
        customer_id=draft.customer_id,
        advisor_id=draft.advisor_id,
        next_best_actions=[nba.model_dump() for nba in draft.next_best_actions],
        customer_context_summary=draft.customer_context_summary,
        goals_summary=draft.goals_summary,
        service_sentiment_note=draft.service_sentiment_note,
        suppress_cross_sell=draft.suppress_cross_sell,
        full_advice_text=draft.full_advice_text,
        status=draft.status,
        created_at=draft.created_at,
    )

"""Case management and audit console API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.auth import UserRole, require_roles
from app.api.schemas import AuditEventResponse, CaseResponse
from app.core.container import get_container

router = APIRouter(prefix="/api", tags=["cases", "audit"])


@router.get("/cases/{case_id}", response_model=CaseResponse)
async def get_case(
    case_id: str,
    _user=Depends(
        require_roles(
            UserRole.FRAUD_ANALYST,
            UserRole.UNDERWRITER,
            UserRole.BRANCH_MANAGER,
            UserRole.FINANCIAL_ADVISOR,
            UserRole.COMPLIANCE_REVIEWER,
        )
    ),
):
    container = get_container()
    case = await container.cases.get_by_id(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return CaseResponse(
        case_id=case.case_id,
        case_type=case.case_type,
        status=case.status,
        priority=case.priority,
        title=case.title,
        customer_id=case.customer_id,
        created_at=case.created_at,
        updated_at=case.updated_at,
    )


@router.get("/cases", response_model=list[CaseResponse])
async def list_open_cases(
    case_type: str | None = None,
    limit: int = 50,
    _user=Depends(require_roles(UserRole.COMPLIANCE_REVIEWER, UserRole.ADMIN)),
):
    container = get_container()
    cases = await container.cases.list_open_cases(case_type=case_type, limit=limit)
    return [
        CaseResponse(
            case_id=c.case_id,
            case_type=c.case_type,
            status=c.status,
            priority=c.priority,
            title=c.title,
            customer_id=c.customer_id,
            created_at=c.created_at,
            updated_at=c.updated_at,
        )
        for c in cases
    ]


@router.get("/audit/{object_id}", response_model=list[AuditEventResponse])
async def get_audit_trail(
    object_id: str,
    _user=Depends(require_roles(UserRole.COMPLIANCE_REVIEWER, UserRole.ADMIN)),
):
    """Return the full audit trail for any object (alert, review, draft, case)."""
    container = get_container()
    events = await container.audit.get_by_object(object_id)
    return [
        AuditEventResponse(
            event_id=e.event_id,
            actor_type=e.actor_type,
            actor_id=e.actor_id,
            action=e.action,
            related_object_id=e.related_object_id,
            related_object_type=e.related_object_type,
            customer_id=e.customer_id,
            notes=e.notes,
            ts=e.ts,
        )
        for e in events
    ]


@router.get("/metrics/agents")
async def get_agent_metrics(
    _user=Depends(require_roles(UserRole.COMPLIANCE_REVIEWER, UserRole.ADMIN)),
):
    """Return basic agent performance metrics derived from audit log."""
    container = get_container()
    # This would be replaced with proper aggregation queries in production
    return {
        "message": "Agent metrics endpoint — connect to observability platform for full metrics",
        "fraud_alerts_pending": len(await container.fraud.list_pending_alerts(limit=500)),
        "loan_reviews_pending": len(await container.loans.list_pending_reviews(limit=500)),
        "open_cases": len(await container.cases.list_open_cases(limit=500)),
    }

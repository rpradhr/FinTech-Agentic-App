"""Fraud workbench API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import UserRole, get_current_user, require_roles
from app.api.schemas import FraudAlertApproveRequest, FraudAlertResponse, TransactionIngestRequest
from app.application.orchestrator import Supervisor
from app.core.container import get_container
from app.core.ids import new_audit_id, new_id
from app.domain.models import Transaction
from app.domain.models.audit import AuditAction, AuditActor, AuditEvent
from app.domain.models.transaction import TransactionChannel

router = APIRouter(prefix="/api/fraud", tags=["fraud"])


def _get_supervisor() -> Supervisor:
    from app.application.orchestrator import build_supervisor
    return build_supervisor(get_container())


@router.post("/events", status_code=status.HTTP_202_ACCEPTED)
async def ingest_transaction(
    body: TransactionIngestRequest,
    _user=Depends(require_roles(UserRole.FRAUD_ANALYST, UserRole.SERVICE_ACCOUNT, UserRole.ADMIN)),
):
    """
    Ingest a transaction event and trigger fraud analysis.
    Returns the created FraudAlert if risk score warrants it.
    """
    from datetime import datetime

    container = get_container()
    supervisor = _get_supervisor()

    txn = Transaction(
        txn_id=body.txn_id,
        customer_id=body.customer_id,
        account_id=body.account_id,
        amount=body.amount,
        currency=body.currency,
        merchant=body.merchant,
        channel=body.channel,
        device_id=body.device_id,
        geo=body.geo,
        branch_id=body.branch_id,
        event_ts=body.event_ts or datetime.utcnow(),
        metadata=body.metadata,
    )

    # Persist transaction
    await container.transactions.save(txn)

    # Run fraud analysis
    alert = await supervisor.process_transaction(txn)

    if alert is None:
        return {"message": "Transaction processed, no alert raised"}

    return FraudAlertResponse(
        alert_id=alert.alert_id,
        txn_id=alert.txn_id,
        customer_id=alert.customer_id,
        risk_score=alert.risk_score,
        risk_level=alert.risk_level,
        reasons=alert.reasons,
        recommended_action=alert.recommended_action,
        ai_explanation=alert.ai_explanation,
        status=alert.status,
        created_at=alert.created_at,
    )


@router.get("/alerts", response_model=list[FraudAlertResponse])
async def list_fraud_alerts(
    limit: int = 50,
    _user=Depends(require_roles(UserRole.FRAUD_ANALYST, UserRole.COMPLIANCE_REVIEWER)),
):
    """List pending fraud alerts ordered by risk score (highest first)."""
    container = get_container()
    alerts = await container.fraud.list_pending_alerts(limit=limit)
    return [
        FraudAlertResponse(
            alert_id=a.alert_id,
            txn_id=a.txn_id,
            customer_id=a.customer_id,
            risk_score=a.risk_score,
            risk_level=a.risk_level,
            reasons=a.reasons,
            recommended_action=a.recommended_action,
            ai_explanation=a.ai_explanation,
            status=a.status,
            created_at=a.created_at,
        )
        for a in alerts
    ]


@router.get("/alerts/{alert_id}", response_model=FraudAlertResponse)
async def get_fraud_alert(
    alert_id: str,
    _user=Depends(require_roles(UserRole.FRAUD_ANALYST, UserRole.COMPLIANCE_REVIEWER)),
):
    container = get_container()
    alert = await container.fraud.get_alert_by_id(alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail=f"Alert {alert_id} not found")
    return FraudAlertResponse(
        alert_id=alert.alert_id,
        txn_id=alert.txn_id,
        customer_id=alert.customer_id,
        risk_score=alert.risk_score,
        risk_level=alert.risk_level,
        reasons=alert.reasons,
        recommended_action=alert.recommended_action,
        ai_explanation=alert.ai_explanation,
        status=alert.status,
        created_at=alert.created_at,
    )


@router.post("/alerts/{alert_id}/approve", response_model=FraudAlertResponse)
async def approve_fraud_alert(
    alert_id: str,
    body: FraudAlertApproveRequest,
    _user=Depends(require_roles(UserRole.FRAUD_ANALYST)),
):
    """
    Human-in-the-loop gate: analyst approves or declines the recommended action.
    This is the ONLY path that can change a fraud alert from pending to actioned.
    """
    container = get_container()

    if body.decision not in ("approved", "declined", "escalated"):
        raise HTTPException(
            status_code=400,
            detail="decision must be 'approved', 'declined', or 'escalated'",
        )

    alert = await container.fraud.update_alert_status(
        alert_id=alert_id,
        status=(
            "confirmed_fraud" if body.decision == "approved"
            else ("escalated" if body.decision == "escalated" else "cleared")
        ),
        analyst_id=body.analyst_id,
        decision=body.decision,
        notes=body.notes,
    )

    # Append audit event
    await container.audit.append(
        AuditEvent(
            event_id=new_audit_id(),
            actor_type=AuditActor.HUMAN,
            actor_id=body.analyst_id,
            action=AuditAction.FRAUD_ALERT_APPROVED if body.decision == "approved"
            else (AuditAction.FRAUD_ALERT_ESCALATED if body.decision == "escalated"
                  else AuditAction.FRAUD_ALERT_DECLINED),
            related_object_id=alert_id,
            related_object_type="fraud_alert",
            customer_id=alert.customer_id,
            notes=body.notes,
            reason_code=body.decision,
        )
    )

    return FraudAlertResponse(
        alert_id=alert.alert_id,
        txn_id=alert.txn_id,
        customer_id=alert.customer_id,
        risk_score=alert.risk_score,
        risk_level=alert.risk_level,
        reasons=alert.reasons,
        recommended_action=alert.recommended_action,
        ai_explanation=alert.ai_explanation,
        status=alert.status,
        created_at=alert.created_at,
    )

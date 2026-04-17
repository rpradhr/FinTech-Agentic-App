"""Customer interactions and sentiment API endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.auth import UserRole, require_roles
from app.api.schemas import (
    CustomerSignalResponse,
    InteractionIngestRequest,
)
from app.application.orchestrator import build_supervisor
from app.core.container import get_container
from app.core.ids import new_interaction_id
from app.domain.models import Interaction

router = APIRouter(prefix="/api/interactions", tags=["interactions"])


@router.post("/analyze", status_code=status.HTTP_202_ACCEPTED)
async def analyze_interaction(
    body: InteractionIngestRequest,
    _user=Depends(require_roles(UserRole.CX_LEAD, UserRole.SERVICE_ACCOUNT, UserRole.ADMIN)),
):
    """Ingest a customer interaction and run sentiment analysis."""

    container = get_container()
    supervisor = build_supervisor(container)

    interaction = Interaction(
        interaction_id=body.interaction_id or new_interaction_id(),
        customer_id=body.customer_id,
        source=body.source,
        content=body.content,
        branch_id=body.branch_id,
        channel_metadata=body.channel_metadata,
    )

    await container.interactions.save_interaction(interaction)
    await supervisor.process_interaction(interaction)

    return {"message": "Interaction analyzed", "interaction_id": interaction.interaction_id}


@router.get(
    "/customers/{customer_id}/signals",
    response_model=CustomerSignalResponse,
)
async def get_customer_signals(
    customer_id: str,
    _user=Depends(
        require_roles(
            UserRole.CX_LEAD,
            UserRole.FINANCIAL_ADVISOR,
            UserRole.FRAUD_ANALYST,
            UserRole.COMPLIANCE_REVIEWER,
        )
    ),
):
    """Return the aggregated customer sentiment signal."""

    container = get_container()
    signal = await container.customers.get_customer_signal(customer_id)
    if signal is None:
        raise HTTPException(status_code=404, detail=f"No signal found for customer {customer_id}")
    return CustomerSignalResponse(
        customer_id=signal.customer_id,
        overall_sentiment=signal.overall_sentiment,
        recent_drivers=signal.recent_drivers,
        churn_risk=signal.churn_risk,
        suppress_cross_sell=signal.suppress_cross_sell,
        updated_at=signal.updated_at,
    )

"""Branch performance monitor API endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.auth import UserRole, require_roles
from app.api.schemas import BranchDashboardEntry, BranchInsightResponse
from app.application.orchestrator import build_supervisor
from app.core.container import get_container

router = APIRouter(prefix="/api/branches", tags=["branches"])


@router.get("/{branch_id}/insights", response_model=list[BranchInsightResponse])
async def get_branch_insights(
    branch_id: str,
    limit: int = 10,
    _user=Depends(require_roles(UserRole.BRANCH_MANAGER, UserRole.ADMIN)),
):
    """Return recent AI-generated insights for a branch."""
    container = get_container()
    insights = await container.branches.get_insights_by_branch(branch_id, limit=limit)
    return [
        BranchInsightResponse(
            insight_id=i.insight_id,
            branch_id=i.branch_id,
            issue_summary=i.issue_summary,
            probable_causes=i.probable_causes,
            ranked_recommendations=i.ranked_recommendations,
            created_at=i.created_at,
        )
        for i in insights
    ]


@router.post("/{branch_id}/analyze", status_code=202)
async def trigger_branch_analysis(
    branch_id: str,
    _user=Depends(require_roles(UserRole.BRANCH_MANAGER, UserRole.ADMIN)),
):
    """Trigger on-demand branch anomaly analysis."""
    container = get_container()
    supervisor = build_supervisor(container)
    insight = await supervisor.analyze_branch(branch_id)
    if insight is None:
        return {"message": "No anomalies detected for this branch"}
    return {"message": "Branch insight created", "insight_id": insight.insight_id}


@router.get("/dashboard", response_model=list[BranchDashboardEntry])
async def branches_dashboard(
    _user=Depends(require_roles(UserRole.BRANCH_MANAGER, UserRole.ADMIN)),
):
    """Return latest KPI snapshot for all branches."""
    container = get_container()
    entries = await container.branches.list_branches_dashboard()
    return [BranchDashboardEntry(**e) for e in entries]

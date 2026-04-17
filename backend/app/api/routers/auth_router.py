"""Dev-only auth endpoints for obtaining test tokens."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.api.auth import create_dev_token
from app.api.schemas import DevTokenRequest, DevTokenResponse
from app.core.config import AppEnv, get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/dev-token", response_model=DevTokenResponse)
async def get_dev_token(body: DevTokenRequest):
    """
    Development-only endpoint to obtain a test JWT.
    DISABLED in staging and production.
    """
    settings = get_settings()
    if settings.app_env not in (AppEnv.DEVELOPMENT, AppEnv.TEST):
        raise HTTPException(
            status_code=404,
            detail="Not found",  # Don't reveal this endpoint exists in prod
        )
    token = create_dev_token(user_id=body.user_id, roles=body.roles)
    return DevTokenResponse(access_token=token)

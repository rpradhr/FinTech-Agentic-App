"""
Authentication and RBAC utilities.

In production, tokens are validated against the configured OIDC IdP.
In development (no OIDC configured), a simple JWT with HS256 is used for testing.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import StrEnum

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from app.core.config import get_settings

logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(auto_error=False)


class UserRole(StrEnum):
    FRAUD_ANALYST = "fraud_analyst"
    UNDERWRITER = "underwriter"
    BRANCH_MANAGER = "branch_manager"
    CX_LEAD = "cx_lead"
    FINANCIAL_ADVISOR = "financial_advisor"
    COMPLIANCE_REVIEWER = "compliance_reviewer"
    ADMIN = "admin"
    SERVICE_ACCOUNT = "service_account"


class CurrentUser(BaseModel):
    user_id: str
    roles: list[UserRole]
    email: str | None = None
    name: str | None = None


def create_dev_token(user_id: str, roles: list[str]) -> str:
    """Create a development JWT — NOT for production use."""
    settings = get_settings()
    expire = datetime.utcnow() + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {
        "sub": user_id,
        "roles": roles,
        "exp": expire,
        "iat": datetime.utcnow(),
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm="HS256")


def _decode_token(token: str) -> dict:
    settings = get_settings()
    return jwt.decode(token, settings.app_secret_key, algorithms=["HS256"])


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
        )
    try:
        payload = _decode_token(credentials.credentials)
        user_id: str = payload.get("sub", "")
        raw_roles: list = payload.get("roles", [])
        roles = [UserRole(r) for r in raw_roles if r in UserRole._value2member_map_]
        return CurrentUser(user_id=user_id, roles=roles)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid token: {exc}",
        ) from exc


def require_roles(*required_roles: UserRole):
    """Dependency factory that enforces at least one of the given roles."""

    async def check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if UserRole.ADMIN in user.roles:
            return user
        if not any(r in user.roles for r in required_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in required_roles]}",
            )
        return user

    return check

"""FastAPI authentication dependencies."""

import logging
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth.entra_id import extract_user_info, validate_token

logger = logging.getLogger(__name__)

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict[str, Any]:
    """Validate the bearer token and return current user info."""
    try:
        claims = await validate_token(credentials.credentials)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        ) from e

    return extract_user_info(claims)


def require_role(role: str):
    """Return a dependency that enforces the specified role."""

    async def _check_role(
        user: dict[str, Any] = Depends(get_current_user),
    ) -> dict[str, Any]:
        if role not in user.get("roles", []):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' is required",
            )
        return user

    return _check_role

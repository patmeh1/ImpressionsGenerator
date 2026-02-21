"""Tests for authentication middleware and role-based access control."""

from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest

from app.auth.entra_id import extract_user_info, validate_token
from app.auth.dependencies import get_current_user, require_role


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_token_claims(
    roles: list[str] | None = None,
    expired: bool = False,
    user_id: str = "user-001",
) -> dict:
    now = datetime.utcnow()
    exp = now - timedelta(hours=1) if expired else now + timedelta(hours=1)
    return {
        "oid": user_id,
        "name": "Test User",
        "preferred_username": "test@hospital.org",
        "roles": roles or ["Doctor"],
        "tid": "test-tenant",
        "exp": exp.timestamp(),
        "iat": now.timestamp(),
        "iss": "https://sts.windows.net/test-tenant/",
        "aud": "api://test-client",
    }


class _FakeCredentials:
    def __init__(self, token: str = "valid-token"):
        self.credentials = token


# ---------------------------------------------------------------------------
# T07 – valid token returns 200 (user info extracted)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_valid_token_returns_200():
    """A valid token should yield user info without raising."""
    claims = _make_token_claims()
    with patch(
        "app.auth.dependencies.validate_token",
        new_callable=AsyncMock,
        return_value=claims,
    ):
        user = await get_current_user(_FakeCredentials())
        assert user["user_id"] == "user-001"
        assert "Doctor" in user["roles"]


# ---------------------------------------------------------------------------
# T08 – invalid token returns 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_invalid_token_returns_401():
    """An invalid/corrupt token must raise 401."""
    with patch(
        "app.auth.dependencies.validate_token",
        new_callable=AsyncMock,
        side_effect=ValueError("Token validation failed"),
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_FakeCredentials("bad-token"))
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# T09 – doctor cannot access admin endpoints (403)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_doctor_cannot_access_admin_endpoints():
    """A Doctor-role user must be rejected from Admin-only endpoints."""
    doctor_claims = _make_token_claims(roles=["Doctor"])
    with patch(
        "app.auth.dependencies.validate_token",
        new_callable=AsyncMock,
        return_value=doctor_claims,
    ):
        # require_role returns a dependency that receives the user dict
        # (already resolved by get_current_user in the DI chain).
        checker = require_role("Admin")
        from fastapi import HTTPException

        # Simulate what FastAPI does: first resolve get_current_user,
        # then pass the user dict into the role checker.
        user = await get_current_user(_FakeCredentials())
        with pytest.raises(HTTPException) as exc_info:
            await checker(user)
        assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------------
# Missing token → 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_missing_token_returns_401():
    """A request without any credentials should raise 401."""
    with patch(
        "app.auth.dependencies.validate_token",
        new_callable=AsyncMock,
        side_effect=ValueError("Missing token"),
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_FakeCredentials(""))
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# Expired token → 401
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_expired_token_returns_401():
    """An expired token should be rejected with 401."""
    with patch(
        "app.auth.dependencies.validate_token",
        new_callable=AsyncMock,
        side_effect=ValueError("Token expired"),
    ):
        from fastapi import HTTPException

        with pytest.raises(HTTPException) as exc_info:
            await get_current_user(_FakeCredentials("expired-token"))
        assert exc_info.value.status_code == 401


# ---------------------------------------------------------------------------
# extract_user_info unit tests
# ---------------------------------------------------------------------------
def test_extract_user_info_returns_expected_fields():
    claims = _make_token_claims(roles=["Admin", "Doctor"])
    info = extract_user_info(claims)
    assert info["user_id"] == "user-001"
    assert info["name"] == "Test User"
    assert info["email"] == "test@hospital.org"
    assert set(info["roles"]) == {"Admin", "Doctor"}
    assert info["tenant_id"] == "test-tenant"

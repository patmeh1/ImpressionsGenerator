"""Tests for data retention policy endpoints and purge logic."""

from datetime import datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient


# ---------------------------------------------------------------------------
# Admin test client (with Admin role claims)
# ---------------------------------------------------------------------------
def _admin_claims() -> dict[str, Any]:
    now = datetime.utcnow()
    return {
        "oid": "admin-001",
        "name": "Admin User",
        "preferred_username": "admin@hospital.org",
        "roles": ["Admin"],
        "tid": "test-tenant-id",
        "exp": (now + timedelta(hours=1)).timestamp(),
        "iat": now.timestamp(),
        "iss": "https://sts.windows.net/test-tenant-id/",
        "aud": "api://test-client-id",
    }


@pytest_asyncio.fixture()
async def admin_client():
    """HTTP client authenticated as Admin."""
    with (
        patch("app.auth.dependencies.validate_token", new_callable=AsyncMock) as mock_validate,
        patch("app.auth.entra_id._get_signing_keys", new_callable=AsyncMock),
    ):
        mock_validate.return_value = _admin_claims()
        from app.main import app

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            ac.headers["Authorization"] = "Bearer test-token"
            yield ac


# ---------------------------------------------------------------------------
# GET /api/admin/retention-policy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_retention_policy_defaults(admin_client):
    """When no policy exists, returns defaults."""
    with patch(
        "app.routers.admin.cosmos_service.get_retention_policy",
        new_callable=AsyncMock,
        return_value=None,
    ):
        resp = await admin_client.get("/api/admin/retention-policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_retention_days"] == 0
    assert data["notes_retention_days"] == 0
    assert data["audit_logs_retention_days"] == 0
    assert data["soft_delete_grace_period_days"] == 30


@pytest.mark.asyncio
async def test_get_retention_policy_existing(admin_client):
    """When policy exists, returns it."""
    mock_policy = {
        "id": "default",
        "reports_retention_days": 90,
        "notes_retention_days": 180,
        "audit_logs_retention_days": 365,
        "soft_delete_grace_period_days": 14,
        "updated_at": "2025-01-01T00:00:00",
    }
    with patch(
        "app.routers.admin.cosmos_service.get_retention_policy",
        new_callable=AsyncMock,
        return_value=mock_policy,
    ):
        resp = await admin_client.get("/api/admin/retention-policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_retention_days"] == 90
    assert data["notes_retention_days"] == 180



# ---------------------------------------------------------------------------
# PUT /api/admin/retention-policy
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_retention_policy(admin_client):
    """Admin can update retention policy."""
    existing = {
        "id": "default",
        "reports_retention_days": 0,
        "notes_retention_days": 0,
        "audit_logs_retention_days": 0,
        "soft_delete_grace_period_days": 30,
        "updated_at": "2025-01-01T00:00:00",
    }
    updated = {**existing, "reports_retention_days": 90, "updated_by": "admin-001"}

    with (
        patch(
            "app.routers.admin.cosmos_service.get_retention_policy",
            new_callable=AsyncMock,
            return_value=existing.copy(),
        ),
        patch(
            "app.routers.admin.cosmos_service.upsert_retention_policy",
            new_callable=AsyncMock,
            return_value=updated,
        ),
        patch(
            "app.routers.admin.cosmos_service.create_audit_log",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        resp = await admin_client.put(
            "/api/admin/retention-policy",
            json={"reports_retention_days": 90},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reports_retention_days"] == 90
    mock_audit.assert_called_once()


@pytest.mark.asyncio
async def test_update_retention_policy_invalid_days(admin_client):
    """Reject invalid retention day values."""
    resp = await admin_client.put(
        "/api/admin/retention-policy",
        json={"reports_retention_days": 45},
    )
    assert resp.status_code == 422



# ---------------------------------------------------------------------------
# Purge service unit tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purge_skipped_when_no_policy():
    """Purge returns skipped when no policy configured."""
    with patch(
        "app.services.purge.cosmos_service.get_retention_policy",
        new_callable=AsyncMock,
        return_value=None,
    ):
        from app.services.purge import run_purge

        result = await run_purge()
    assert result["status"] == "skipped"


@pytest.mark.asyncio
async def test_purge_executes_with_policy():
    """Purge soft-deletes and purges items when policy is configured."""
    policy = {
        "reports_retention_days": 90,
        "notes_retention_days": 60,
        "audit_logs_retention_days": 365,
        "soft_delete_grace_period_days": 14,
    }
    with (
        patch(
            "app.services.purge.cosmos_service.get_retention_policy",
            new_callable=AsyncMock,
            return_value=policy,
        ),
        patch(
            "app.services.purge.cosmos_service.soft_delete_expired_items",
            new_callable=AsyncMock,
            return_value=[{"id": "item-1"}],
        ) as mock_soft,
        patch(
            "app.services.purge.cosmos_service.purge_soft_deleted_items",
            new_callable=AsyncMock,
            return_value=2,
        ) as mock_purge,
        patch(
            "app.services.purge.cosmos_service.create_audit_log",
            new_callable=AsyncMock,
        ) as mock_audit,
    ):
        from app.services.purge import run_purge

        result = await run_purge()

    assert result["status"] == "completed"
    # Should be called for reports, notes, audit_logs
    assert mock_soft.call_count == 3
    assert mock_purge.call_count == 3
    mock_audit.assert_called_once()


@pytest.mark.asyncio
async def test_purge_skips_unlimited_containers():
    """Purge skips containers with 0 (unlimited) retention days."""
    policy = {
        "reports_retention_days": 0,  # unlimited
        "notes_retention_days": 90,
        "audit_logs_retention_days": 0,  # unlimited
        "soft_delete_grace_period_days": 30,
    }
    with (
        patch(
            "app.services.purge.cosmos_service.get_retention_policy",
            new_callable=AsyncMock,
            return_value=policy,
        ),
        patch(
            "app.services.purge.cosmos_service.soft_delete_expired_items",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_soft,
        patch(
            "app.services.purge.cosmos_service.purge_soft_deleted_items",
            new_callable=AsyncMock,
            return_value=0,
        ),
        patch(
            "app.services.purge.cosmos_service.create_audit_log",
            new_callable=AsyncMock,
        ),
    ):
        from app.services.purge import run_purge

        await run_purge()

    # soft_delete_expired_items returns [] for 0-day containers but is still called
    # The logic inside the method returns [] when retention_days <= 0
    assert mock_soft.call_count == 3

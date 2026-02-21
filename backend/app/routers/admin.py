"""Admin management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends

from app.auth.dependencies import require_role
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/stats")
async def get_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Get overall system statistics. Admin only."""
    stats = await cosmos_service.get_stats()
    return stats


@router.get("/doctors")
async def list_doctors_with_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> list[dict[str, Any]]:
    """List all doctors with their usage statistics. Admin only."""
    return await cosmos_service.get_doctors_with_stats()

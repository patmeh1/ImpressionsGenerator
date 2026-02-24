"""Admin management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import require_role
from app.models.retention_policy import RetentionPolicyResponse, RetentionPolicyUpdate
from app.services.audit import audit_service
from app.services.cosmos_db import cosmos_service
from app.services.purge import run_purge

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/admin", tags=["admin"])

VALID_RETENTION_DAYS = {0, 30, 60, 90, 180, 365}


@router.get("/stats")
async def get_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Get overall system statistics. Admin only."""
    audit_service.log_data_access(user, "stats", "", "read")
    stats = await cosmos_service.get_stats()
    return stats


@router.get("/doctors")
async def list_doctors_with_stats(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> list[dict[str, Any]]:
    """List all doctors with their usage statistics. Admin only."""
    audit_service.log_data_access(user, "doctors_stats", "", "list")
    return await cosmos_service.get_doctors_with_stats()


@router.get("/doctors/{doctor_id}/feedback-scores")
async def get_doctor_feedback_scores(
    doctor_id: str,
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Get aggregate style quality scores for a doctor. Admin only."""
    return await cosmos_service.get_average_rating_for_doctor(doctor_id)


@router.get("/retention-policy", response_model=RetentionPolicyResponse)
async def get_retention_policy(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Get the current data retention policy. Admin only."""
    policy = await cosmos_service.get_retention_policy()
    if policy is None:
        # Return defaults when no policy exists
        from datetime import datetime

        return {
            "id": "default",
            "reports_retention_days": 0,
            "notes_retention_days": 0,
            "audit_logs_retention_days": 0,
            "soft_delete_grace_period_days": 30,
            "updated_at": datetime.utcnow().isoformat(),
        }
    return policy


@router.put("/retention-policy", response_model=RetentionPolicyResponse)
async def update_retention_policy(
    body: RetentionPolicyUpdate,
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Update the data retention policy. Admin only."""
    update_data = body.model_dump(exclude_none=True)

    # Validate retention day values
    for field in ("reports_retention_days", "notes_retention_days", "audit_logs_retention_days"):
        if field in update_data and update_data[field] not in VALID_RETENTION_DAYS:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Invalid value for {field}. Allowed: {sorted(VALID_RETENTION_DAYS)}",
            )

    # Merge with existing policy
    existing = await cosmos_service.get_retention_policy() or {
        "reports_retention_days": 0,
        "notes_retention_days": 0,
        "audit_logs_retention_days": 0,
        "soft_delete_grace_period_days": 30,
    }
    existing.update(update_data)
    existing["updated_by"] = user.get("user_id", "unknown")

    result = await cosmos_service.upsert_retention_policy(existing)

    # Audit log for the policy change
    await cosmos_service.create_audit_log({
        "action": "retention_policy_updated",
        "details": update_data,
        "performed_by": user.get("user_id", "unknown"),
    })

    return result


@router.post("/retention-policy/purge")
async def trigger_purge(
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Manually trigger a data purge based on retention policy. Admin only."""
    result = await run_purge()

    return result

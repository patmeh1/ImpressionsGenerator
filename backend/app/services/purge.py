"""Background purge service for data retention enforcement."""

import logging
from typing import Any

from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)

# Map of retention policy field → Cosmos DB container
_RETENTION_CONTAINERS: dict[str, str] = {
    "reports_retention_days": "reports",
    "notes_retention_days": "notes",
    "audit_logs_retention_days": "audit_logs",
}


async def run_purge() -> dict[str, Any]:
    """Execute the retention purge cycle.

    1. Read the current retention policy.
    2. For each data category, soft-delete expired items.
    3. Permanently purge items past the soft-delete grace period.
    4. Record an audit log entry for the operation.

    Returns a summary dict.
    """
    policy = await cosmos_service.get_retention_policy()
    if policy is None:
        logger.info("No retention policy configured – skipping purge")
        return {"status": "skipped", "reason": "no_policy_configured"}

    grace_period = policy.get("soft_delete_grace_period_days", 30)
    summary: dict[str, Any] = {"soft_deleted": {}, "purged": {}}

    for field, container in _RETENTION_CONTAINERS.items():
        retention_days = policy.get(field, 0)

        # Soft-delete expired items
        deleted = await cosmos_service.soft_delete_expired_items(container, retention_days)
        summary["soft_deleted"][container] = len(deleted)

        # Permanently purge items past grace period
        purged = await cosmos_service.purge_soft_deleted_items(container, grace_period)
        summary["purged"][container] = purged

    # Audit log for this purge run
    await cosmos_service.create_audit_log({
        "action": "data_purge",
        "details": summary,
        "triggered_by": "system",
    })

    logger.info("Purge cycle complete: %s", summary)
    return {"status": "completed", "summary": summary}

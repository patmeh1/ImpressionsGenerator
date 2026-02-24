"""Data retention policy models."""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class RetentionDays(int, Enum):
    """Allowed retention period values in days."""
    DAYS_30 = 30
    DAYS_60 = 60
    DAYS_90 = 90
    DAYS_180 = 180
    DAYS_365 = 365
    UNLIMITED = 0  # 0 means unlimited


class RetentionPolicyUpdate(BaseModel):
    """Request model for updating retention policy."""
    reports_retention_days: Optional[int] = Field(
        None,
        description="Retention period for reports in days (30/60/90/180/365 or 0 for unlimited)",
    )
    notes_retention_days: Optional[int] = Field(
        None,
        description="Retention period for historical notes in days (30/60/90/180/365 or 0 for unlimited)",
    )
    audit_logs_retention_days: Optional[int] = Field(
        None,
        description="Retention period for audit logs in days (30/60/90/180/365 or 0 for unlimited)",
    )
    soft_delete_grace_period_days: Optional[int] = Field(
        None,
        ge=0,
        le=90,
        description="Grace period in days before permanently deleting soft-deleted items (0-90)",
    )


class RetentionPolicyResponse(BaseModel):
    """Response model for retention policy."""
    id: str
    reports_retention_days: int = Field(
        default=0, description="Retention period for reports (0 = unlimited)"
    )
    notes_retention_days: int = Field(
        default=0, description="Retention period for notes (0 = unlimited)"
    )
    audit_logs_retention_days: int = Field(
        default=0, description="Retention period for audit logs (0 = unlimited)"
    )
    soft_delete_grace_period_days: int = Field(
        default=30, description="Grace period before permanent deletion"
    )
    updated_at: str
    updated_by: Optional[str] = None

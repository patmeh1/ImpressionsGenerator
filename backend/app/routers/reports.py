"""Report management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.auth.dependencies import get_current_user
from app.models.feedback import FeedbackCreate, FeedbackResponse
from app.models.report import ReportResponse, ReportUpdate
from app.services.ai_search import ai_search_service
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/reports", tags=["reports"])


@router.get("", response_model=list[ReportResponse])
async def list_reports(
    doctor_id: str | None = Query(default=None),
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List reports. Admins see all; doctors see only their own."""
    if "Admin" in user.get("roles", []):
        return await cosmos_service.list_reports(doctor_id=doctor_id)
    else:
        return await cosmos_service.list_reports(doctor_id=user["user_id"])


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a specific report."""
    report = await _find_report(report_id, user)
    return report


@router.put("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: str,
    body: ReportUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update/edit a report's findings, impressions, or recommendations."""
    report = await _find_report(report_id, user)
    data = body.model_dump(exclude_unset=True)
    updated = await cosmos_service.update_report(
        report_id=report_id,
        doctor_id=report["doctor_id"],
        data=data,
    )
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return updated


@router.post("/{report_id}/approve", response_model=ReportResponse)
async def approve_report(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark a report as final/approved."""
    report = await _find_report(report_id, user)
    approved = await cosmos_service.approve_report(
        report_id=report_id,
        doctor_id=report["doctor_id"],
    )
    if not approved:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return approved


@router.post("/{report_id}/reject", response_model=ReportResponse)
async def reject_report(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Mark a report as rejected."""
    report = await _find_report(report_id, user)
    rejected = await cosmos_service.reject_report(
        report_id=report_id,
        doctor_id=report["doctor_id"],
    )
    if not rejected:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return rejected


@router.get("/{report_id}/versions")
async def get_report_versions(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get version history for a report."""
    report = await _find_report(report_id, user)
    return report.get("versions", [])


@router.post("/{report_id}/feedback", response_model=FeedbackResponse, status_code=status.HTTP_201_CREATED)
async def submit_feedback(
    report_id: str,
    body: FeedbackCreate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Submit a style accuracy rating for a generated report."""
    report = await _find_report(report_id, user)
    feedback = await cosmos_service.create_feedback(
        report_id=report_id,
        doctor_id=report["doctor_id"],
        data=body.model_dump(),
    )
    # Best-effort: update the search index with the rating so future
    # RAG retrieval can weight this report higher/lower.
    try:
        await ai_search_service.update_document_rating(
            doc_id=report_id,
            style_rating=float(body.rating),
        )
    except Exception as e:
        logger.warning("Failed to update search index rating for report %s: %s", report_id, e)
    return feedback


@router.get("/{report_id}/feedback", response_model=list[FeedbackResponse])
async def get_report_feedback(
    report_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """Get all feedback for a report."""
    await _find_report(report_id, user)
    return await cosmos_service.get_feedback_for_report(report_id)


async def _find_report(report_id: str, user: dict[str, Any]) -> dict[str, Any]:
    """Find a report and verify access permissions."""
    # Try finding with user's doctor_id first
    doctor_id = user.get("user_id", "")
    report = await cosmos_service.get_report(report_id, doctor_id)

    if not report and "Admin" in user.get("roles", []):
        # Admin: search across all doctors
        all_reports = await cosmos_service.list_reports()
        report = next((r for r in all_reports if r["id"] == report_id), None)

    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    if "Admin" not in user.get("roles", []) and report.get("doctor_id") != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own reports",
        )

    return report

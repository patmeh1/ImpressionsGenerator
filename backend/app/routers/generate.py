"""Report generation endpoint."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user
from app.models.report import GenerateRequest
from app.services.generation import generation_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/generate", tags=["generate"])


@router.post("")
async def generate_report(
    body: GenerateRequest,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """
    Generate a structured clinical report from dictated text.

    Accepts dictated text, doctor_id, report_type, and body_region.
    Returns a structured report with findings, impressions, recommendations,
    and grounding validation results.
    """
    # Ensure the user is the doctor or an admin
    if "Admin" not in user.get("roles", []) and user.get("user_id") != body.doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only generate reports for yourself",
        )

    try:
        report = await generation_service.generate(
            dictated_text=body.dictated_text,
            doctor_id=body.doctor_id,
            report_type=body.report_type,
            body_region=body.body_region,
        )
    except RuntimeError as e:
        logger.error("Report generation failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Report generation failed: {e}",
        ) from e
    except Exception as e:
        logger.exception("Unexpected error during report generation")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during report generation",
        ) from e

    return report

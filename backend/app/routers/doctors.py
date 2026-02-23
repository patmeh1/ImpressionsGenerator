"""Doctor profile management endpoints."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import get_current_user, require_role
from app.models.doctor import DoctorCreate, DoctorResponse, DoctorUpdate
from app.models.style_profile import StyleProfile
from app.services.cosmos_db import cosmos_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/doctors", tags=["doctors"])


@router.get("", response_model=list[DoctorResponse])
async def list_doctors(
    user: dict[str, Any] = Depends(get_current_user),
) -> list[dict[str, Any]]:
    """List all doctors. Admins see all; doctors see only themselves."""
    if "Admin" in user.get("roles", []):
        return await cosmos_service.list_doctors()
    else:
        doctor = await cosmos_service.get_doctor(user["user_id"])
        return [doctor] if doctor else []


@router.get("/{doctor_id}", response_model=DoctorResponse)
async def get_doctor(
    doctor_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get a doctor profile by ID."""
    _enforce_doctor_access(user, doctor_id)
    doctor = await cosmos_service.get_doctor(doctor_id)
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.post("", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
async def create_doctor(
    body: DoctorCreate,
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> dict[str, Any]:
    """Create a new doctor profile. Admin only."""
    data = body.model_dump()
    return await cosmos_service.create_doctor(data)


@router.put("/{doctor_id}", response_model=DoctorResponse)
async def update_doctor(
    doctor_id: str,
    body: DoctorUpdate,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Update a doctor profile. Admin or the doctor themselves."""
    _enforce_doctor_access(user, doctor_id)
    data = body.model_dump(exclude_unset=True)
    updated = await cosmos_service.update_doctor(doctor_id, data)
    if not updated:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return updated


@router.get("/{doctor_id}/style-profile", response_model=StyleProfile)
async def get_style_profile(
    doctor_id: str,
    user: dict[str, Any] = Depends(get_current_user),
) -> dict[str, Any]:
    """Get the extracted writing style profile for a doctor."""
    _enforce_doctor_access(user, doctor_id)
    profile = await cosmos_service.get_style_profile(doctor_id)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Style profile not found for this doctor",
        )
    return profile


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_doctor(
    doctor_id: str,
    user: dict[str, Any] = Depends(require_role("Admin")),
) -> None:
    """Delete a doctor profile. Admin only."""
    deleted = await cosmos_service.delete_doctor(doctor_id)
    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")


def _enforce_doctor_access(user: dict[str, Any], doctor_id: str) -> None:
    """Ensure non-admin users can only access their own profile."""
    if "Admin" in user.get("roles", []):
        return
    if user.get("user_id") != doctor_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only access your own profile",
        )

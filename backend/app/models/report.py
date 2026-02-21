"""Pydantic models for reports and generation requests."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class ReportStatus(str, Enum):
    DRAFT = "draft"
    EDITED = "edited"
    FINAL = "final"


class GenerateRequest(BaseModel):
    dictated_text: str = Field(..., min_length=1)
    doctor_id: str = Field(..., min_length=1)
    report_type: str = Field(..., min_length=1, description="e.g. CT, MRI, X-Ray, Ultrasound, PET")
    body_region: str = Field(..., min_length=1, description="e.g. Chest, Abdomen, Brain, Spine")


class ReportVersion(BaseModel):
    version: int
    findings: str
    impressions: str
    recommendations: str
    status: ReportStatus
    edited_at: datetime


class ReportResponse(BaseModel):
    id: str
    doctor_id: str
    input_text: str
    findings: str
    impressions: str
    recommendations: str
    report_type: str = ""
    body_region: str = ""
    status: ReportStatus = ReportStatus.DRAFT
    versions: list[ReportVersion] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReportUpdate(BaseModel):
    findings: str | None = None
    impressions: str | None = None
    recommendations: str | None = None

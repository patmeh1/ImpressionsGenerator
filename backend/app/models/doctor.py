"""Pydantic models for doctor profiles."""

from datetime import datetime

from pydantic import BaseModel, Field


class DoctorCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    specialty: str = Field(..., min_length=1, max_length=100)
    department: str = Field(default="", max_length=100)


class DoctorUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    specialty: str | None = Field(default=None, min_length=1, max_length=100)
    department: str | None = Field(default=None, max_length=100)


class DoctorResponse(BaseModel):
    id: str
    name: str
    specialty: str
    department: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}

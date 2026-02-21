"""Pydantic models for historical notes."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field


class SourceType(str, Enum):
    UPLOAD = "upload"
    PASTE = "paste"


class NoteCreate(BaseModel):
    content: str = Field(..., min_length=1)
    source_type: SourceType = SourceType.PASTE
    file_name: str | None = None


class NoteResponse(BaseModel):
    id: str
    doctor_id: str
    content: str
    source_type: SourceType
    file_name: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}

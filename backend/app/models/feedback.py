"""Pydantic models for style quality feedback."""

from datetime import datetime

from pydantic import BaseModel, Field


class FeedbackCreate(BaseModel):
    rating: int = Field(..., ge=1, le=5, description="Style accuracy rating (1-5 stars)")
    feedback_text: str = Field(default="", description="Optional free-text feedback")


class FeedbackResponse(BaseModel):
    id: str
    report_id: str
    doctor_id: str
    rating: int
    feedback_text: str = ""
    created_at: datetime

    model_config = {"from_attributes": True}

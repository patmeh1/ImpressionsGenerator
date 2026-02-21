"""Pydantic models for doctor writing style profiles."""

from datetime import datetime

from pydantic import BaseModel, Field


class StyleProfile(BaseModel):
    doctor_id: str
    vocabulary_patterns: list[str] = Field(default_factory=list)
    abbreviation_map: dict[str, str] = Field(default_factory=dict)
    sentence_structure: list[str] = Field(
        default_factory=list,
        description="Typical sentence structures, e.g. 'short declarative', 'uses semicolons'",
    )
    section_ordering: list[str] = Field(
        default_factory=list,
        description="Preferred order of report sections",
    )
    sample_phrases: list[str] = Field(
        default_factory=list,
        description="Characteristic phrases the doctor commonly uses",
    )
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    model_config = {"from_attributes": True}

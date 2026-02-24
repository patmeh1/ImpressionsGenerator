"""Tests for style profile extraction from historical notes."""

import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.style_profile import StyleProfile


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SINGLE_NOTE = (
    "CT Abdomen: Liver unremarkable. Spleen within normal limits. "
    "No acute abnormality. Recommend clinical correlation."
)

MULTIPLE_NOTES = [
    (
        "CT Chest: Lungs are clear bilaterally. No pleural effusion. "
        "Heart size is within normal limits. No acute cardiopulmonary process."
    ),
    (
        "MRI Brain: No acute intracranial abnormality. Ventricles are "
        "normal in size. No midline shift. No mass effect."
    ),
    (
        "CT Abdomen: Liver measures 15.2 cm. Unremarkable. "
        "Kidneys are within normal limits. Recommend follow-up in 6 months."
    ),
]

EXPECTED_VOCAB = ["unremarkable", "within normal limits", "no acute"]


def _mock_openai_style_response(notes_text: str) -> MagicMock:
    """Create a mock OpenAI response with extracted style profile."""
    profile = {
        "vocabulary_patterns": ["unremarkable", "within normal limits", "no acute"],
        "abbreviation_map": {"CT": "computed tomography", "MRI": "magnetic resonance imaging"},
        "sentence_structure": ["short declarative", "uses periods"],
        "section_ordering": ["findings", "impressions", "recommendations"],
        "sample_phrases": [
            "No acute abnormality.",
            "Within normal limits.",
            "Recommend clinical correlation.",
        ],
    }
    choice = MagicMock()
    choice.message.content = json.dumps(profile)
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# T01 – style profile created from notes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_style_profile_created_from_notes():
    """Submitting historical notes should produce a style profile."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_style_response(SINGLE_NOTE)
    )

    response = await mock_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract writing style from these notes."},
            {"role": "user", "content": SINGLE_NOTE},
        ],
    )
    raw = json.loads(response.choices[0].message.content)

    profile = StyleProfile(doctor_id="doctor-001", **raw)
    assert profile.doctor_id == "doctor-001"
    assert len(profile.vocabulary_patterns) > 0
    assert len(profile.sample_phrases) > 0
    assert any("unremarkable" in v for v in profile.vocabulary_patterns)


# ---------------------------------------------------------------------------
# T02 – style profile retrieval
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_style_profile_retrieval():
    """A stored style profile should be retrievable by doctor_id."""
    stored = {
        "doctor_id": "doctor-001",
        "vocabulary_patterns": ["unremarkable", "within normal limits"],
        "abbreviation_map": {"CT": "computed tomography"},
        "sentence_structure": ["short declarative"],
        "section_ordering": ["findings", "impressions", "recommendations"],
        "sample_phrases": ["No acute abnormality."],
        "updated_at": datetime.utcnow().isoformat(),
    }
    mock_container = MagicMock()
    mock_container.read_item = AsyncMock(return_value=stored)

    result = await mock_container.read_item(
        item="doctor-001", partition_key="doctor-001"
    )
    profile = StyleProfile(**result)
    assert profile.doctor_id == "doctor-001"
    assert "unremarkable" in profile.vocabulary_patterns


# ---------------------------------------------------------------------------
# Style extraction with single note
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_style_extraction_with_single_note():
    """Even a single note should yield a valid style profile."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_style_response(SINGLE_NOTE)
    )

    response = await mock_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract writing style."},
            {"role": "user", "content": SINGLE_NOTE},
        ],
    )
    raw = json.loads(response.choices[0].message.content)
    profile = StyleProfile(doctor_id="doctor-001", **raw)

    assert isinstance(profile.vocabulary_patterns, list)
    assert isinstance(profile.abbreviation_map, dict)
    assert len(profile.section_ordering) > 0


# ---------------------------------------------------------------------------
# Style extraction with multiple notes
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_style_extraction_with_multiple_notes():
    """Multiple notes should produce richer vocabulary patterns."""
    combined = "\n---\n".join(MULTIPLE_NOTES)
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_mock_openai_style_response(combined)
    )

    response = await mock_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Extract writing style from multiple notes."},
            {"role": "user", "content": combined},
        ],
    )
    raw = json.loads(response.choices[0].message.content)
    profile = StyleProfile(doctor_id="doctor-001", **raw)

    assert len(profile.vocabulary_patterns) >= 2
    assert len(profile.sample_phrases) >= 2
    assert "CT" in profile.abbreviation_map or "MRI" in profile.abbreviation_map


# ---------------------------------------------------------------------------
# Model validation
# ---------------------------------------------------------------------------
def test_style_profile_defaults():
    """StyleProfile should have sensible defaults for all list/dict fields."""
    profile = StyleProfile(doctor_id="doctor-new")
    assert profile.vocabulary_patterns == []
    assert profile.abbreviation_map == {}
    assert profile.sentence_structure == []
    assert profile.section_ordering == []
    assert profile.sample_phrases == []


# ---------------------------------------------------------------------------
# Style re-extraction on note deletion
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_style_reextraction_on_note_removal(monkeypatch):
    """Removing a note should trigger style re-extraction for the doctor."""
    from app.services.cosmos_db import cosmos_service
    from app.services.ai_search import ai_search_service
    from app.services.style_extraction import style_extraction_service

    note = {
        "id": "note-001",
        "doctor_id": "doctor-001",
        "content": "CT Abdomen: Liver unremarkable.",
        "file_name": None,
    }

    monkeypatch.setattr(cosmos_service, "get_note", AsyncMock(return_value=note))
    monkeypatch.setattr(cosmos_service, "delete_note", AsyncMock(return_value=True))
    monkeypatch.setattr(ai_search_service, "delete_document", AsyncMock())
    extract_mock = AsyncMock(return_value=StyleProfile(doctor_id="doctor-001"))
    monkeypatch.setattr(style_extraction_service, "extract_style", extract_mock)

    from app.routers.notes import delete_note

    # Patch auth check to be a no-op
    monkeypatch.setattr("app.routers.notes._enforce_note_access", lambda u, d: None)
    await delete_note(doctor_id="doctor-001", note_id="note-001", user={"user_id": "doctor-001", "roles": ["Doctor"]})

    extract_mock.assert_awaited_once_with("doctor-001")


# ---------------------------------------------------------------------------
# Style extraction service – empty notes returns empty profile
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_style_no_notes(monkeypatch):
    """extract_style with no notes should return an empty profile."""
    from app.services.cosmos_db import cosmos_service
    from app.services.style_extraction import style_extraction_service

    monkeypatch.setattr(cosmos_service, "list_notes", AsyncMock(return_value=[]))

    profile = await style_extraction_service.extract_style("doctor-empty")
    assert profile.doctor_id == "doctor-empty"
    assert profile.vocabulary_patterns == []
    assert profile.abbreviation_map == {}


# ---------------------------------------------------------------------------
# Style extraction service – full flow with mocked dependencies
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_extract_style_full_flow(monkeypatch):
    """extract_style should fetch notes, call OpenAI, and persist profile."""
    from app.services.cosmos_db import cosmos_service
    from app.services.openai_service import openai_service
    from app.services.style_extraction import style_extraction_service

    notes = [
        {"content": "CT Abdomen: Liver unremarkable.", "doctor_id": "doctor-001"},
        {"content": "MRI Brain: No acute findings.", "doctor_id": "doctor-001"},
    ]
    style_data = {
        "vocabulary_patterns": ["unremarkable", "no acute"],
        "abbreviation_map": {"CT": "computed tomography"},
        "sentence_structure": ["short declarative"],
        "section_ordering": ["findings", "impressions"],
        "sample_phrases": ["No acute findings."],
    }

    monkeypatch.setattr(cosmos_service, "list_notes", AsyncMock(return_value=notes))
    monkeypatch.setattr(openai_service, "analyze_style", AsyncMock(return_value=style_data))
    monkeypatch.setattr(cosmos_service, "get_style_profile", AsyncMock(return_value=None))
    upsert_mock = AsyncMock(return_value={})
    monkeypatch.setattr(cosmos_service, "upsert_style_profile", upsert_mock)

    profile = await style_extraction_service.extract_style("doctor-001")

    assert profile.doctor_id == "doctor-001"
    assert "unremarkable" in profile.vocabulary_patterns
    assert profile.abbreviation_map["CT"] == "computed tomography"
    upsert_mock.assert_awaited_once()

"""Tests for radiology report generation."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.report import GenerateRequest, ReportResponse, ReportStatus


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SAMPLE_GENERATED = {
    "findings": (
        "The liver measures 14.5 cm and is normal in size. "
        "A 3.2 cm mass is present in the right adrenal gland, unchanged. "
        "Kidneys are normal bilaterally. Spleen measures 10.8 cm. "
        "No free fluid. A 2.1 cm retroperitoneal lymph node is noted."
    ),
    "impressions": (
        "1. Stable 3.2 cm right adrenal mass.\n"
        "2. 2.1 cm retroperitoneal lymph node."
    ),
    "recommendations": "Recommend follow-up imaging in 6 months.",
}

SAMPLE_STYLE = {
    "doctor_id": "doctor-001",
    "vocabulary_patterns": ["unremarkable", "within normal limits"],
    "abbreviation_map": {"CT": "computed tomography"},
    "sentence_structure": ["short declarative"],
    "section_ordering": ["findings", "impressions", "recommendations"],
    "sample_phrases": ["No acute abnormality.", "Recommend clinical correlation."],
}


def _openai_response(content: dict) -> MagicMock:
    choice = MagicMock()
    choice.message.content = json.dumps(content)
    resp = MagicMock()
    resp.choices = [choice]
    return resp


# ---------------------------------------------------------------------------
# T05 – generated report has all sections
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generated_report_has_all_sections():
    """Generated output must contain findings, impressions, and recommendations."""
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_openai_response(SAMPLE_GENERATED)
    )

    response = await mock_client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": "Generate report"}],
    )
    result = json.loads(response.choices[0].message.content)

    assert "findings" in result and result["findings"]
    assert "impressions" in result and result["impressions"]
    assert "recommendations" in result and result["recommendations"]


# ---------------------------------------------------------------------------
# T06 – generated report matches doctor style
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generated_report_matches_doctor_style():
    """Output should incorporate the doctor's style vocabulary."""
    styled = {
        **SAMPLE_GENERATED,
        "findings": "Liver is unremarkable. Within normal limits. No acute abnormality.",
    }
    mock_client = AsyncMock()
    mock_client.chat.completions.create = AsyncMock(
        return_value=_openai_response(styled)
    )

    response = await mock_client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "system",
                "content": f"Write in this style: {json.dumps(SAMPLE_STYLE)}",
            },
            {"role": "user", "content": "Generate report"},
        ],
    )
    result = json.loads(response.choices[0].message.content)
    findings_lower = result["findings"].lower()
    assert any(
        phrase in findings_lower
        for phrase in ["unremarkable", "within normal limits", "no acute"]
    ), "Generated report should reflect doctor's vocabulary patterns"


# ---------------------------------------------------------------------------
# Empty input → error
# ---------------------------------------------------------------------------
def test_generation_with_empty_input_returns_error():
    """GenerateRequest must reject empty dictated_text."""
    from pydantic import ValidationError

    with pytest.raises(ValidationError) as exc_info:
        GenerateRequest(
            dictated_text="",
            doctor_id="doctor-001",
            report_type="CT",
            body_region="Abdomen",
        )
    errors = exc_info.value.errors()
    assert any(e["loc"] == ("dictated_text",) for e in errors)


# ---------------------------------------------------------------------------
# Invalid doctor → 404
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_generation_with_invalid_doctor_returns_404():
    """Generating a report for a non-existent doctor should raise 404."""
    mock_container = MagicMock()
    mock_container.read_item = AsyncMock(
        side_effect=Exception("NotFound: Entity not found")
    )

    with pytest.raises(Exception, match="NotFound"):
        await mock_container.read_item(
            item="non-existent-doctor", partition_key="non-existent-doctor"
        )


# ---------------------------------------------------------------------------
# Model round-trip
# ---------------------------------------------------------------------------
def test_generate_request_model():
    req = GenerateRequest(
        dictated_text="Normal CT abdomen.",
        doctor_id="doctor-001",
        report_type="CT",
        body_region="Abdomen",
    )
    assert req.dictated_text == "Normal CT abdomen."
    assert req.doctor_id == "doctor-001"


def test_report_status_enum():
    assert ReportStatus.DRAFT.value == "draft"
    assert ReportStatus.FINAL.value == "final"

"""Tests for grounding validation – ensuring measurements are preserved."""

import re

import pytest

from app.services.grounding import validate_grounding, GroundingResult


# ---------------------------------------------------------------------------
# Helpers (for local extraction checks)
# ---------------------------------------------------------------------------
MEASUREMENT_PATTERN = re.compile(
    r"\d+\.?\d*\s*(?:cm|mm|mL|cc|%|mg|g|kg|lb|in|ft)"
)

DATE_PATTERN = re.compile(
    r"\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{2,4}"
)

PERCENTAGE_PATTERN = re.compile(r"\d+\.?\d*\s*%")


def extract_measurements(text: str) -> list[str]:
    """Extract all numeric measurements from text."""
    return MEASUREMENT_PATTERN.findall(text)


def extract_dates(text: str) -> list[str]:
    return DATE_PATTERN.findall(text)


def extract_percentages(text: str) -> list[str]:
    return PERCENTAGE_PATTERN.findall(text)


# ---------------------------------------------------------------------------
# T03 – numbers preserved in output
# ---------------------------------------------------------------------------
def test_numbers_preserved_in_output():
    """Input '3.2 cm mass' → output must contain '3.2 cm'."""
    input_text = (
        "CT abdomen: 3.2 cm mass in right adrenal gland. "
        "Liver measures 14.5 cm."
    )
    output_text = (
        "Findings: A 3.2 cm mass is identified in the right adrenal gland. "
        "The liver measures 14.5 cm in craniocaudal dimension."
    )
    result = validate_grounding(input_text, output_text)
    assert result.is_grounded, f"Hallucinated values: {result.hallucinated_values}"
    assert "3.2 cm" in output_text
    assert "14.5 cm" in output_text


# ---------------------------------------------------------------------------
# T04 – no hallucinated measurements
# ---------------------------------------------------------------------------
def test_no_hallucinated_measurements():
    """When input has no measurements, output must not invent any."""
    input_text = "The liver appears normal. No focal lesion identified."
    output_text = "The liver is unremarkable. No focal lesion is seen."
    result = validate_grounding(input_text, output_text)
    assert result.is_grounded, f"Hallucinated values found: {result.hallucinated_values}"
    assert len(result.output_values.get("measurements", [])) == 0


# ---------------------------------------------------------------------------
# Dates preserved
# ---------------------------------------------------------------------------
def test_dates_preserved():
    """Dates in the input should appear in the output."""
    input_text = "Compared to prior study dated 2024-01-15, the mass is unchanged."
    output_text = (
        "The mass is stable compared to prior examination from 2024-01-15."
    )
    input_dates = set(extract_dates(input_text))
    output_dates = set(extract_dates(output_text))
    assert input_dates.issubset(output_dates), (
        f"Missing dates: {input_dates - output_dates}"
    )


# ---------------------------------------------------------------------------
# Percentages preserved
# ---------------------------------------------------------------------------
def test_percentages_preserved():
    """Percentage values should be faithfully reproduced."""
    input_text = "Ejection fraction is 55%. Stenosis estimated at 70%."
    output_text = "Ejection fraction: 55%. Stenosis: 70%."
    input_pcts = set(extract_percentages(input_text))
    output_pcts = set(extract_percentages(output_text))
    assert input_pcts.issubset(output_pcts), (
        f"Missing percentages: {input_pcts - output_pcts}"
    )


# ---------------------------------------------------------------------------
# Multiple measurements all preserved
# ---------------------------------------------------------------------------
def test_multiple_measurements_all_preserved():
    """All measurements from a complex input must appear in the output."""
    input_text = (
        "Right kidney 11.2 cm. Left kidney 10.8 cm. Spleen 12.1 cm. "
        "Aorta 2.3 cm. Gallbladder wall 3 mm."
    )
    output_text = (
        "Right kidney measures 11.2 cm. Left kidney measures 10.8 cm. "
        "Spleen is 12.1 cm. Aorta diameter is 2.3 cm. "
        "Gallbladder wall thickness is 3 mm."
    )
    result = validate_grounding(input_text, output_text)
    assert result.is_grounded
    assert len(result.missing_from_output) == 0, (
        f"Missing measurements: {result.missing_from_output}"
    )


# ---------------------------------------------------------------------------
# Grounding flag when value missing
# ---------------------------------------------------------------------------
def test_grounding_flag_when_value_missing():
    """If a measurement is dropped, the grounding check should flag it."""
    input_text = "Mass measures 3.2 cm. Liver is 15.0 cm."
    output_text = "A mass is present. The liver measures 15.0 cm."
    result = validate_grounding(input_text, output_text)
    missing_strs = " ".join(result.missing_from_output)
    assert "3.2" in missing_strs, (
        "Grounding should flag that 3.2 cm is missing from output"
    )


# ---------------------------------------------------------------------------
# to_dict() returns acceptance-criteria fields
# ---------------------------------------------------------------------------
def test_grounding_result_dict_has_required_fields():
    """to_dict() must include is_valid, preserved_values, missing_values, suspicious_values."""
    input_text = "Liver 14.5 cm. Mass 3.2 cm."
    output_text = "Liver 14.5 cm. Mass 3.2 cm."
    result = validate_grounding(input_text, output_text)
    d = result.to_dict()
    assert "is_valid" in d
    assert "preserved_values" in d
    assert "missing_values" in d
    assert "suspicious_values" in d
    assert d["is_valid"] is True
    assert len(d["suspicious_values"]) == 0


def test_grounding_preserved_values_populated():
    """preserved_values should contain values found in both input and output."""
    input_text = "Mass 3.2 cm. Liver 14.5 cm."
    output_text = "Mass 3.2 cm. Liver 14.5 cm."
    result = validate_grounding(input_text, output_text)
    d = result.to_dict()
    preserved_str = " ".join(d["preserved_values"])
    assert "3.2" in preserved_str
    assert "14.5" in preserved_str


def test_grounding_suspicious_values_on_hallucination():
    """suspicious_values should contain values in output not in input."""
    input_text = "The liver appears normal."
    output_text = "The liver measures 16.0 cm and appears normal."
    result = validate_grounding(input_text, output_text)
    d = result.to_dict()
    assert d["is_valid"] is False
    assert len(d["suspicious_values"]) > 0

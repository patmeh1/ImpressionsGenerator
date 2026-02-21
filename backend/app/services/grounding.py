"""Grounding validation service for clinical report accuracy."""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# Patterns for extracting clinical values from text
_PATTERNS = {
    "measurements": re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:mm|cm|m|in|inches|feet|ft)\b", re.IGNORECASE
    ),
    "percentages": re.compile(r"\b(\d+(?:\.\d+)?)\s*%", re.IGNORECASE),
    "dates": re.compile(
        r"\b(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b"
        r"|\b(\d{4}-\d{2}-\d{2})\b"
        r"|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s*\d{2,4}\b",
        re.IGNORECASE,
    ),
    "numbers": re.compile(r"\b(\d+(?:\.\d+)?)\b"),
    "units_with_values": re.compile(
        r"\b(\d+(?:\.\d+)?)\s*(?:mg|g|kg|mL|L|cc|mmHg|bpm|Gy|cGy|mCi|SUV|HU)\b",
        re.IGNORECASE,
    ),
}


@dataclass
class GroundingResult:
    """Result of grounding validation."""

    is_grounded: bool = True
    input_values: dict[str, list[str]] = field(default_factory=dict)
    output_values: dict[str, list[str]] = field(default_factory=dict)
    missing_from_output: list[str] = field(default_factory=list)
    hallucinated_values: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_grounded": self.is_grounded,
            "input_values": self.input_values,
            "output_values": self.output_values,
            "missing_from_output": self.missing_from_output,
            "hallucinated_values": self.hallucinated_values,
            "warnings": self.warnings,
        }


def _extract_values(text: str) -> dict[str, set[str]]:
    """Extract all measurable values from text by category."""
    extracted: dict[str, set[str]] = {}
    for category, pattern in _PATTERNS.items():
        matches = pattern.findall(text)
        values: set[str] = set()
        for match in matches:
            if isinstance(match, tuple):
                values.update(m for m in match if m)
            else:
                values.add(match)
        if values:
            extracted[category] = values
    return extracted


def _get_all_numbers(text: str) -> set[str]:
    """Extract all numeric values from text."""
    return set(_PATTERNS["numbers"].findall(text))


def validate_grounding(input_text: str, output_text: str) -> GroundingResult:
    """
    Validate that generated output is grounded in the input text.

    Checks that:
    1. All numbers/measurements from the output exist in the input
    2. No fabricated values appear in the output

    Returns a GroundingResult with detailed findings.
    """
    result = GroundingResult()

    input_values = _extract_values(input_text)
    output_values = _extract_values(output_text)

    result.input_values = {k: sorted(v) for k, v in input_values.items()}
    result.output_values = {k: sorted(v) for k, v in output_values.items()}

    input_numbers = _get_all_numbers(input_text)
    output_numbers = _get_all_numbers(output_text)

    # Check for values in output not found in input (potential hallucinations)
    for category in ["measurements", "units_with_values", "percentages"]:
        output_vals = output_values.get(category, set())
        input_vals = input_values.get(category, set())
        fabricated = output_vals - input_vals
        for val in fabricated:
            # Also check if the numeric part appears anywhere in input
            if val not in input_numbers:
                result.hallucinated_values.append(f"{category}: {val}")

    # Check numeric values in output against input
    novel_numbers = output_numbers - input_numbers
    # Filter out trivially common numbers (0, 1, 2, etc.)
    trivial = {"0", "1", "2", "3", "4", "5"}
    significant_novel = novel_numbers - trivial
    if significant_novel:
        for num in sorted(significant_novel):
            result.hallucinated_values.append(f"number: {num}")

    # Check for input measurements missing from output (warnings only)
    for category in ["measurements", "units_with_values"]:
        input_vals = input_values.get(category, set())
        output_vals = output_values.get(category, set())
        missing = input_vals - output_vals
        for val in missing:
            result.missing_from_output.append(f"{category}: {val}")

    # Determine overall grounding status
    if result.hallucinated_values:
        result.is_grounded = False
        result.warnings.append(
            f"Found {len(result.hallucinated_values)} potentially hallucinated value(s) "
            "in the generated output that were not present in the input."
        )

    if result.missing_from_output:
        result.warnings.append(
            f"{len(result.missing_from_output)} input value(s) not found in the output. "
            "These may have been omitted by the model."
        )

    logger.info(
        "Grounding check: grounded=%s, hallucinated=%d, missing=%d",
        result.is_grounded,
        len(result.hallucinated_values),
        len(result.missing_from_output),
    )

    return result

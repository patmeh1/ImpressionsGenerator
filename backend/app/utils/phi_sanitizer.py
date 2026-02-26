"""PHI sanitization utilities for HIPAA-compliant logging.

Provides a logging filter that scrubs Protected Health Information (PHI)
patterns from log messages before they are emitted.
"""

import logging
import re

# Patterns that may indicate PHI in log messages
_PHI_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    # SSN: 123-45-6789
    (re.compile(r"\b\d{3}-\d{2}-\d{4}\b"), "[REDACTED-SSN]"),
    # MRN / Medical Record Number (common 6-10 digit formats)
    (re.compile(r"\bMRN[:\s#]*\d{4,10}\b", re.IGNORECASE), "[REDACTED-MRN]"),
    # Phone numbers: (123) 456-7890, 123-456-7890, 123.456.7890
    (re.compile(r"\(?\d{3}\)?[-.\s]\d{3}[-.\s]\d{4}\b"), "[REDACTED-PHONE]"),
    # Email addresses
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"), "[REDACTED-EMAIL]"),
    # Date of birth patterns: DOB: MM/DD/YYYY
    (re.compile(r"\bDOB[:\s]*\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", re.IGNORECASE), "[REDACTED-DOB]"),
    # Patient name patterns: "Patient: Name" or "patient name:"
    (re.compile(r"\bPatient\s*(?:name)?[:\s]+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+", re.IGNORECASE), "[REDACTED-PATIENT]"),
]


class PHISanitizingFilter(logging.Filter):
    """Logging filter that redacts PHI patterns from log messages."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = sanitize_phi(record.msg)
        if record.args:
            if isinstance(record.args, dict):
                record.args = {
                    k: sanitize_phi(v) if isinstance(v, str) else v
                    for k, v in record.args.items()
                }
            elif isinstance(record.args, tuple):
                record.args = tuple(
                    sanitize_phi(a) if isinstance(a, str) else a
                    for a in record.args
                )
        return True


def sanitize_phi(text: str) -> str:
    """Remove PHI patterns from a text string."""
    for pattern, replacement in _PHI_PATTERNS:
        text = pattern.sub(replacement, text)
    return text

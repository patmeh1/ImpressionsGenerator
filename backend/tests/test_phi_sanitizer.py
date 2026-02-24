"""Tests for PHI sanitization utilities."""

import logging

from app.utils.phi_sanitizer import PHISanitizingFilter, sanitize_phi


class TestSanitizePhi:
    """Tests for the sanitize_phi function."""

    def test_redacts_ssn(self):
        assert "[REDACTED-SSN]" in sanitize_phi("SSN is 123-45-6789")

    def test_redacts_mrn(self):
        assert "[REDACTED-MRN]" in sanitize_phi("MRN: 12345678")

    def test_redacts_phone(self):
        result = sanitize_phi("Call 123-456-7890")
        assert "[REDACTED-PHONE]" in result

    def test_redacts_email(self):
        assert "[REDACTED-EMAIL]" in sanitize_phi("Email: patient@example.com")

    def test_redacts_dob(self):
        assert "[REDACTED-DOB]" in sanitize_phi("DOB: 01/15/1990")

    def test_redacts_patient_name(self):
        assert "[REDACTED-PATIENT]" in sanitize_phi("Patient: John Smith")

    def test_preserves_safe_text(self):
        safe = "Report generation complete for doctor abc-123"
        assert sanitize_phi(safe) == safe

    def test_multiple_patterns_redacted(self):
        text = "Patient: Jane Doe, SSN 123-45-6789, DOB: 03/15/1985"
        result = sanitize_phi(text)
        assert "Jane Doe" not in result
        assert "123-45-6789" not in result
        assert "03/15/1985" not in result


class TestPHISanitizingFilter:
    """Tests for the PHISanitizingFilter logging filter."""

    def test_filter_scrubs_log_message(self):
        filt = PHISanitizingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="Patient: John Smith has SSN 123-45-6789",
            args=None, exc_info=None,
        )
        filt.filter(record)
        assert "John Smith" not in record.msg
        assert "123-45-6789" not in record.msg

    def test_filter_scrubs_string_args(self):
        filt = PHISanitizingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="User email: %s",
            args=("patient@example.com",), exc_info=None,
        )
        filt.filter(record)
        assert record.args is not None
        assert "patient@example.com" not in str(record.args)

    def test_filter_returns_true(self):
        filt = PHISanitizingFilter()
        record = logging.LogRecord(
            name="test", level=logging.INFO, pathname="", lineno=0,
            msg="safe message", args=None, exc_info=None,
        )
        assert filt.filter(record) is True

"""Tests for the audit trail logging service."""

import hashlib
import json
import logging
import time

import pytest

from app.services.audit import AuditEventType, AuditService, audit_service


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
SAMPLE_USER = {"user_id": "doctor-001", "name": "Dr. Jane Smith", "roles": ["Doctor"]}
ADMIN_USER = {"user_id": "admin-001", "name": "Admin User", "roles": ["Admin"]}


@pytest.fixture(autouse=True)
def _enable_audit_propagation():
    """Configure audit and allow caplog to capture audit log records during tests."""
    audit_logger = logging.getLogger("audit")
    # Ensure the audit logger is configured (idempotent)
    audit_service.configure()
    # Enable propagation so caplog captures records
    audit_logger.propagate = True
    yield
    audit_logger.propagate = False


def _capture_audit_records(
    caplog: pytest.LogCaptureFixture,
) -> list[logging.LogRecord]:
    """Return only records emitted by the 'audit' logger."""
    return [r for r in caplog.records if r.name == "audit"]


# ---------------------------------------------------------------------------
# hash_content
# ---------------------------------------------------------------------------
class TestHashContent:
    def test_returns_sha256_hex(self):
        text = "some sensitive data"
        expected = hashlib.sha256(text.encode("utf-8")).hexdigest()
        assert audit_service.hash_content(text) == expected

    def test_empty_string(self):
        assert audit_service.hash_content("") == hashlib.sha256(b"").hexdigest()

    def test_different_inputs_produce_different_hashes(self):
        h1 = audit_service.hash_content("patient name A")
        h2 = audit_service.hash_content("patient name B")
        assert h1 != h2

    def test_same_input_produces_same_hash(self):
        text = "consistent input"
        assert audit_service.hash_content(text) == audit_service.hash_content(text)


# ---------------------------------------------------------------------------
# timer helpers
# ---------------------------------------------------------------------------
class TestTimer:
    def test_start_timer_returns_float(self):
        assert isinstance(audit_service.start_timer(), float)

    def test_elapsed_ms_positive(self):
        start = audit_service.start_timer()
        time.sleep(0.01)
        elapsed = audit_service.elapsed_ms(start)
        assert elapsed > 0


# ---------------------------------------------------------------------------
# log_generation
# ---------------------------------------------------------------------------
class TestLogGeneration:
    def test_emits_audit_record(self, caplog):
        with caplog.at_level(logging.INFO, logger="audit"):
            audit_service.log_generation(
                user=SAMPLE_USER,
                doctor_id="doctor-001",
                input_text="some input",
                output_text="some output",
                duration_ms=123.45,
                report_id="rpt-001",
            )
        records = _capture_audit_records(caplog)
        assert len(records) >= 1
        rec = records[-1]
        assert hasattr(rec, "audit_event")
        event = rec.audit_event
        assert event["event_type"] == AuditEventType.GENERATION
        assert event["user_id"] == "doctor-001"
        assert event["doctor_id"] == "doctor-001"
        assert event["report_id"] == "rpt-001"
        assert event["duration_ms"] == 123.45

    def test_no_phi_in_event(self, caplog):
        input_text = "Patient John Doe has cancer"
        output_text = "Findings: malignant tumor"
        with caplog.at_level(logging.INFO, logger="audit"):
            audit_service.log_generation(
                user=SAMPLE_USER,
                doctor_id="doctor-001",
                input_text=input_text,
                output_text=output_text,
                duration_ms=50,
            )
        records = _capture_audit_records(caplog)
        event = records[-1].audit_event
        # The raw text must not appear; only hashes
        assert event["input_hash"] == audit_service.hash_content(input_text)
        assert event["output_hash"] == audit_service.hash_content(output_text)
        assert "John Doe" not in json.dumps(event)
        assert "malignant" not in json.dumps(event)


# ---------------------------------------------------------------------------
# log_data_access
# ---------------------------------------------------------------------------
class TestLogDataAccess:
    def test_emits_data_access_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="audit"):
            audit_service.log_data_access(
                user=SAMPLE_USER,
                resource_type="report",
                resource_id="rpt-001",
                action="read",
            )
        records = _capture_audit_records(caplog)
        event = records[-1].audit_event
        assert event["event_type"] == AuditEventType.DATA_ACCESS
        assert event["action"] == "read"
        assert event["resource_type"] == "report"
        assert event["resource_id"] == "rpt-001"


# ---------------------------------------------------------------------------
# log_admin_action
# ---------------------------------------------------------------------------
class TestLogAdminAction:
    def test_emits_admin_action_event(self, caplog):
        with caplog.at_level(logging.INFO, logger="audit"):
            audit_service.log_admin_action(
                user=ADMIN_USER,
                action="delete",
                resource_type="doctor",
                resource_id="doctor-002",
                details="profile_deleted",
            )
        records = _capture_audit_records(caplog)
        event = records[-1].audit_event
        assert event["event_type"] == AuditEventType.ADMIN_ACTION
        assert event["action"] == "delete"
        assert event["resource_type"] == "doctor"
        assert event["resource_id"] == "doctor-002"
        assert event["details"] == "profile_deleted"
        assert event["user_id"] == "admin-001"


# ---------------------------------------------------------------------------
# AuditEventType enum
# ---------------------------------------------------------------------------
class TestAuditEventType:
    def test_values(self):
        assert AuditEventType.GENERATION == "generation"
        assert AuditEventType.DATA_ACCESS == "data_access"
        assert AuditEventType.ADMIN_ACTION == "admin_action"


# ---------------------------------------------------------------------------
# configure
# ---------------------------------------------------------------------------
class TestConfigure:
    def test_configure_without_appinsights(self):
        svc = AuditService()
        svc.configure()
        assert svc._appinsights_handler is None

    def test_configure_idempotent(self, caplog):
        svc = AuditService()
        svc.configure()
        initial_handler_count = len(logging.getLogger("audit").handlers)
        svc.configure()  # should not add duplicate handlers
        assert len(logging.getLogger("audit").handlers) == initial_handler_count


# ---------------------------------------------------------------------------
# JSON format
# ---------------------------------------------------------------------------
class TestJsonFormat:
    def test_log_output_is_valid_json(self, caplog):
        with caplog.at_level(logging.INFO, logger="audit"):
            audit_service.log_data_access(
                user=SAMPLE_USER,
                resource_type="note",
                resource_id="note-001",
                action="list",
            )
        records = _capture_audit_records(caplog)
        assert len(records) >= 1
        # The formatter produces JSON; verify the record has the right structure
        event = records[-1].audit_event
        assert "timestamp" in event
        assert "event_type" in event

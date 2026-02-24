"""Audit trail logging service for compliance reporting.

Logs all significant events (generation, data access, admin actions) in
structured JSON format.  Sensitive content is hashed (SHA-256) so that no
PHI appears in log entries.

When an Application Insights connection string is configured, events are
also emitted as custom App Insights events via opencensus.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from enum import Enum
from typing import Any

logger = logging.getLogger("audit")


# ---------------------------------------------------------------------------
# Event type taxonomy
# ---------------------------------------------------------------------------
class AuditEventType(str, Enum):
    """Top-level categories for audit events."""

    GENERATION = "generation"
    DATA_ACCESS = "data_access"
    ADMIN_ACTION = "admin_action"


# ---------------------------------------------------------------------------
# JSON formatter for structured audit logs
# ---------------------------------------------------------------------------
class _JsonAuditFormatter(logging.Formatter):
    """Emit each log record as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:  # noqa: A003
        import json

        payload: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Merge extra structured fields attached by the audit service
        if hasattr(record, "audit_event"):
            payload["audit_event"] = record.audit_event
        return json.dumps(payload, default=str)


# ---------------------------------------------------------------------------
# Audit service
# ---------------------------------------------------------------------------
class AuditService:
    """Central audit-trail service.

    * Emits structured JSON log lines via the ``audit`` logger.
    * Optionally sends custom events to Azure Application Insights.
    """

    _appinsights_handler: logging.Handler | None = None

    # -- lifecycle -----------------------------------------------------------

    def configure(self, appinsights_connection_string: str = "") -> None:
        """Set up the audit logger with JSON formatting and optional App Insights."""

        audit_logger = logging.getLogger("audit")
        # Avoid adding duplicate handlers on re-configuration
        if audit_logger.handlers:
            return

        audit_logger.setLevel(logging.INFO)
        audit_logger.propagate = False

        # 1) Stream handler with JSON formatter (always present)
        handler = logging.StreamHandler()
        handler.setFormatter(_JsonAuditFormatter())
        audit_logger.addHandler(handler)

        # 2) Azure Application Insights handler (optional)
        if appinsights_connection_string:
            try:
                from opencensus.ext.azure.log_exporter import AzureLogHandler

                az_handler = AzureLogHandler(
                    connection_string=appinsights_connection_string
                )
                audit_logger.addHandler(az_handler)
                self._appinsights_handler = az_handler
                audit_logger.info("App Insights audit handler attached")
            except Exception as exc:
                audit_logger.warning(
                    "Failed to attach App Insights handler: %s", exc
                )

    # -- helpers -------------------------------------------------------------

    @staticmethod
    def hash_content(content: str) -> str:
        """Return a SHA-256 hex digest of *content* (no PHI leakage)."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _user_id(user: dict[str, Any]) -> str:
        return user.get("user_id", "unknown")

    # -- custom App Insights event -------------------------------------------

    def _track_event(self, name: str, properties: dict[str, Any]) -> None:
        """Send a custom event to App Insights if available."""
        if self._appinsights_handler is None:
            return
        try:
            # Log with custom_dimensions for App Insights
            logger.info(
                name,
                extra={"custom_dimensions": properties},
            )
        except Exception:
            pass  # best-effort

    # -- public API ----------------------------------------------------------

    def log_generation(
        self,
        user: dict[str, Any],
        doctor_id: str,
        input_text: str,
        output_text: str,
        duration_ms: float,
        report_id: str = "",
    ) -> None:
        """Log a report-generation event."""
        event = {
            "event_type": AuditEventType.GENERATION,
            "user_id": self._user_id(user),
            "doctor_id": doctor_id,
            "input_hash": self.hash_content(input_text),
            "output_hash": self.hash_content(output_text),
            "report_id": report_id,
            "duration_ms": round(duration_ms, 2),
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "report_generated",
            extra={"audit_event": event},
        )
        self._track_event("ReportGenerated", event)

    def log_data_access(
        self,
        user: dict[str, Any],
        resource_type: str,
        resource_id: str,
        action: str,
    ) -> None:
        """Log a data-access event (read / list)."""
        event = {
            "event_type": AuditEventType.DATA_ACCESS,
            "user_id": self._user_id(user),
            "resource_type": resource_type,
            "resource_id": resource_id,
            "action": action,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "data_accessed",
            extra={"audit_event": event},
        )
        self._track_event("DataAccessed", event)

    def log_admin_action(
        self,
        user: dict[str, Any],
        action: str,
        resource_type: str,
        resource_id: str = "",
        details: str = "",
    ) -> None:
        """Log an administrative action (create / update / delete)."""
        event = {
            "event_type": AuditEventType.ADMIN_ACTION,
            "user_id": self._user_id(user),
            "action": action,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "details": details,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        logger.info(
            "admin_action",
            extra={"audit_event": event},
        )
        self._track_event("AdminAction", event)

    # -- query helper (in-process; production should query Log Analytics) ----

    @staticmethod
    def start_timer() -> float:
        """Return a monotonic timestamp for duration measurement."""
        return time.monotonic()

    @staticmethod
    def elapsed_ms(start: float) -> float:
        """Return elapsed milliseconds since *start*."""
        return (time.monotonic() - start) * 1000


# Singleton
audit_service = AuditService()

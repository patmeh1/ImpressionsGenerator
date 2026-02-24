"""Azure Monitor / Application Insights telemetry service.

Provides custom metrics, distributed tracing, and request tracking
for the Impressions Generator backend.
"""

import logging
import time
from typing import Any

from opentelemetry import trace

from app.config import settings

logger = logging.getLogger(__name__)

tracer = trace.get_tracer("impressions_generator")


class MonitoringService:
    """Manages Application Insights telemetry, custom metrics, and tracing."""

    def __init__(self) -> None:
        self._initialized = False

    def initialize(self) -> None:
        """Configure Azure Monitor OpenTelemetry if a connection string is set."""
        conn_str = settings.APPINSIGHTS_CONNECTION_STRING
        if not conn_str:
            logger.info(
                "APPINSIGHTS_CONNECTION_STRING not set – telemetry disabled"
            )
            return

        try:
            from azure.monitor.opentelemetry import configure_azure_monitor

            configure_azure_monitor(connection_string=conn_str)
            self._initialized = True
            logger.info("Azure Monitor OpenTelemetry configured")
        except Exception as e:
            logger.warning("Failed to configure Azure Monitor: %s", e)

    @property
    def is_enabled(self) -> bool:
        return self._initialized

    # ------------------------------------------------------------------
    # Custom metric helpers
    # ------------------------------------------------------------------
    def track_generation(
        self,
        doctor_id: str,
        duration_ms: float,
        token_usage: dict[str, int] | None = None,
    ) -> None:
        """Record a report-generation event with custom attributes."""
        span = trace.get_current_span()
        span.set_attribute("generation.doctor_id", doctor_id)
        span.set_attribute("generation.duration_ms", duration_ms)
        if token_usage:
            span.set_attribute(
                "generation.prompt_tokens",
                token_usage.get("prompt_tokens", 0),
            )
            span.set_attribute(
                "generation.completion_tokens",
                token_usage.get("completion_tokens", 0),
            )
            span.set_attribute(
                "generation.total_tokens",
                token_usage.get("total_tokens", 0),
            )
        logger.info(
            "Generation metric: doctor=%s duration=%.1fms tokens=%s",
            doctor_id,
            duration_ms,
            token_usage,
        )

    def track_token_usage(self, usage: dict[str, int]) -> None:
        """Record OpenAI token-usage counters on the current span."""
        span = trace.get_current_span()
        for key in ("prompt_tokens", "completion_tokens", "total_tokens"):
            span.set_attribute(f"openai.{key}", usage.get(key, 0))

    # ------------------------------------------------------------------
    # Span helpers (for distributed tracing)
    # ------------------------------------------------------------------
    @staticmethod
    def start_span(name: str, attributes: dict[str, Any] | None = None):
        """Create and return a new OpenTelemetry span."""
        return tracer.start_as_current_span(name, attributes=attributes or {})

    @staticmethod
    def current_time_ms() -> float:
        return time.time() * 1000


# Singleton
monitoring_service = MonitoringService()

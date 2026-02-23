"""Tests for the monitoring / telemetry service."""

from unittest.mock import MagicMock, patch

from app.services.monitoring import MonitoringService


class TestMonitoringService:
    """Unit tests for MonitoringService."""

    def test_initialize_without_connection_string(self):
        """Should remain disabled when APPINSIGHTS_CONNECTION_STRING is empty."""
        svc = MonitoringService()
        with patch("app.services.monitoring.settings") as mock_settings:
            mock_settings.APPINSIGHTS_CONNECTION_STRING = ""
            svc.initialize()
        assert svc.is_enabled is False

    def test_initialize_with_connection_string(self):
        """Should enable telemetry when connection string is provided."""
        svc = MonitoringService()
        with (
            patch("app.services.monitoring.settings") as mock_settings,
            patch(
                "app.services.monitoring.configure_azure_monitor",
                create=True,
            ) as mock_configure,
        ):
            mock_settings.APPINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test"
            # Patch the import inside the method
            with patch.dict(
                "sys.modules",
                {"azure.monitor.opentelemetry": MagicMock(configure_azure_monitor=mock_configure)},
            ):
                svc.initialize()
            assert svc.is_enabled is True

    def test_initialize_handles_import_error(self):
        """Should log a warning and stay disabled on import failure."""
        svc = MonitoringService()
        with patch("app.services.monitoring.settings") as mock_settings:
            mock_settings.APPINSIGHTS_CONNECTION_STRING = "InstrumentationKey=test"
            # Force the import to raise
            with patch.dict("sys.modules", {"azure.monitor.opentelemetry": None}):
                svc.initialize()
        assert svc.is_enabled is False

    def test_track_generation_sets_attributes(self):
        """track_generation should annotate the current span."""
        svc = MonitoringService()
        mock_span = MagicMock()
        with patch("app.services.monitoring.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            svc.track_generation(
                doctor_id="doc-1",
                duration_ms=1234.5,
                token_usage={"prompt_tokens": 100, "completion_tokens": 50, "total_tokens": 150},
            )
        mock_span.set_attribute.assert_any_call("generation.doctor_id", "doc-1")
        mock_span.set_attribute.assert_any_call("generation.duration_ms", 1234.5)
        mock_span.set_attribute.assert_any_call("generation.total_tokens", 150)

    def test_track_generation_without_token_usage(self):
        """track_generation should work when token_usage is None."""
        svc = MonitoringService()
        mock_span = MagicMock()
        with patch("app.services.monitoring.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            svc.track_generation(doctor_id="doc-2", duration_ms=500.0, token_usage=None)
        mock_span.set_attribute.assert_any_call("generation.doctor_id", "doc-2")
        # Should NOT have set token attributes
        token_calls = [c for c in mock_span.set_attribute.call_args_list if "total_tokens" in str(c)]
        assert len(token_calls) == 0

    def test_track_token_usage(self):
        """track_token_usage should annotate the current span with openai.* attributes."""
        svc = MonitoringService()
        mock_span = MagicMock()
        with patch("app.services.monitoring.trace") as mock_trace:
            mock_trace.get_current_span.return_value = mock_span
            svc.track_token_usage({"prompt_tokens": 200, "completion_tokens": 80, "total_tokens": 280})
        mock_span.set_attribute.assert_any_call("openai.total_tokens", 280)

    def test_current_time_ms(self):
        """current_time_ms should return a positive float in milliseconds."""
        val = MonitoringService.current_time_ms()
        assert isinstance(val, float)
        assert val > 0

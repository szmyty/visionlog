"""Unit tests for OpenTelemetry tracing integration."""
import sys
from unittest.mock import MagicMock, patch

from visionlog.visionlog import add_otel_context, get_logger


def _make_span_context(trace_id: int, span_id: int, sampled: bool = True):
    """Helper that builds a real OTel SpanContext."""
    from opentelemetry.trace import SpanContext, TraceFlags

    return SpanContext(
        trace_id=trace_id,
        span_id=span_id,
        is_remote=False,
        trace_flags=TraceFlags(0x01 if sampled else 0x00),
    )


def test_add_otel_context_with_valid_span():
    """Injects trace_id and span_id when an active, valid span exists."""
    trace_id = 0xDEADBEEFDEADBEEFDEADBEEFDEADBEEF
    span_id = 0xDEADBEEFDEADBEEF
    ctx = _make_span_context(trace_id, span_id)

    mock_span = MagicMock()
    mock_span.get_span_context.return_value = ctx

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        event_dict = {"event": "test"}
        result = add_otel_context(None, "info", event_dict)

    assert result["trace_id"] == format(trace_id, "032x")
    assert result["span_id"] == format(span_id, "016x")


def test_add_otel_context_with_invalid_span():
    """Does not inject trace context when there is no active span."""
    from opentelemetry.trace import INVALID_SPAN_CONTEXT

    mock_span = MagicMock()
    mock_span.get_span_context.return_value = INVALID_SPAN_CONTEXT

    with patch("opentelemetry.trace.get_current_span", return_value=mock_span):
        event_dict = {"event": "test"}
        result = add_otel_context(None, "info", event_dict)

    assert "trace_id" not in result
    assert "span_id" not in result


def test_add_otel_context_import_error(monkeypatch):
    """Gracefully skips tracing when opentelemetry is not installed."""
    monkeypatch.setitem(sys.modules, "opentelemetry", None)
    monkeypatch.setitem(sys.modules, "opentelemetry.trace", None)

    event_dict = {"event": "test"}
    result = add_otel_context(None, "info", event_dict)

    assert "trace_id" not in result
    assert "span_id" not in result


def test_get_logger_otel_context_always_in_processor_chain():
    """add_otel_context is always part of the processor chain at module load time."""
    import structlog as _structlog

    processors = _structlog.get_config()["processors"]
    assert add_otel_context in processors


def test_get_logger_enable_tracing_param_accepted():
    """enable_tracing parameter is accepted for backward compatibility and has no effect on the processor chain."""
    import structlog as _structlog

    processors_before = _structlog.get_config()["processors"]

    get_logger(enable_tracing=True)
    assert _structlog.get_config()["processors"] is processors_before

    get_logger(enable_tracing=False)
    assert _structlog.get_config()["processors"] is processors_before

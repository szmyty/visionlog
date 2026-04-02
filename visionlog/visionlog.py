import threading
import structlog
import orjson
import uuid
from typing import Any, Dict, List, Optional, Protocol, Union, runtime_checkable

from visionlog.enrichers.network import get_public_ip, get_geo_info, NetworkEnricher  # noqa: F401
from visionlog.enrichers.device import get_device_info, DeviceEnricher  # noqa: F401


@runtime_checkable
class Enricher(Protocol):
    """Protocol for pluggable log enrichers.

    Implement this protocol to create a custom enricher that can be passed to
    :func:`get_logger` via the ``enrichers`` parameter.  Each enricher receives
    the current :class:`structlog.stdlib.BoundLogger`, may bind additional
    fields to it, and must return the (possibly modified) logger.

    Example::

        import structlog

        class RequestIDEnricher:
            def __init__(self, request_id: str) -> None:
                self.request_id = request_id

            def enrich(
                self, logger: structlog.stdlib.BoundLogger
            ) -> structlog.stdlib.BoundLogger:
                return logger.bind(request_id=self.request_id)
    """

    def enrich(
        self, logger: structlog.stdlib.BoundLogger
    ) -> structlog.stdlib.BoundLogger:
        """Enrich *logger* with additional context and return it."""
        ...

def serialize_json(record, *args, **kwargs) -> str:
    """Serialize logs using orjson for high-performance JSON output."""
    return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()

def add_common_fields(logger, method_name, event_dict) -> Dict[str, Any]:
    """Injects common metadata fields into every log."""
    event_dict.setdefault("log_id", str(uuid.uuid4()))
    event_dict.setdefault("logger_library", "visionlog")
    return event_dict

def add_otel_context(logger, method_name, event_dict):
    """Injects OpenTelemetry trace and span IDs into log records when a span is active.

    Gracefully does nothing if the ``opentelemetry`` package is not installed or
    if there is no currently active span.
    """
    try:
        from opentelemetry import trace  # noqa: PLC0415
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            event_dict["trace_id"] = format(ctx.trace_id, "032x")
            event_dict["span_id"] = format(ctx.span_id, "016x")
    except ImportError:
        pass
    return event_dict

_CONFIGURED = False
_CONFIGURE_LOCK = threading.Lock()


def configure_visionlog(renderer=None, extra_processors=None) -> None:
    """Configure structlog for visionlog.

    This function is idempotent: it only configures structlog once per process.
    Calling it multiple times has no effect after the first successful call.
    Thread-safe: concurrent callers are serialised via an internal lock.

    Args:
        renderer: Optional structlog processor to use as the final renderer.
            Defaults to :class:`structlog.processors.JSONRenderer` with the
            :func:`serialize_json` serializer.
        extra_processors: Optional list of additional structlog processors to
            insert before the renderer.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        with _CONFIGURE_LOCK:
            if not _CONFIGURED:
                if renderer is None:
                    renderer = structlog.processors.JSONRenderer(serializer=serialize_json)
                processors = [
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    add_common_fields,
                    add_otel_context,
                ]
                if extra_processors:
                    processors.extend(extra_processors)
                processors.append(renderer)
                structlog.configure(
                    processors=processors,
                    logger_factory=structlog.stdlib.LoggerFactory(),
                    wrapper_class=structlog.stdlib.BoundLogger,
                    cache_logger_on_first_use=True,
                )
                _CONFIGURED = True


def get_logger(
    service_name="visionlog",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Union[bool, str, None] = None,
    device_info: bool = False,
    user_agent: Optional[str] = None,
    geo_info: bool = False,
    enable_tracing: bool = False,
    privacy_mode: bool = True,
    disable_network: bool = False,
    enrichers: Optional[List[Enricher]] = None,
) -> structlog.stdlib.BoundLogger:
    """
    Creates a structured logger with optional default fields.

    .. warning::
        **PII / Privacy Notice**: This library can enrich log records with
        IP addresses, geo-location data (city, region, country, timezone, ISP),
        and device fingerprint information (OS, browser, device model).  All of
        these may constitute **Personally Identifiable Information (PII)** under
        regulations such as **GDPR**, **CCPA**, **LGPD**, and others.

        * ``privacy_mode`` is **enabled by default** (``True``) which prevents
          any PII-bearing enrichment from being collected or logged.
        * Set ``privacy_mode=False`` only when you have a lawful basis for
          collecting this data, have notified users, and have reviewed your
          compliance obligations.

    - `privacy_mode`: When ``True`` (default), disables all PII enrichment —
      IP lookup, geo-location lookup, and device detection are silently skipped
      regardless of ``ip_address``, ``geo_info``, and ``device_info``.
      Set to ``False`` to enable those features.
    - `disable_network`: When ``True``, all external HTTP calls (IP lookup and
      geo-location lookup) are skipped and fallback values are returned (``None``
      for IP, ``{}`` for geo info).  Useful in CI environments, air-gapped
      systems, or any restricted-network context.  Compatible with
      ``privacy_mode``; when both are ``True`` network calls are already
      prevented by ``privacy_mode``.
    - `user_id`: Tracks the user identity
    - `session_id`: Tracks user session
    - `ip_address`: Controls IP address logging:
        - ``None`` → do nothing (default)
        - ``True`` → auto-fetch the public IP via an external service
        - ``str`` → use the provided IP address string directly
    - `device_info`: If True, extracts detailed device data
    - `user_agent`: Custom user-agent string for parsing device details
    - `geo_info`: If True, fetches IP geo-location (city, country, ISP, timezone)
    - `enable_tracing`: Deprecated since version 0.2.0. OpenTelemetry context is
      now always injected automatically when a span is active; this parameter has
      no effect and will be removed in a future release.
    - `enrichers`: Optional list of :class:`Enricher` instances applied after
      all built-in enrichment.  Each enricher's :meth:`~Enricher.enrich` method
      is called in order, receiving and returning the
      :class:`structlog.stdlib.BoundLogger`.
    """

    configure_visionlog()

    logger = structlog.get_logger(service=service_name)

    # Attach user metadata if provided
    if user_id:
        logger = logger.bind(user_id=user_id)
    if session_id:
        logger = logger.bind(session_id=session_id)

    # PII enrichment is only performed when privacy_mode is disabled
    if not privacy_mode:
        # Handle IP address logging
        ip = None
        if ip_address is True:
            ip = None if disable_network else get_public_ip()
        elif isinstance(ip_address, str):
            ip = ip_address

        if ip:
            logger = logger.bind(ip_address=ip)

            if geo_info and not disable_network:
                logger = logger.bind(**get_geo_info(ip))

        # Handle device info
        if device_info:
            logger = DeviceEnricher(enabled=True, user_agent=user_agent).enrich(logger)

    # Apply pluggable enrichers
    if enrichers:
        for enricher in enrichers:
            logger = enricher.enrich(logger)

    return logger

if __name__ == "__main__":
    # Example usage
    logger = get_logger(
        user_id="user_42",
        session_id="sess_123",
        ip_address=True,
        device_info=True,
        user_agent="Mozilla/5.0",
        geo_info=True
    )

    logger.info("User accessed dashboard", action="view", endpoint="/dashboard")
    logger.warning("Invalid login attempt", action="login_failed")
    logger.error("API request failed", endpoint="/api/data", status_code=500)

    print("\n✅ Visionlog 0.1.1 is logging with detailed analytics tracking!")

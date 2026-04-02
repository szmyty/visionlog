import logging
import socket
import threading
import structlog
import orjson
import uuid
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, Protocol, Union, runtime_checkable

if TYPE_CHECKING:
    from visionlog.config import LoggerConfig

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


#: Type alias for a structlog processor callable.
#:
#: A processor is any callable that accepts ``(logger, method_name, event_dict)``
#: and returns a (possibly modified) ``event_dict``.
Processor = Callable[..., Any]

def serialize_json(record, *args, **kwargs) -> str:
    """Serialize logs using orjson for high-performance JSON output.

    Falls back to ``str(record)`` when orjson cannot serialize the record so
    that logging pipelines are never interrupted by serialization errors.
    """
    try:
        return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()
    except Exception:
        logging.getLogger(__name__).warning(
            "orjson serialization failed; falling back to str(record)"
        )
        return str(record)


def _build_renderer_from_name(name: str):
    """Return a structlog renderer for *name*.

    Supported names:

    * ``"json"`` – :class:`structlog.processors.JSONRenderer` backed by orjson
      (default).
    * ``"console"`` – :class:`structlog.dev.ConsoleRenderer` for human-readable
      output.
    * ``"logfmt"`` – :class:`structlog.processors.LogfmtRenderer` for
      `logfmt <https://brandur.org/logfmt>`_-style output.

    Unknown names fall back to the JSON renderer.
    """
    if name == "console":
        return structlog.dev.ConsoleRenderer()
    if name == "logfmt":
        return structlog.processors.LogfmtRenderer()
    # "json" or any unrecognised value → JSON (default)
    return structlog.processors.JSONRenderer(serializer=serialize_json)

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


def configure_visionlog(renderer=None, extra_processors=None, renderer_name: str = "json", id_generator: Optional[Callable[[], str]] = None) -> None:
    """Configure structlog for visionlog.

    This function is idempotent: it only configures structlog once per process.
    Calling it multiple times has no effect after the first successful call.
    Thread-safe: concurrent callers are serialised via an internal lock.

    Args:
        renderer: Optional structlog processor to use as the final renderer.
            When provided, takes precedence over *renderer_name*.
            Defaults to ``None`` (use *renderer_name* to select a built-in).
        extra_processors: Optional list of additional structlog processors to
            insert before the renderer.
        renderer_name: Name of the built-in renderer to use when *renderer* is
            ``None``.  Supported values are ``"json"`` (default),
            ``"console"``, and ``"logfmt"``.
        id_generator: Optional callable that returns a string ID for each log
            record.  When provided, it is called once per log entry to produce
            the ``log_id`` field.  When ``None`` (default) a UUID4 string is
            used.
    """
    global _CONFIGURED
    if not _CONFIGURED:
        with _CONFIGURE_LOCK:
            if not _CONFIGURED:
                if renderer is None:
                    renderer = _build_renderer_from_name(renderer_name)
                if id_generator is not None:
                    _gen = id_generator
                    def _custom_id_fields_processor(logger, method_name, event_dict) -> Dict[str, Any]:
                        event_dict.setdefault("log_id", _gen())
                        event_dict.setdefault("logger_library", "visionlog")
                        return event_dict
                    fields_processor = _custom_id_fields_processor
                else:
                    fields_processor = add_common_fields
                processors = [
                    structlog.processors.TimeStamper(fmt="iso"),
                    structlog.processors.add_log_level,
                    fields_processor,
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
    config: Optional["LoggerConfig"] = None,
    service_name: str = "visionlog",
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

    Accepts either a :class:`~visionlog.LoggerConfig` instance (via the
    ``config`` parameter) or individual keyword arguments.  When ``config``
    is provided its fields take precedence over any matching keyword
    arguments, enabling reusable, object-based configuration.

    For backward compatibility, passing a plain string as the first positional
    argument is still supported and is treated as ``service_name``::

        # New config-based usage
        from visionlog import get_logger, LoggerConfig
        logger = get_logger(config=LoggerConfig(service_name="my-app"))

        # Legacy positional / keyword usage (still supported)
        logger = get_logger("my-app")
        logger = get_logger(service_name="my-app")

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

    - `config`: Optional :class:`~visionlog.LoggerConfig` instance.  When
      provided, its fields override the corresponding keyword arguments.
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

    # Backward compat: allow get_logger("my-app") — treat positional string as
    # service_name and clear config so the kwargs path is used.
    if isinstance(config, str):
        if service_name != "visionlog":
            import warnings
            warnings.warn(
                "Both a positional string and 'service_name' were provided to "
                "get_logger(); the positional string takes precedence. "
                "Use get_logger(service_name=...) or get_logger(config=...) "
                "to avoid ambiguity.",
                stacklevel=2,
            )
        service_name = config
        config = None

    # When a LoggerConfig is provided, its fields take precedence.
    renderer = None
    renderer_name: str = "json"
    hostname: bool = False
    environment: Optional[str] = None
    extra_processors: Optional[List[Processor]] = None
    id_generator: Optional[Callable[[], str]] = None
    if config is not None:
        service_name = config.service_name
        user_id = config.user_id
        session_id = config.session_id
        privacy_mode = config.privacy_mode
        disable_network = config.disable_network
        enrichers = list(config.enrichers)
        renderer = config.renderer
        renderer_name = config.renderer_name
        hostname = config.hostname
        environment = config.environment
        extra_processors = config.extra_processors
        id_generator = config.id_generator

    configure_visionlog(renderer=renderer, renderer_name=renderer_name, extra_processors=extra_processors, id_generator=id_generator)

    logger = structlog.get_logger(service=service_name)

    if hostname:
        logger = logger.bind(hostname=socket.gethostname())

    if environment:
        logger = logger.bind(environment=environment)

    # Attach user metadata if provided
    if user_id:
        logger = logger.bind(user_id=user_id)
    if session_id:
        logger = logger.bind(session_id=session_id)

    # Normalise enrichers list and prepend legacy-param-derived enrichers for
    # backward compatibility.  All PII enrichment is delegated to enrichers.
    enrichers = enrichers or []
    if not privacy_mode:
        legacy_enrichers: List[Enricher] = []

        # IP address and geo-location enrichment
        if ip_address is True and not disable_network:
            legacy_enrichers.append(NetworkEnricher(ip=True, geo=geo_info))
        elif isinstance(ip_address, str):
            legacy_enrichers.append(
                NetworkEnricher(ip=ip_address, geo=geo_info and not disable_network)
            )

        # Device information enrichment
        if device_info:
            legacy_enrichers.append(DeviceEnricher(enabled=True, user_agent=user_agent))

        enrichers = legacy_enrichers + list(enrichers)

    # Apply enrichers sequentially
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

import sys
import warnings
import structlog
import loguru
import orjson
import uuid
import httpx
import platform
from typing import Any, Dict, Optional, Union

try:
    from device_detector import DeviceDetector
except ImportError:
    DeviceDetector = None

def serialize_json(record, *args, **kwargs) -> str:
    """Serialize logs using orjson for high-performance JSON output."""
    return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()

def get_public_ip() -> Optional[str]:
    """Fetches the user's public IP address.

    .. warning::
        **PII / Privacy Notice**: The public IP address is Personally Identifiable
        Information (PII) under regulations such as GDPR and CCPA.  Only call this
        function when you have a lawful basis for collecting it and the caller has
        set ``privacy_mode=False`` in :func:`get_logger`.
    """
    try:
        return httpx.get("https://api64.ipify.org?format=json", timeout=5.0).json()["ip"]
    except (httpx.RequestError, httpx.HTTPStatusError, KeyError, ValueError) as error:
        warnings.warn(f"Failed to fetch public IP: {error}")
        return None

def get_geo_info(ip: str) -> Dict[str, str]:
    """Fetches geo-location & ISP info for a given IP address.

    .. warning::
        **PII / Privacy Notice**: Geo-location data derived from an IP address
        (city, region, country, timezone, ISP) may constitute PII under GDPR,
        CCPA, and similar regulations.  Only call this function when you have a
        lawful basis for collecting it and the caller has set
        ``privacy_mode=False`` in :func:`get_logger`.
    """
    try:
        response = httpx.get(f"https://ipinfo.io/{ip}/json", timeout=5.0).json()
        return {
            "city": response.get("city", ""),
            "region": response.get("region", ""),
            "country": response.get("country", ""),
            "timezone": response.get("timezone", ""),
            "org": response.get("org", ""),  # ISP / Organization
        }
    except (httpx.RequestError, httpx.HTTPStatusError, KeyError, ValueError) as error:
        warnings.warn(f"Failed to fetch geo info for IP {ip}: {error}")
        return {}

def get_device_info(user_agent: Optional[str] = None) -> Dict[str, str]:
    """Extracts detailed device details from user-agent string.

    .. warning::
        **PII / Privacy Notice**: Device fingerprint data (OS, browser, device
        model, architecture) can be used to identify individual users and may
        constitute PII under GDPR, CCPA, and similar regulations.  Only call
        this function when you have a lawful basis for collecting it and the
        caller has set ``privacy_mode=False`` in :func:`get_logger`.
    """
    if user_agent is not None and DeviceDetector is None:
        raise ImportError(
            "Device detection requires the 'device-detector' package. "
            "Install it with: pip install visionlog[device]"
        )
    device = DeviceDetector(user_agent).parse() if user_agent and DeviceDetector else None

    return {
        "device_type": device.device_type() if device else platform.system(),
        "os": device.os_name() if device else platform.system(),
        "os_version": device.os_version() if device else platform.release(),
        "device_brand": device.device_brand() if device else "",
        "device_model": device.device_model() if device else "",
        "architecture": platform.architecture()[0],  # 32-bit / 64-bit
        "browser": device.client_name() if device else "",
        "browser_version": device.client_version() if device else "",
    }

def add_common_fields(logger, method_name, event_dict) -> Dict[str, Any]:
    """Injects common metadata fields into every log."""
    event_dict.setdefault("log_id", str(uuid.uuid4()))
    event_dict.setdefault("app_name", "visionlog")
    event_dict.setdefault("log_level", method_name.upper())
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
    - `user_id`: Tracks the user identity
    - `session_id`: Tracks user session
    - `ip_address`: Controls IP address logging:
        - ``None`` → do nothing (default)
        - ``True`` → auto-fetch the public IP via an external service
        - ``str`` → use the provided IP address string directly
    - `device_info`: If True, extracts detailed device data
    - `user_agent`: Custom user-agent string for parsing device details
    - `geo_info`: If True, fetches IP geo-location (city, country, ISP, timezone)
    - `enable_tracing`: If True, injects OpenTelemetry trace/span IDs into every log
      record when a span is active. Requires ``visionlog[tracing]`` to be installed.
    """

    loguru.logger.remove()
    loguru.logger.add(sys.stdout, format="{message}", serialize=False)

    processors = [
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        add_common_fields,
    ]
    if enable_tracing:
        processors.append(add_otel_context)
    processors.append(structlog.processors.JSONRenderer(serializer=serialize_json))

    structlog.configure(
        processors=processors,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

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
            ip = get_public_ip()
        elif isinstance(ip_address, str):
            ip = ip_address

        if ip:
            logger = logger.bind(ip_address=ip)

            if geo_info:
                logger = logger.bind(**get_geo_info(ip))

        # Handle device info
        if device_info:
            logger = logger.bind(**get_device_info(user_agent))

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

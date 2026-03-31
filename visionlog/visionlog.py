import sys
import warnings
import structlog
import loguru
import orjson
import uuid
import requests
import platform
from typing import Optional, Union

try:
    from device_detector import DeviceDetector
except ImportError:
    DeviceDetector = None

def serialize_json(record, *args, **kwargs):
    """Serialize logs using orjson for high-performance JSON output."""
    return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()

def get_public_ip():
    """Fetches the user's public IP address."""
    try:
        return requests.get("https://api64.ipify.org?format=json", timeout=5).json()["ip"]
    except (requests.RequestException, KeyError, ValueError) as error:
        warnings.warn(f"Failed to fetch public IP: {error}")
        return None

def get_geo_info(ip: str):
    """Fetches geo-location & ISP info for a given IP address."""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json", timeout=5).json()
        return {
            "city": response.get("city", ""),
            "region": response.get("region", ""),
            "country": response.get("country", ""),
            "timezone": response.get("timezone", ""),
            "org": response.get("org", ""),  # ISP / Organization
        }
    except (requests.RequestException, KeyError, ValueError) as error:
        warnings.warn(f"Failed to fetch geo info for IP {ip}: {error}")
        return {}

def get_device_info(user_agent: Optional[str] = None):
    """Extracts detailed device details from user-agent string."""
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

def add_common_fields(logger, method_name, event_dict):
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
):
    """
    Creates a structured logger with optional default fields.

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

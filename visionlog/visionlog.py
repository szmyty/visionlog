import sys
import structlog
import loguru
import orjson
import uuid
import requests
import platform
from device_detector import DeviceDetector
from typing import Optional

def serialize_json(record, *args, **kwargs):
    """Serialize logs using orjson for high-performance JSON output."""
    return orjson.dumps(record, option=orjson.OPT_APPEND_NEWLINE).decode()

def get_public_ip():
    """Fetches the user's public IP address."""
    try:
        return requests.get("https://api64.ipify.org?format=json").json()["ip"]
    except:
        return None

def get_geo_info(ip: str):
    """Fetches geo-location & ISP info for a given IP address."""
    try:
        response = requests.get(f"https://ipinfo.io/{ip}/json").json()
        return {
            "city": response.get("city", ""),
            "region": response.get("region", ""),
            "country": response.get("country", ""),
            "timezone": response.get("timezone", ""),
            "org": response.get("org", ""),  # ISP / Organization
        }
    except:
        return {}

def get_device_info(user_agent: Optional[str] = None):
    """Extracts detailed device details from user-agent string."""
    device = DeviceDetector(user_agent).parse() if user_agent else None

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

def get_logger(
    service_name="visionlog",
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    ip_address: Optional[str] = None,
    device_info: bool = False,
    user_agent: Optional[str] = None,
    geo_info: bool = False
):
    """
    Creates a structured logger with optional default fields.

    - `user_id`: Tracks the user identity
    - `session_id`: Tracks user session
    - `ip_address`: True (autodetect), None (ignore), or manual string
    - `device_info`: If True, extracts detailed device data
    - `user_agent`: Custom user-agent string for parsing device details
    - `geo_info`: If True, fetches IP geo-location (city, country, ISP, timezone)
    """

    loguru.logger.remove()
    loguru.logger.add(sys.stdout, format="{message}", serialize=False)
    
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            add_common_fields,
            structlog.processors.JSONRenderer(serializer=serialize_json),
        ],
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

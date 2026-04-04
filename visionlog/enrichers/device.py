"""Device detection enricher for visionlog."""
import platform

__all__ = ["get_device_info", "DeviceEnricher"]
from typing import Dict, Optional

import structlog

try:
    from device_detector import DeviceDetector
except ImportError:
    DeviceDetector = None


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


class DeviceEnricher:
    """Enricher that detects and binds device information to the logger.

    Uses the optional ``device-detector`` package when a user-agent string is
    provided, and falls back to :mod:`platform` data otherwise.

    Args:
        enabled: When ``True``, device detection is performed during
            :meth:`enrich`.  Defaults to ``False``.
        user_agent: Optional user-agent string used by the device detector.
            When ``None`` and ``enabled`` is ``True``, platform information is
            used as a fallback.

    Example::

        from visionlog import get_logger, DeviceEnricher

        logger = get_logger(
            privacy_mode=False,
            enrichers=[DeviceEnricher(enabled=True, user_agent=request.headers.get("User-Agent"))],
        )
    """

    def __init__(self, enabled: bool = False, user_agent: Optional[str] = None) -> None:
        self.enabled = enabled
        self.user_agent = user_agent

    def enrich(
        self, logger: structlog.stdlib.BoundLogger
    ) -> structlog.stdlib.BoundLogger:
        """Enrich *logger* with device information and return it."""
        if self.enabled:
            logger = logger.bind(**get_device_info(self.user_agent))
        return logger

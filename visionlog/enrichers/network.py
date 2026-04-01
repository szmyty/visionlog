"""Network enrichment module: public IP and geo-location logic."""
import functools
import warnings

import httpx
import structlog
from typing import Dict, Optional


@functools.lru_cache(maxsize=1)
def get_public_ip() -> Optional[str]:
    """Fetches the user's public IP address.

    The result is cached after the first successful (or failed) call so that
    repeated calls within the same process do not incur additional HTTP
    round-trips.  Call :func:`get_public_ip.cache_clear` to invalidate the
    cache if needed.

    .. warning::
        **PII / Privacy Notice**: The public IP address is Personally Identifiable
        Information (PII) under regulations such as GDPR and CCPA.  Only call this
        function when you have a lawful basis for collecting it and the caller has
        set ``privacy_mode=False`` in :func:`~visionlog.visionlog.get_logger`.
    """
    try:
        return httpx.get("https://api64.ipify.org?format=json", timeout=5.0).json()["ip"]
    except (httpx.RequestError, httpx.HTTPStatusError, KeyError, ValueError) as error:
        warnings.warn(f"Failed to fetch public IP: {error}")
        return None


def get_geo_info(ip: str, timeout: float = 5.0) -> Dict[str, str]:
    """Fetches geo-location & ISP info for a given IP address.

    .. warning::
        **PII / Privacy Notice**: Geo-location data derived from an IP address
        (city, region, country, timezone, ISP) may constitute PII under GDPR,
        CCPA, and similar regulations.  Only call this function when you have a
        lawful basis for collecting it and the caller has set
        ``privacy_mode=False`` in :func:`~visionlog.visionlog.get_logger`.
    """
    try:
        response = httpx.get(f"https://ipinfo.io/{ip}/json", timeout=timeout).json()
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


class NetworkEnricher:
    """Enriches a logger with the host's public IP and/or geo-location data.

    Implements the :class:`~visionlog.visionlog.Enricher` protocol so it can
    be passed directly to :func:`~visionlog.visionlog.get_logger` via the
    ``enrichers`` parameter.

    Args:
        ip: When ``True``, auto-fetch the public IP address and bind it as
            ``ip_address``.
        geo: When ``True`` (and an IP was resolved), fetch geo-location data
            (city, region, country, timezone, org) and bind all fields.
        timeout: HTTP timeout in seconds used for geo-location requests.
            The IP lookup uses a fixed 5-second timeout because its result is
            cached across calls.

    Example::

        from visionlog import get_logger
        from visionlog.enrichers.network import NetworkEnricher

        logger = get_logger(
            privacy_mode=False,
            enrichers=[NetworkEnricher(ip=True, geo=True)],
        )
    """

    def __init__(self, ip: bool = False, geo: bool = False, timeout: float = 5.0) -> None:
        self.ip = ip
        self.geo = geo
        self.timeout = timeout

    def enrich(
        self, logger: structlog.stdlib.BoundLogger
    ) -> structlog.stdlib.BoundLogger:
        """Enrich *logger* with IP and/or geo data and return it."""
        if self.ip:
            resolved_ip = get_public_ip()
            if resolved_ip:
                logger = logger.bind(ip_address=resolved_ip)
                if self.geo:
                    geo_data = get_geo_info(resolved_ip, self.timeout)
                    if geo_data:
                        logger = logger.bind(**geo_data)
        return logger

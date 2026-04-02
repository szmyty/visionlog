"""Unit tests for visionlog.enrichers.device module."""
import platform
from unittest.mock import MagicMock, patch

import pytest
import structlog

from visionlog.enrichers.device import DeviceEnricher, get_device_info
from visionlog.visionlog import Enricher, get_logger


# ---------------------------------------------------------------------------
# get_device_info() tests
# ---------------------------------------------------------------------------


def test_get_device_info_no_agent_returns_platform_fallback():
    """Verifies fallback to platform module when no user agent is provided."""
    info = get_device_info(user_agent=None)
    assert isinstance(info, dict)
    assert "device_type" in info
    assert "os" in info
    assert "os_version" in info
    assert "architecture" in info
    assert info["device_brand"] == ""
    assert info["device_model"] == ""
    assert info["browser"] == ""
    assert info["browser_version"] == ""


def test_get_device_info_architecture_is_populated():
    """Verifies that architecture is always populated from platform.architecture()."""
    info = get_device_info()
    assert info["architecture"] in ("32bit", "64bit", platform.architecture()[0])


def test_get_device_info_missing_package_raises_with_user_agent():
    """Verifies ImportError is raised when user_agent provided but package missing."""
    import visionlog.enrichers.device as device_module

    original = device_module.DeviceDetector
    try:
        device_module.DeviceDetector = None
        with pytest.raises(ImportError, match="pip install visionlog\\[device\\]"):
            get_device_info(user_agent="Mozilla/5.0")
    finally:
        device_module.DeviceDetector = original


def test_get_device_info_missing_package_no_agent_ok():
    """Verifies no error when DeviceDetector missing but no user_agent given."""
    import visionlog.enrichers.device as device_module

    original = device_module.DeviceDetector
    try:
        device_module.DeviceDetector = None
        info = get_device_info(user_agent=None)
        assert isinstance(info, dict)
        assert "device_type" in info
    finally:
        device_module.DeviceDetector = original


# ---------------------------------------------------------------------------
# DeviceEnricher protocol conformance
# ---------------------------------------------------------------------------


def test_device_enricher_satisfies_enricher_protocol():
    """Verifies that DeviceEnricher satisfies the Enricher protocol."""
    assert isinstance(DeviceEnricher(), Enricher)


# ---------------------------------------------------------------------------
# DeviceEnricher.__init__() defaults
# ---------------------------------------------------------------------------


def test_device_enricher_default_enabled_is_false():
    """Verifies that DeviceEnricher defaults to enabled=False."""
    enricher = DeviceEnricher()
    assert enricher.enabled is False


def test_device_enricher_default_user_agent_is_none():
    """Verifies that DeviceEnricher defaults to user_agent=None."""
    enricher = DeviceEnricher()
    assert enricher.user_agent is None


def test_device_enricher_stores_enabled_and_user_agent():
    """Verifies that constructor arguments are stored on the instance."""
    enricher = DeviceEnricher(enabled=True, user_agent="TestAgent/1.0")
    assert enricher.enabled is True
    assert enricher.user_agent == "TestAgent/1.0"


# ---------------------------------------------------------------------------
# DeviceEnricher.enrich() behaviour
# ---------------------------------------------------------------------------


def test_device_enricher_disabled_is_noop():
    """Verifies that DeviceEnricher with enabled=False makes no changes to the logger."""
    logger = get_logger()
    enricher = DeviceEnricher(enabled=False)
    result = enricher.enrich(logger)
    assert "device_type" not in result._context
    assert "os" not in result._context


def test_device_enricher_enabled_binds_device_fields():
    """Verifies that enabled=True binds device fields to the logger."""
    device_data = {
        "device_type": "desktop",
        "os": "Linux",
        "os_version": "5.15",
        "device_brand": "",
        "device_model": "",
        "architecture": "64bit",
        "browser": "",
        "browser_version": "",
    }
    with patch("visionlog.enrichers.device.get_device_info", return_value=device_data):
        logger = get_logger()
        enricher = DeviceEnricher(enabled=True)
        result = enricher.enrich(logger)
    assert result._context.get("device_type") == "desktop"
    assert result._context.get("os") == "Linux"
    assert result._context.get("architecture") == "64bit"


def test_device_enricher_passes_user_agent_to_get_device_info():
    """Verifies that the user_agent is forwarded to get_device_info."""
    with patch("visionlog.enrichers.device.get_device_info", return_value={
        "device_type": "", "os": "", "os_version": "",
        "device_brand": "", "device_model": "", "architecture": "64bit",
        "browser": "Chrome", "browser_version": "110",
    }) as mock_fn:
        logger = get_logger()
        enricher = DeviceEnricher(enabled=True, user_agent="Mozilla/5.0 Chrome/110")
        enricher.enrich(logger)
    mock_fn.assert_called_once_with("Mozilla/5.0 Chrome/110")


def test_device_enricher_enabled_false_does_not_call_get_device_info():
    """Verifies that get_device_info is not called when enabled=False."""
    with patch("visionlog.enrichers.device.get_device_info") as mock_fn:
        logger = get_logger()
        enricher = DeviceEnricher(enabled=False, user_agent="Mozilla/5.0")
        enricher.enrich(logger)
    mock_fn.assert_not_called()


def test_device_enricher_can_be_used_with_get_logger_enrichers():
    """Verifies that DeviceEnricher integrates with get_logger via enrichers param."""
    device_data = {
        "device_type": "mobile",
        "os": "Android",
        "os_version": "12",
        "device_brand": "Samsung",
        "device_model": "Galaxy S21",
        "architecture": "64bit",
        "browser": "Chrome Mobile",
        "browser_version": "110",
    }
    with patch("visionlog.enrichers.device.get_device_info", return_value=device_data):
        logger = get_logger(
            user_id="u42",
            enrichers=[DeviceEnricher(enabled=True, user_agent="Samsung Browser")],
        )
    assert logger._context.get("user_id") == "u42"
    assert logger._context.get("device_type") == "mobile"
    assert logger._context.get("device_brand") == "Samsung"


# ---------------------------------------------------------------------------
# Export / import tests
# ---------------------------------------------------------------------------


def test_device_enricher_exported_from_enrichers_package():
    """Verifies DeviceEnricher is accessible from visionlog.enrichers."""
    from visionlog.enrichers import DeviceEnricher as FromEnrichers

    assert FromEnrichers is DeviceEnricher


def test_device_enricher_exported_from_top_level_package():
    """Verifies DeviceEnricher is accessible from the top-level visionlog package."""
    from visionlog import DeviceEnricher as TopLevel

    assert TopLevel is DeviceEnricher


def test_get_device_info_importable_from_visionlog_visionlog():
    """Verifies backward-compatible re-export of get_device_info from visionlog.visionlog."""
    from visionlog.visionlog import get_device_info as from_visionlog

    assert from_visionlog is get_device_info

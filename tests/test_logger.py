"""Unit tests for visionlog core logging functions."""
import json
import warnings
from unittest.mock import patch, MagicMock

import pytest
import httpx

from visionlog.visionlog import (
    serialize_json,
    add_common_fields,
    get_device_info,
    get_geo_info,
    get_public_ip,
    get_logger,
)


def test_serialize_json():
    """Verifies JSON output format and newline handling."""
    record = {"event": "test", "level": "info"}
    result = serialize_json(record)
    assert result.endswith("\n"), "Serialized JSON should end with a newline"
    parsed = json.loads(result)
    assert parsed["event"] == "test"
    assert parsed["level"] == "info"


def test_add_common_fields():
    """Validates presence of log_id, app_name, and log_level in every log."""
    event_dict = {"event": "something happened"}
    result = add_common_fields(None, "info", event_dict)
    assert "log_id" in result, "log_id should be injected"
    assert "app_name" in result, "app_name should be injected"
    assert "log_level" in result, "log_level should be injected"
    assert result["app_name"] == "visionlog"
    assert result["log_level"] == "INFO"


def test_get_logger_basic():
    """Ensures logger initializes correctly without triggering network calls."""
    with patch("visionlog.visionlog.get_public_ip") as mock_ip:
        logger = get_logger()
        mock_ip.assert_not_called()
    assert logger is not None


def test_get_logger_with_user_id():
    """Verifies that user_id is bound to the logger."""
    logger = get_logger(user_id="user_42")
    # structlog BoundLogger stores bound variables in _context
    context = logger._context
    assert context.get("user_id") == "user_42"


def test_get_device_info_no_agent():
    """Verifies fallback behavior when no user agent is provided."""
    info = get_device_info(user_agent=None)
    assert isinstance(info, dict)
    assert "device_type" in info
    assert "os" in info
    assert "os_version" in info
    assert "architecture" in info
    # Without a user agent these fields default to empty strings
    assert info["device_brand"] == ""
    assert info["device_model"] == ""
    assert info["browser"] == ""
    assert info["browser_version"] == ""


def test_get_device_info_missing_package_raises():
    """Verifies that an ImportError is raised when user_agent is provided but DeviceDetector is not installed."""
    import visionlog.visionlog as vl_module

    original = vl_module.DeviceDetector
    try:
        vl_module.DeviceDetector = None
        with pytest.raises(ImportError, match="pip install visionlog\\[device\\]"):
            get_device_info(user_agent="Mozilla/5.0")
    finally:
        vl_module.DeviceDetector = original


def test_get_device_info_missing_package_no_agent_ok():
    """Verifies that no error is raised when DeviceDetector is missing but no user_agent is given."""
    import visionlog.visionlog as vl_module

    original = vl_module.DeviceDetector
    try:
        vl_module.DeviceDetector = None
        info = get_device_info(user_agent=None)
        assert isinstance(info, dict)
    finally:
        vl_module.DeviceDetector = original


def test_get_public_ip_failure():
    """Mocks a network failure and verifies graceful fallback to None with a warning."""
    with patch("visionlog.visionlog.httpx.get", side_effect=httpx.RequestError("network error")):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_public_ip()
    assert result is None
    assert len(caught) == 1
    assert "Failed to fetch public IP" in str(caught[0].message)


def test_get_public_ip_missing_key():
    """Mocks a missing key in the response and verifies graceful fallback to None with a warning."""
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # Missing "ip" key
    with patch("visionlog.visionlog.httpx.get", return_value=mock_response):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_public_ip()
    assert result is None
    assert len(caught) == 1
    assert "Failed to fetch public IP" in str(caught[0].message)


def test_get_geo_info_failure():
    """Mocks a network failure for geo info and verifies fallback to empty dict with a warning."""
    with patch("visionlog.visionlog.httpx.get", side_effect=httpx.RequestError("timeout")):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_geo_info("1.2.3.4")
    assert result == {}
    assert len(caught) == 1
    assert "Failed to fetch geo info" in str(caught[0].message)
    assert "1.2.3.4" in str(caught[0].message)


def test_get_geo_info_invalid_json():
    """Mocks an invalid JSON response for geo info and verifies fallback to empty dict with a warning."""
    mock_response = MagicMock()
    mock_response.json.side_effect = ValueError("invalid JSON")
    with patch("visionlog.visionlog.httpx.get", return_value=mock_response):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_geo_info("1.2.3.4")
    assert result == {}
    assert len(caught) == 1
    assert "Failed to fetch geo info" in str(caught[0].message)


def test_privacy_mode_true_skips_ip_lookup():
    """Verifies that privacy_mode=True (default) prevents IP lookup even when ip_address=True."""
    with patch("visionlog.visionlog.get_public_ip") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_privacy_mode_true_skips_geo_lookup():
    """Verifies that privacy_mode=True skips geo lookup even when geo_info=True."""
    with patch("visionlog.visionlog.get_geo_info") as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=True)
        mock_geo.assert_not_called()
    assert "city" not in logger._context
    assert "country" not in logger._context


def test_privacy_mode_true_skips_device_info():
    """Verifies that privacy_mode=True skips device detection even when device_info=True."""
    with patch("visionlog.visionlog.get_device_info") as mock_device:
        logger = get_logger(device_info=True, privacy_mode=True)
        mock_device.assert_not_called()
    assert "device_type" not in logger._context


def test_privacy_mode_default_is_true():
    """Verifies that privacy_mode defaults to True, preventing PII collection without opt-in."""
    with patch("visionlog.visionlog.get_public_ip") as mock_ip, \
         patch("visionlog.visionlog.get_device_info") as mock_device:
        logger = get_logger(ip_address=True, device_info=True)
        mock_ip.assert_not_called()
        mock_device.assert_not_called()
    assert "ip_address" not in logger._context
    assert "device_type" not in logger._context


def test_privacy_mode_false_allows_ip_lookup():
    """Verifies that privacy_mode=False allows IP lookup when ip_address=True."""
    with patch("visionlog.visionlog.get_public_ip", return_value="1.2.3.4") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False)
        mock_ip.assert_called_once()
    assert logger._context.get("ip_address") == "1.2.3.4"


def test_privacy_mode_false_allows_geo_lookup():
    """Verifies that privacy_mode=False allows geo lookup when geo_info=True and ip is provided."""
    geo_data = {"city": "Boston", "region": "MA", "country": "US", "timezone": "America/New_York", "org": "AS1 Example"}
    with patch("visionlog.visionlog.get_geo_info", return_value=geo_data) as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=False)
        mock_geo.assert_called_once_with("1.2.3.4")
    assert logger._context.get("city") == "Boston"


def test_privacy_mode_false_allows_device_info():
    """Verifies that privacy_mode=False allows device detection when device_info=True."""
    device_data = {
        "device_type": "desktop", "os": "Linux", "os_version": "5.15",
        "device_brand": "", "device_model": "", "architecture": "64bit",
        "browser": "", "browser_version": "",
    }
    with patch("visionlog.visionlog.get_device_info", return_value=device_data) as mock_device:
        logger = get_logger(device_info=True, privacy_mode=False)
        mock_device.assert_called_once()
    assert logger._context.get("device_type") == "desktop"

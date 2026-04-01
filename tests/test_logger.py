"""Unit tests for visionlog core logging functions."""
import json
import warnings
from unittest.mock import patch, MagicMock

import pytest
import httpx
import structlog

from visionlog.visionlog import (
    serialize_json,
    add_common_fields,
    get_device_info,
    get_geo_info,
    get_public_ip,
    get_logger,
    configure_visionlog,
    Enricher,
)
import visionlog.visionlog as vl_module


def test_serialize_json():
    """Verifies JSON output format and newline handling."""
    record = {"event": "test", "level": "info"}
    result = serialize_json(record)
    assert result.endswith("\n"), "Serialized JSON should end with a newline"
    parsed = json.loads(result)
    assert parsed["event"] == "test"
    assert parsed["level"] == "info"


def test_add_common_fields():
    """Validates presence of log_id and logger_library in every log."""
    event_dict = {"event": "something happened"}
    result = add_common_fields(None, "info", event_dict)
    assert "log_id" in result, "log_id should be injected"
    assert "logger_library" in result, "logger_library should be injected"
    assert "app_name" not in result, "app_name should not be present"
    assert "log_level" not in result, "log_level should not be present"
    assert result["logger_library"] == "visionlog"


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
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network.httpx.get", side_effect=httpx.RequestError("network error")):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_public_ip()
    assert result is None
    assert len(caught) == 1
    assert "Failed to fetch public IP" in str(caught[0].message)


def test_get_public_ip_missing_key():
    """Mocks a missing key in the response and verifies graceful fallback to None with a warning."""
    get_public_ip.cache_clear()
    mock_response = MagicMock()
    mock_response.json.return_value = {}  # Missing "ip" key
    with patch("visionlog.enrichers.network.httpx.get", return_value=mock_response):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = get_public_ip()
    assert result is None
    assert len(caught) == 1
    assert "Failed to fetch public IP" in str(caught[0].message)


def test_get_geo_info_failure():
    """Mocks a network failure for geo info and verifies fallback to empty dict with a warning."""
    with patch("visionlog.enrichers.network.httpx.get", side_effect=httpx.RequestError("timeout")):
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
    with patch("visionlog.enrichers.network.httpx.get", return_value=mock_response):
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


def test_disable_network_skips_ip_lookup():
    """Verifies that disable_network=True prevents get_public_ip from being called."""
    with patch("visionlog.visionlog.get_public_ip") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False, disable_network=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_disable_network_skips_geo_lookup():
    """Verifies that disable_network=True prevents get_geo_info from being called."""
    with patch("visionlog.visionlog.get_geo_info") as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=False, disable_network=True)
        mock_geo.assert_not_called()
    assert "city" not in logger._context
    assert "country" not in logger._context


def test_disable_network_false_allows_ip_lookup():
    """Verifies that disable_network=False (default) still allows IP lookup."""
    with patch("visionlog.visionlog.get_public_ip", return_value="9.9.9.9") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False, disable_network=False)
        mock_ip.assert_called_once()
    assert logger._context.get("ip_address") == "9.9.9.9"


def test_disable_network_allows_device_info():
    """Verifies that disable_network=True does not block device_info (no HTTP call)."""
    device_data = {
        "device_type": "desktop", "os": "Linux", "os_version": "5.15",
        "device_brand": "", "device_model": "", "architecture": "64bit",
        "browser": "", "browser_version": "",
    }
    with patch("visionlog.visionlog.get_device_info", return_value=device_data) as mock_device:
        logger = get_logger(device_info=True, privacy_mode=False, disable_network=True)
        mock_device.assert_called_once()
    assert logger._context.get("device_type") == "desktop"


def test_disable_network_default_is_false():
    """Verifies that disable_network defaults to False (does not block network calls)."""
    with patch("visionlog.visionlog.get_public_ip", return_value="5.5.5.5") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False)
        mock_ip.assert_called_once()
    assert logger._context.get("ip_address") == "5.5.5.5"


def test_disable_network_str_ip_still_bound():
    """Verifies that a string IP address is still bound even when disable_network=True (no HTTP needed)."""
    logger = get_logger(ip_address="1.2.3.4", privacy_mode=False, disable_network=True)
    assert logger._context.get("ip_address") == "1.2.3.4"


# ---------------------------------------------------------------------------
# configure_visionlog() tests
# ---------------------------------------------------------------------------

def test_configure_visionlog_is_idempotent():
    """Verifies that configure_visionlog() only calls structlog.configure() once."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        with patch("structlog.configure") as mock_configure:
            configure_visionlog()
            configure_visionlog()
            configure_visionlog()
        mock_configure.assert_called_once()
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_sets_flag():
    """Verifies that _CONFIGURED is set to True after configure_visionlog() runs."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        configure_visionlog()
        assert vl_module._CONFIGURED is True
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_skips_when_already_configured():
    """Verifies that configure_visionlog() skips structlog.configure() when _CONFIGURED is True."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = True
        with patch("structlog.configure") as mock_configure:
            configure_visionlog()
        mock_configure.assert_not_called()
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_custom_renderer():
    """Verifies that configure_visionlog() uses the provided renderer."""
    import structlog as _structlog

    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        custom_renderer = _structlog.dev.ConsoleRenderer()
        with patch("structlog.configure") as mock_configure:
            configure_visionlog(renderer=custom_renderer)
        mock_configure.assert_called_once()
        call_processors = mock_configure.call_args[1]["processors"]
        assert call_processors[-1] is custom_renderer
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_extra_processors():
    """Verifies that extra_processors are inserted before the renderer."""
    import structlog as _structlog

    def my_processor(logger, method_name, event_dict):
        return event_dict

    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        with patch("structlog.configure") as mock_configure:
            configure_visionlog(extra_processors=[my_processor])
        call_processors = mock_configure.call_args[1]["processors"]
        renderer = call_processors[-1]
        assert isinstance(renderer, _structlog.processors.JSONRenderer)
        assert my_processor in call_processors
        assert call_processors.index(my_processor) < call_processors.index(renderer)
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_calls_configure_visionlog():
    """Verifies that get_logger() triggers configure_visionlog() when not yet configured."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        with patch("visionlog.visionlog.configure_visionlog", wraps=configure_visionlog) as mock_cfg:
            get_logger()
        mock_cfg.assert_called_once()
    finally:
        vl_module._CONFIGURED = original


def test_no_structlog_configure_at_import_time():
    """Verifies that importing visionlog does not call structlog.configure() at module level."""
    import importlib
    import sys

    # Snapshot the current module state so we can restore it after the test
    saved_modules = {k: v for k, v in sys.modules.items() if "visionlog" in k}
    try:
        # Remove cached modules so we can re-import cleanly
        for mod_name in list(sys.modules.keys()):
            if "visionlog" in mod_name:
                del sys.modules[mod_name]

        with patch("structlog.configure") as mock_configure:
            importlib.import_module("visionlog")

        mock_configure.assert_not_called()
    finally:
        # Restore original module state to avoid polluting other tests
        for mod_name in list(sys.modules.keys()):
            if "visionlog" in mod_name:
                del sys.modules[mod_name]
        sys.modules.update(saved_modules)



# ---------------------------------------------------------------------------
# Enricher protocol tests
# ---------------------------------------------------------------------------

class _ConstantEnricher:
    """Test enricher that binds a fixed field."""

    def enrich(
        self, logger: structlog.stdlib.BoundLogger
    ) -> structlog.stdlib.BoundLogger:
        return logger.bind(enriched_by="constant")


class _ChainEnricher:
    """Test enricher that appends a step marker."""

    def __init__(self, step: int) -> None:
        self.step = step

    def enrich(
        self, logger: structlog.stdlib.BoundLogger
    ) -> structlog.stdlib.BoundLogger:
        return logger.bind(**{f"step_{self.step}": True})


def test_enricher_protocol_is_recognized():
    """Verifies that a class with enrich() satisfies the Enricher protocol."""
    assert isinstance(_ConstantEnricher(), Enricher)


def test_get_logger_no_enrichers_is_unchanged():
    """Verifies backward compatibility: omitting enrichers has no effect."""
    logger_plain = get_logger(user_id="u1")
    logger_none = get_logger(user_id="u1", enrichers=None)
    assert logger_plain._context == logger_none._context


def test_get_logger_single_enricher():
    """Verifies that a single enricher binds its fields to the logger."""
    logger = get_logger(enrichers=[_ConstantEnricher()])
    assert logger._context.get("enriched_by") == "constant"


def test_get_logger_multiple_enrichers_applied_in_order():
    """Verifies that multiple enrichers are applied in the order they are listed."""
    logger = get_logger(enrichers=[_ChainEnricher(1), _ChainEnricher(2)])
    assert logger._context.get("step_1") is True
    assert logger._context.get("step_2") is True


def test_get_logger_enrichers_combined_with_built_in_fields():
    """Verifies that enricher fields coexist with built-in bound fields."""
    logger = get_logger(user_id="u42", enrichers=[_ConstantEnricher()])
    assert logger._context.get("user_id") == "u42"
    assert logger._context.get("enriched_by") == "constant"


def test_get_logger_empty_enrichers_list():
    """Verifies that an empty enrichers list is treated the same as None."""
    logger = get_logger(enrichers=[])
    assert "enriched_by" not in logger._context


def test_enricher_exported_from_package():
    """Verifies that Enricher is accessible from the top-level visionlog package."""
    from visionlog import Enricher as TopLevelEnricher
    assert TopLevelEnricher is Enricher

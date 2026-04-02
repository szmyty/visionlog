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
from visionlog.config import LoggerConfig
import visionlog.visionlog as vl_module


def test_serialize_json():
    """Verifies JSON output format and newline handling."""
    record = {"event": "test", "level": "info"}
    result = serialize_json(record)
    assert result.endswith("\n"), "Serialized JSON should end with a newline"
    parsed = json.loads(result)
    assert parsed["event"] == "test"
    assert parsed["level"] == "info"


def test_serialize_json_fallback_on_error():
    """Verifies fallback to str(record) when orjson serialization fails."""
    non_serializable = {"event": object()}
    with patch("orjson.dumps", side_effect=TypeError("not serializable")):
        result = serialize_json(non_serializable)
    assert result == str(non_serializable)


def test_serialize_json_fallback_emits_warning():
    """Verifies that a warning is logged when orjson serialization fails."""
    mock_logger = MagicMock()
    with patch("orjson.dumps", side_effect=TypeError("not serializable")):
        with patch("logging.getLogger", return_value=mock_logger):
            serialize_json({"event": object()})
    mock_logger.warning.assert_called_once()


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
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip:
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
    import visionlog.enrichers.device as device_module

    original = device_module.DeviceDetector
    try:
        device_module.DeviceDetector = None
        with pytest.raises(ImportError, match="pip install visionlog\\[device\\]"):
            get_device_info(user_agent="Mozilla/5.0")
    finally:
        device_module.DeviceDetector = original


def test_get_device_info_missing_package_no_agent_ok():
    """Verifies that no error is raised when DeviceDetector is missing but no user_agent is given."""
    import visionlog.enrichers.device as device_module

    original = device_module.DeviceDetector
    try:
        device_module.DeviceDetector = None
        info = get_device_info(user_agent=None)
        assert isinstance(info, dict)
    finally:
        device_module.DeviceDetector = original


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
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_privacy_mode_true_skips_geo_lookup():
    """Verifies that privacy_mode=True skips geo lookup even when geo_info=True."""
    with patch("visionlog.enrichers.network.get_geo_info") as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=True)
        mock_geo.assert_not_called()
    assert "city" not in logger._context
    assert "country" not in logger._context


def test_privacy_mode_true_skips_device_info():
    """Verifies that privacy_mode=True skips device detection even when device_info=True."""
    with patch("visionlog.enrichers.device.get_device_info") as mock_device:
        logger = get_logger(device_info=True, privacy_mode=True)
        mock_device.assert_not_called()
    assert "device_type" not in logger._context


def test_privacy_mode_default_is_true():
    """Verifies that privacy_mode defaults to True, preventing PII collection without opt-in."""
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip, \
         patch("visionlog.enrichers.device.get_device_info") as mock_device:
        logger = get_logger(ip_address=True, device_info=True)
        mock_ip.assert_not_called()
        mock_device.assert_not_called()
    assert "ip_address" not in logger._context
    assert "device_type" not in logger._context


def test_privacy_mode_false_allows_ip_lookup():
    """Verifies that privacy_mode=False allows IP lookup when ip_address=True."""
    with patch("visionlog.enrichers.network.get_public_ip", return_value="1.2.3.4") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False)
        mock_ip.assert_called_once()
    assert logger._context.get("ip_address") == "1.2.3.4"


def test_privacy_mode_false_allows_geo_lookup():
    """Verifies that privacy_mode=False allows geo lookup when geo_info=True and ip is provided."""
    geo_data = {"city": "Boston", "region": "MA", "country": "US", "timezone": "America/New_York", "org": "AS1 Example"}
    with patch("visionlog.enrichers.network.get_geo_info", return_value=geo_data) as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=False)
        mock_geo.assert_called_once_with("1.2.3.4", 5.0)
    assert logger._context.get("city") == "Boston"


def test_privacy_mode_false_allows_device_info():
    """Verifies that privacy_mode=False allows device detection when device_info=True."""
    device_data = {
        "device_type": "desktop", "os": "Linux", "os_version": "5.15",
        "device_brand": "", "device_model": "", "architecture": "64bit",
        "browser": "", "browser_version": "",
    }
    with patch("visionlog.enrichers.device.get_device_info", return_value=device_data) as mock_device:
        logger = get_logger(device_info=True, privacy_mode=False)
        mock_device.assert_called_once()
    assert logger._context.get("device_type") == "desktop"


def test_disable_network_skips_ip_lookup():
    """Verifies that disable_network=True prevents get_public_ip from being called."""
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip:
        logger = get_logger(ip_address=True, privacy_mode=False, disable_network=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_disable_network_skips_geo_lookup():
    """Verifies that disable_network=True prevents get_geo_info from being called."""
    with patch("visionlog.enrichers.network.get_geo_info") as mock_geo:
        logger = get_logger(ip_address="1.2.3.4", geo_info=True, privacy_mode=False, disable_network=True)
        mock_geo.assert_not_called()
    assert "city" not in logger._context
    assert "country" not in logger._context


def test_disable_network_false_allows_ip_lookup():
    """Verifies that disable_network=False (default) still allows IP lookup."""
    with patch("visionlog.enrichers.network.get_public_ip", return_value="9.9.9.9") as mock_ip:
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
    with patch("visionlog.enrichers.device.get_device_info", return_value=device_data) as mock_device:
        logger = get_logger(device_info=True, privacy_mode=False, disable_network=True)
        mock_device.assert_called_once()
    assert logger._context.get("device_type") == "desktop"


def test_disable_network_default_is_false():
    """Verifies that disable_network defaults to False (does not block network calls)."""
    with patch("visionlog.enrichers.network.get_public_ip", return_value="5.5.5.5") as mock_ip:
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


# ---------------------------------------------------------------------------
# LoggerConfig-based usage tests
# ---------------------------------------------------------------------------

def test_get_logger_with_config_basic():
    """Verifies that get_logger accepts a LoggerConfig and creates a logger."""
    config = LoggerConfig(service_name="config-app")
    logger = get_logger(config=config)
    assert logger is not None


def test_get_logger_with_config_service_name():
    """Verifies that config.service_name is used as the service field."""
    config = LoggerConfig(service_name="my-service")
    logger = get_logger(config=config)
    assert logger._initial_values.get("service") == "my-service"


def test_get_logger_with_config_user_id():
    """Verifies that config.user_id is bound to the logger."""
    config = LoggerConfig(service_name="svc", user_id="cfg_user")
    logger = get_logger(config=config)
    assert logger._context.get("user_id") == "cfg_user"


def test_get_logger_with_config_session_id():
    """Verifies that config.session_id is bound to the logger."""
    config = LoggerConfig(service_name="svc", session_id="cfg_sess")
    logger = get_logger(config=config)
    assert logger._context.get("session_id") == "cfg_sess"


def test_get_logger_with_config_environment():
    """Verifies that config.environment is bound to the logger when provided."""
    config = LoggerConfig(service_name="svc", environment="production")
    logger = get_logger(config=config)
    assert logger._context.get("environment") == "production"


def test_get_logger_with_config_environment_none_not_bound():
    """Verifies that environment is not bound when config.environment is None."""
    config = LoggerConfig(service_name="svc")
    logger = get_logger(config=config)
    assert "environment" not in logger._context


def test_get_logger_with_config_hostname_true():
    """Verifies that config.hostname=True binds the machine hostname."""
    config = LoggerConfig(service_name="svc", hostname=True)
    with patch("socket.gethostname", return_value="test-host"):
        logger = get_logger(config=config)
    assert logger._context.get("hostname") == "test-host"


def test_get_logger_with_config_hostname_false_not_bound():
    """Verifies that hostname is not bound when config.hostname is False."""
    config = LoggerConfig(service_name="svc", hostname=False)
    logger = get_logger(config=config)
    assert "hostname" not in logger._context


def test_get_logger_with_config_privacy_mode_true_skips_enrichers():
    """Verifies that config.privacy_mode=True prevents PII enrichment."""
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip:
        config = LoggerConfig(service_name="svc", privacy_mode=True)
        logger = get_logger(config=config, ip_address=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_get_logger_with_config_privacy_mode_false_allows_enrichment():
    """Verifies that config.privacy_mode=False enables PII enrichment."""
    with patch("visionlog.enrichers.network.get_public_ip", return_value="1.2.3.4") as mock_ip:
        config = LoggerConfig(service_name="svc", privacy_mode=False)
        logger = get_logger(config=config, ip_address=True)
        mock_ip.assert_called_once()
    assert logger._context.get("ip_address") == "1.2.3.4"


def test_get_logger_with_config_disable_network():
    """Verifies that config.disable_network=True prevents HTTP calls."""
    with patch("visionlog.enrichers.network.get_public_ip") as mock_ip:
        config = LoggerConfig(service_name="svc", privacy_mode=False, disable_network=True)
        logger = get_logger(config=config, ip_address=True)
        mock_ip.assert_not_called()
    assert "ip_address" not in logger._context


def test_get_logger_with_config_enrichers():
    """Verifies that config.enrichers are applied to the logger."""
    class _TagEnricher:
        def enrich(self, logger):
            return logger.bind(tagged_by="config")

    config = LoggerConfig(service_name="svc", enrichers=[_TagEnricher()])
    logger = get_logger(config=config)
    assert logger._context.get("tagged_by") == "config"


def test_get_logger_with_config_overrides_kwargs():
    """Verifies that config values override matching keyword arguments."""
    config = LoggerConfig(service_name="config-name", user_id="config-user")
    logger = get_logger(config=config, service_name="kwarg-name", user_id="kwarg-user")
    assert logger._context.get("service") == "config-name"
    assert logger._context.get("user_id") == "config-user"


def test_get_logger_with_config_renderer():
    """Verifies that config.renderer is passed to configure_visionlog."""
    import structlog as _structlog

    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        custom_renderer = _structlog.dev.ConsoleRenderer()
        config = LoggerConfig(service_name="svc", renderer=custom_renderer)
        with patch("visionlog.visionlog.configure_visionlog", wraps=configure_visionlog) as mock_cfg:
            get_logger(config=config)
        mock_cfg.assert_called_once_with(renderer=custom_renderer, renderer_name="json", extra_processors=None)
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_with_config_extra_processors():
    """Verifies that config.extra_processors is passed to configure_visionlog."""
    import structlog as _structlog

    def my_processor(logger, method_name, event_dict):
        event_dict["custom"] = True
        return event_dict

    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        config = LoggerConfig(service_name="svc", extra_processors=[my_processor])
        with patch("visionlog.visionlog.configure_visionlog", wraps=configure_visionlog) as mock_cfg:
            get_logger(config=config)
        mock_cfg.assert_called_once_with(renderer=None, renderer_name="json", extra_processors=[my_processor])
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_config_extra_processors_in_pipeline():
    """Verifies that config.extra_processors are placed before the renderer in the pipeline."""
    import structlog as _structlog

    def my_processor(logger, method_name, event_dict):
        return event_dict

    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        config = LoggerConfig(service_name="svc", extra_processors=[my_processor])
        with patch("structlog.configure") as mock_configure:
            get_logger(config=config)
        call_processors = mock_configure.call_args[1]["processors"]
        renderer = call_processors[-1]
        assert isinstance(renderer, _structlog.processors.JSONRenderer)
        assert my_processor in call_processors
        assert call_processors.index(my_processor) < call_processors.index(renderer)
    finally:
        vl_module._CONFIGURED = original



    """Verifies backward compat: get_logger('my-app') still treats first arg as service_name."""
    logger = get_logger("legacy-app")
    assert logger._initial_values.get("service") == "legacy-app"


def test_get_logger_kwargs_still_work_without_config():
    """Verifies that individual keyword arguments still work when config is not provided."""
    logger = get_logger(service_name="kwarg-app", user_id="kwarg-user", session_id="kwarg-sess")
    assert logger._context.get("service") == "kwarg-app"
    assert logger._context.get("user_id") == "kwarg-user"
    assert logger._context.get("session_id") == "kwarg-sess"


# ---------------------------------------------------------------------------
# renderer_name / _build_renderer_from_name tests
# ---------------------------------------------------------------------------

from visionlog.visionlog import _build_renderer_from_name  # noqa: E402


def test_build_renderer_from_name_json():
    """Verifies that 'json' produces a JSONRenderer."""
    renderer = _build_renderer_from_name("json")
    assert isinstance(renderer, structlog.processors.JSONRenderer)


def test_build_renderer_from_name_console():
    """Verifies that 'console' produces a ConsoleRenderer."""
    renderer = _build_renderer_from_name("console")
    assert isinstance(renderer, structlog.dev.ConsoleRenderer)


def test_build_renderer_from_name_logfmt():
    """Verifies that 'logfmt' produces a LogfmtRenderer."""
    renderer = _build_renderer_from_name("logfmt")
    assert isinstance(renderer, structlog.processors.LogfmtRenderer)


def test_build_renderer_from_name_unknown_falls_back_to_json():
    """Verifies that an unknown renderer_name falls back to JSONRenderer."""
    renderer = _build_renderer_from_name("unknown-format")
    assert isinstance(renderer, structlog.processors.JSONRenderer)


def test_configure_visionlog_renderer_name_console():
    """Verifies that renderer_name='console' selects ConsoleRenderer."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        with patch("structlog.configure") as mock_configure:
            configure_visionlog(renderer_name="console")
        call_processors = mock_configure.call_args[1]["processors"]
        assert isinstance(call_processors[-1], structlog.dev.ConsoleRenderer)
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_renderer_name_logfmt():
    """Verifies that renderer_name='logfmt' selects LogfmtRenderer."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        with patch("structlog.configure") as mock_configure:
            configure_visionlog(renderer_name="logfmt")
        call_processors = mock_configure.call_args[1]["processors"]
        assert isinstance(call_processors[-1], structlog.processors.LogfmtRenderer)
    finally:
        vl_module._CONFIGURED = original


def test_configure_visionlog_custom_renderer_overrides_renderer_name():
    """Verifies that a custom renderer object takes precedence over renderer_name."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        custom_renderer = structlog.dev.ConsoleRenderer()
        with patch("structlog.configure") as mock_configure:
            configure_visionlog(renderer=custom_renderer, renderer_name="json")
        call_processors = mock_configure.call_args[1]["processors"]
        assert call_processors[-1] is custom_renderer
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_with_config_renderer_name_console():
    """Verifies that config.renderer_name='console' selects ConsoleRenderer."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        config = LoggerConfig(service_name="svc", renderer_name="console")
        with patch("structlog.configure") as mock_configure:
            get_logger(config=config)
        call_processors = mock_configure.call_args[1]["processors"]
        assert isinstance(call_processors[-1], structlog.dev.ConsoleRenderer)
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_with_config_renderer_name_logfmt():
    """Verifies that config.renderer_name='logfmt' selects LogfmtRenderer."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        config = LoggerConfig(service_name="svc", renderer_name="logfmt")
        with patch("structlog.configure") as mock_configure:
            get_logger(config=config)
        call_processors = mock_configure.call_args[1]["processors"]
        assert isinstance(call_processors[-1], structlog.processors.LogfmtRenderer)
    finally:
        vl_module._CONFIGURED = original


def test_get_logger_with_config_renderer_name_and_custom_renderer_uses_custom():
    """Verifies that config.renderer takes precedence over config.renderer_name."""
    original = vl_module._CONFIGURED
    try:
        vl_module._CONFIGURED = False
        custom_renderer = structlog.dev.ConsoleRenderer()
        config = LoggerConfig(
            service_name="svc",
            renderer_name="logfmt",
            renderer=custom_renderer,
        )
        with patch("structlog.configure") as mock_configure:
            get_logger(config=config)
        call_processors = mock_configure.call_args[1]["processors"]
        assert call_processors[-1] is custom_renderer
    finally:
        vl_module._CONFIGURED = original


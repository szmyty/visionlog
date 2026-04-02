"""Unit tests for the LoggerConfig dataclass."""
import pytest
import structlog

from visionlog.config import LoggerConfig
from visionlog import LoggerConfig as TopLevelLoggerConfig
from visionlog.visionlog import Enricher


# ---------------------------------------------------------------------------
# Basic construction
# ---------------------------------------------------------------------------

def test_loggerconfig_requires_service_name():
    """Verifies that service_name is the only required field."""
    cfg = LoggerConfig(service_name="my-service")
    assert cfg.service_name == "my-service"


def test_loggerconfig_defaults():
    """Verifies that all optional fields have the expected default values."""
    cfg = LoggerConfig(service_name="svc")
    assert cfg.user_id is None
    assert cfg.session_id is None
    assert cfg.privacy_mode is True
    assert cfg.disable_network is False
    assert cfg.enrichers == []
    assert cfg.hostname is False
    assert cfg.environment is None
    assert cfg.renderer_name == "json"
    assert cfg.renderer is None


def test_loggerconfig_missing_service_name_raises():
    """Verifies that omitting service_name raises a TypeError."""
    with pytest.raises(TypeError):
        LoggerConfig()  # type: ignore[call-arg]


# ---------------------------------------------------------------------------
# Field assignment
# ---------------------------------------------------------------------------

def test_loggerconfig_user_id():
    cfg = LoggerConfig(service_name="svc", user_id="u42")
    assert cfg.user_id == "u42"


def test_loggerconfig_session_id():
    cfg = LoggerConfig(service_name="svc", session_id="sess_001")
    assert cfg.session_id == "sess_001"


def test_loggerconfig_privacy_mode_false():
    cfg = LoggerConfig(service_name="svc", privacy_mode=False)
    assert cfg.privacy_mode is False


def test_loggerconfig_disable_network_true():
    cfg = LoggerConfig(service_name="svc", disable_network=True)
    assert cfg.disable_network is True


def test_loggerconfig_hostname_default():
    cfg = LoggerConfig(service_name="svc")
    assert cfg.hostname is False


def test_loggerconfig_hostname_true():
    cfg = LoggerConfig(service_name="svc", hostname=True)
    assert cfg.hostname is True


def test_loggerconfig_environment():
    cfg = LoggerConfig(service_name="svc", environment="production")
    assert cfg.environment == "production"


def test_loggerconfig_renderer():
    renderer = structlog.dev.ConsoleRenderer()
    cfg = LoggerConfig(service_name="svc", renderer=renderer)
    assert cfg.renderer is renderer


def test_loggerconfig_renderer_name_default():
    """Verifies that renderer_name defaults to 'json'."""
    cfg = LoggerConfig(service_name="svc")
    assert cfg.renderer_name == "json"


def test_loggerconfig_renderer_name_console():
    """Verifies that renderer_name can be set to 'console'."""
    cfg = LoggerConfig(service_name="svc", renderer_name="console")
    assert cfg.renderer_name == "console"


def test_loggerconfig_renderer_name_logfmt():
    """Verifies that renderer_name can be set to 'logfmt'."""
    cfg = LoggerConfig(service_name="svc", renderer_name="logfmt")
    assert cfg.renderer_name == "logfmt"


# ---------------------------------------------------------------------------
# Enrichers field
# ---------------------------------------------------------------------------

class _DummyEnricher:
    def enrich(self, logger: structlog.stdlib.BoundLogger) -> structlog.stdlib.BoundLogger:
        return logger.bind(dummy=True)


def test_loggerconfig_enrichers_default_is_empty_list():
    cfg = LoggerConfig(service_name="svc")
    assert cfg.enrichers == []


def test_loggerconfig_enrichers_populated():
    e = _DummyEnricher()
    cfg = LoggerConfig(service_name="svc", enrichers=[e])
    assert len(cfg.enrichers) == 1
    assert cfg.enrichers[0] is e


def test_loggerconfig_enrichers_mutable_default_independent():
    """Verifies that separate instances don't share the same enrichers list."""
    cfg1 = LoggerConfig(service_name="a")
    cfg2 = LoggerConfig(service_name="b")
    cfg1.enrichers.append(_DummyEnricher())
    assert cfg2.enrichers == []


def test_loggerconfig_enrichers_satisfy_protocol():
    """Verifies that enrichers stored in LoggerConfig satisfy the Enricher protocol."""
    e = _DummyEnricher()
    cfg = LoggerConfig(service_name="svc", enrichers=[e])
    assert isinstance(cfg.enrichers[0], Enricher)


# ---------------------------------------------------------------------------
# Exported from top-level package
# ---------------------------------------------------------------------------

def test_loggerconfig_exported_from_package():
    """Verifies that LoggerConfig is accessible from the top-level visionlog package."""
    assert TopLevelLoggerConfig is LoggerConfig


# ---------------------------------------------------------------------------
# extra_processors field
# ---------------------------------------------------------------------------

def test_loggerconfig_extra_processors_default_is_none():
    """Verifies that extra_processors defaults to None."""
    cfg = LoggerConfig(service_name="svc")
    assert cfg.extra_processors is None


def test_loggerconfig_extra_processors_populated():
    """Verifies that extra_processors can be set to a list of callables."""
    def my_processor(logger, method_name, event_dict):
        return event_dict

    cfg = LoggerConfig(service_name="svc", extra_processors=[my_processor])
    assert cfg.extra_processors is not None
    assert len(cfg.extra_processors) == 1
    assert cfg.extra_processors[0] is my_processor


def test_loggerconfig_extra_processors_empty_list():
    """Verifies that extra_processors can be set to an empty list."""
    cfg = LoggerConfig(service_name="svc", extra_processors=[])
    assert cfg.extra_processors == []

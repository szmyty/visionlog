"""Tests that verify the public API (``__all__``) exports of visionlog."""
import pytest


# ---------------------------------------------------------------------------
# Top-level package
# ---------------------------------------------------------------------------

def test_top_level_all_is_defined():
    """visionlog.__all__ must exist and be a list."""
    import visionlog
    assert hasattr(visionlog, "__all__")
    assert isinstance(visionlog.__all__, list)


def test_top_level_all_contents():
    """Every name in visionlog.__all__ must be importable from the package."""
    import visionlog
    for name in visionlog.__all__:
        assert hasattr(visionlog, name), f"visionlog.__all__ lists {name!r} but it is not accessible on the package"


@pytest.mark.parametrize("name", [
    "get_logger",
    "configure_visionlog",
    "LoggerConfig",
    "Enricher",
    "Processor",
    "NetworkEnricher",
    "DeviceEnricher",
    "get_public_ip",
    "get_geo_info",
    "get_device_info",
    "serialize_json",
    "add_common_fields",
    "add_otel_context",
])
def test_top_level_exports_each_name(name):
    """Each intended public name is exported from the top-level package."""
    import visionlog
    assert name in visionlog.__all__, f"{name!r} is missing from visionlog.__all__"
    assert hasattr(visionlog, name), f"{name!r} is in __all__ but not accessible as visionlog.{name}"


def test_top_level_no_private_names_in_all():
    """visionlog.__all__ must not expose private names (underscore-prefixed)."""
    import visionlog
    private = [n for n in visionlog.__all__ if n.startswith("_")]
    assert private == [], f"Private names found in visionlog.__all__: {private}"


# ---------------------------------------------------------------------------
# enrichers sub-package
# ---------------------------------------------------------------------------

def test_enrichers_all_is_defined():
    """visionlog.enrichers.__all__ must exist and be a list."""
    from visionlog import enrichers
    assert hasattr(enrichers, "__all__")
    assert isinstance(enrichers.__all__, list)


@pytest.mark.parametrize("name", [
    "NetworkEnricher",
    "DeviceEnricher",
    "get_public_ip",
    "get_geo_info",
    "get_device_info",
])
def test_enrichers_exports_each_name(name):
    """Each public name is accessible via visionlog.enrichers."""
    from visionlog import enrichers
    assert name in enrichers.__all__, f"{name!r} is missing from visionlog.enrichers.__all__"
    assert hasattr(enrichers, name), f"{name!r} is in __all__ but not accessible on the enrichers sub-package"


# ---------------------------------------------------------------------------
# enrichers.network module
# ---------------------------------------------------------------------------

def test_network_module_all_is_defined():
    """visionlog.enrichers.network.__all__ must exist."""
    from visionlog.enrichers import network
    assert hasattr(network, "__all__")


@pytest.mark.parametrize("name", ["get_public_ip", "get_geo_info", "NetworkEnricher"])
def test_network_module_exports_each_name(name):
    """Expected names are in visionlog.enrichers.network.__all__."""
    from visionlog.enrichers import network
    assert name in network.__all__
    assert hasattr(network, name)


def test_network_module_no_private_names_in_all():
    """No underscore-prefixed names in visionlog.enrichers.network.__all__."""
    from visionlog.enrichers import network
    private = [n for n in network.__all__ if n.startswith("_")]
    assert private == []


# ---------------------------------------------------------------------------
# enrichers.device module
# ---------------------------------------------------------------------------

def test_device_module_all_is_defined():
    """visionlog.enrichers.device.__all__ must exist."""
    from visionlog.enrichers import device
    assert hasattr(device, "__all__")


@pytest.mark.parametrize("name", ["get_device_info", "DeviceEnricher"])
def test_device_module_exports_each_name(name):
    """Expected names are in visionlog.enrichers.device.__all__."""
    from visionlog.enrichers import device
    assert name in device.__all__
    assert hasattr(device, name)


def test_device_module_no_private_names_in_all():
    """No underscore-prefixed names in visionlog.enrichers.device.__all__."""
    from visionlog.enrichers import device
    private = [n for n in device.__all__ if n.startswith("_")]
    assert private == []


# ---------------------------------------------------------------------------
# visionlog.visionlog core module
# ---------------------------------------------------------------------------

def test_core_module_all_is_defined():
    """visionlog.visionlog.__all__ must exist."""
    from visionlog import visionlog as core
    assert hasattr(core, "__all__")


@pytest.mark.parametrize("name", [
    "Enricher",
    "Processor",
    "serialize_json",
    "add_common_fields",
    "add_otel_context",
    "configure_visionlog",
    "get_logger",
])
def test_core_module_exports_each_name(name):
    """Expected names are in visionlog.visionlog.__all__."""
    from visionlog import visionlog as core
    assert name in core.__all__
    assert hasattr(core, name)


def test_core_module_no_private_names_in_all():
    """No underscore-prefixed names in visionlog.visionlog.__all__."""
    from visionlog import visionlog as core
    private = [n for n in core.__all__ if n.startswith("_")]
    assert private == []

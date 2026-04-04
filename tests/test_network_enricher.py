"""Unit tests for visionlog.enrichers.network module."""
from unittest.mock import patch

import httpx

from visionlog.enrichers.network import NetworkEnricher, get_geo_info, get_public_ip
from visionlog.visionlog import Enricher, get_logger


# ---------------------------------------------------------------------------
# get_public_ip() tests
# ---------------------------------------------------------------------------


def test_get_public_ip_returns_ip():
    """Verifies that get_public_ip returns the IP string on success."""
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network._fetch_json", return_value={"ip": "203.0.113.1"}):
        result = get_public_ip()
    assert result == "203.0.113.1"


def test_get_public_ip_caches_result():
    """Verifies that get_public_ip caches its result (lru_cache) across calls."""
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network._fetch_json", return_value={"ip": "203.0.113.1"}) as mock_fetch:
        first = get_public_ip()
        second = get_public_ip()
    assert first == second == "203.0.113.1"
    # _fetch_json should only have been called once thanks to lru_cache
    mock_fetch.assert_called_once()


# ---------------------------------------------------------------------------
# get_geo_info() tests
# ---------------------------------------------------------------------------


def test_get_geo_info_returns_all_fields():
    """Verifies that get_geo_info returns all expected geo fields."""
    with patch(
        "visionlog.enrichers.network._fetch_json",
        return_value={
            "city": "Boston",
            "region": "MA",
            "country": "US",
            "timezone": "America/New_York",
            "org": "AS1 Example",
        },
    ):
        result = get_geo_info("203.0.113.1")
    assert result == {
        "city": "Boston",
        "region": "MA",
        "country": "US",
        "timezone": "America/New_York",
        "org": "AS1 Example",
    }


def test_get_geo_info_missing_fields_default_to_empty():
    """Verifies that missing fields in geo response default to empty strings."""
    with patch("visionlog.enrichers.network._fetch_json", return_value={"city": "London"}):
        result = get_geo_info("203.0.113.1")
    assert result["city"] == "London"
    assert result["region"] == ""
    assert result["country"] == ""
    assert result["timezone"] == ""
    assert result["org"] == ""


def test_get_geo_info_uses_timeout_parameter():
    """Verifies that get_geo_info passes the timeout argument to _fetch_json."""
    with patch("visionlog.enrichers.network._fetch_json", return_value={}) as mock_fetch:
        get_geo_info("1.2.3.4", timeout=3.0)
    _, kwargs = mock_fetch.call_args
    assert kwargs.get("timeout") == 3.0


# ---------------------------------------------------------------------------
# NetworkEnricher protocol conformance
# ---------------------------------------------------------------------------


def test_network_enricher_satisfies_enricher_protocol():
    """Verifies that NetworkEnricher satisfies the Enricher protocol."""
    assert isinstance(NetworkEnricher(), Enricher)


# ---------------------------------------------------------------------------
# NetworkEnricher.enrich() behaviour
# ---------------------------------------------------------------------------


def test_network_enricher_no_ip_no_geo_is_noop():
    """Verifies that NetworkEnricher with ip=False, geo=False makes no changes."""
    get_public_ip.cache_clear()
    logger_before = get_logger(user_id="u1")
    enricher = NetworkEnricher(ip=False, geo=False)
    logger_after = enricher.enrich(logger_before)
    assert "ip_address" not in logger_after._context
    assert "city" not in logger_after._context


def test_network_enricher_ip_true_binds_ip():
    """Verifies that ip=True fetches and binds the public IP."""
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network._fetch_json", return_value={"ip": "10.0.0.1"}):
        logger = get_logger()
        enricher = NetworkEnricher(ip=True)
        logger = enricher.enrich(logger)
    assert logger._context.get("ip_address") == "10.0.0.1"


def test_network_enricher_ip_and_geo_binds_both():
    """Verifies that ip=True, geo=True fetches and binds IP and geo data."""
    get_public_ip.cache_clear()
    responses = [
        {"ip": "10.0.0.2"},
        {
            "city": "Berlin",
            "region": "BE",
            "country": "DE",
            "timezone": "Europe/Berlin",
            "org": "AS2 Example",
        },
    ]

    with patch("visionlog.enrichers.network._fetch_json", side_effect=responses):
        logger = get_logger()
        enricher = NetworkEnricher(ip=True, geo=True)
        logger = enricher.enrich(logger)

    assert logger._context.get("ip_address") == "10.0.0.2"
    assert logger._context.get("city") == "Berlin"
    assert logger._context.get("country") == "DE"


def test_network_enricher_geo_skipped_when_ip_fails():
    """Verifies that geo enrichment is skipped when IP lookup fails."""
    get_public_ip.cache_clear()
    with patch(
        "visionlog.enrichers.network._fetch_json",
        side_effect=httpx.RequestError("timeout"),
    ):
        with patch("visionlog.enrichers.network._logger"):
            logger = get_logger()
            enricher = NetworkEnricher(ip=True, geo=True)
            logger = enricher.enrich(logger)

    assert "ip_address" not in logger._context
    assert "city" not in logger._context


def test_network_enricher_geo_false_skips_geo():
    """Verifies that geo=False skips geo lookup even when IP is found."""
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network._fetch_json", return_value={"ip": "10.0.0.3"}) as mock_fetch:
        logger = get_logger()
        enricher = NetworkEnricher(ip=True, geo=False)
        logger = enricher.enrich(logger)

    assert logger._context.get("ip_address") == "10.0.0.3"
    assert "city" not in logger._context
    # _fetch_json should only have been called once (for IP, not geo)
    mock_fetch.assert_called_once()


def test_network_enricher_can_be_used_with_get_logger_enrichers():
    """Verifies that NetworkEnricher integrates with get_logger via enrichers param."""
    get_public_ip.cache_clear()
    with patch("visionlog.enrichers.network._fetch_json", return_value={"ip": "10.0.0.4"}):
        logger = get_logger(
            user_id="u99",
            privacy_mode=False,
            enrichers=[NetworkEnricher(ip=True)],
        )
    assert logger._context.get("user_id") == "u99"
    assert logger._context.get("ip_address") == "10.0.0.4"


def test_network_enricher_exported_from_package():
    """Verifies NetworkEnricher is accessible from the top-level visionlog package."""
    from visionlog import NetworkEnricher as TopLevel

    assert TopLevel is NetworkEnricher

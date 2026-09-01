import httpx
import pytest

from geo_agent.tools import territorial


def _reset():
    territorial._get_territorial_context.cache_clear()
    territorial._last_request_at = 0.0


def test_territorial_context_success(httpx_mock):
    _reset()
    httpx_mock.add_response(json=[{
        "lat": "-31.4167",
        "lon": "-64.1833",
        "display_name": "Córdoba, Argentina",
        "category": "place",
        "type": "city",
        "address": {"city": "Córdoba", "country": "Argentina", "country_code": "ar"},
    }])

    result = territorial._get_territorial_context("Cordoba, Argentina")

    assert result["ok"] is True
    assert result["data"]["latitude"] == -31.4167
    assert result["data"]["longitude"] == -64.1833
    request = httpx_mock.get_requests()[0]
    assert request.headers["User-Agent"].startswith("geo-agent-langgraph/")


def test_territorial_context_no_result(httpx_mock):
    _reset()
    httpx_mock.add_response(json=[])

    result = territorial._get_territorial_context("not-a-real-place")

    assert result["ok"] is False
    assert result["error"] == "Location not found"


def test_territorial_context_caches_same_query(httpx_mock):
    _reset()
    httpx_mock.add_response(json=[{"lat": "-31.4", "lon": "-64.1", "address": {}}])

    territorial._get_territorial_context("Córdoba")
    territorial._get_territorial_context("Córdoba")

    assert len(httpx_mock.get_requests()) == 1


def test_territorial_context_throttles_second_uncached_request(httpx_mock, monkeypatch):
    _reset()
    times = iter([100.0, 100.0, 100.25, 101.0])
    sleeps = []
    monkeypatch.setattr(territorial.time, "monotonic", lambda: next(times))
    monkeypatch.setattr(territorial.time, "sleep", lambda seconds: sleeps.append(seconds))
    httpx_mock.add_response(json=[{"lat": "-31.4", "lon": "-64.1", "address": {}}])
    httpx_mock.add_response(json=[{"lat": "-32.8", "lon": "-68.8", "address": {}}])

    territorial._get_territorial_context("Córdoba")
    territorial._get_territorial_context("Mendoza")

    assert len(sleeps) == 1
    assert sleeps[0] == pytest.approx(0.75)


def test_territorial_context_returns_structured_network_failure(httpx_mock):
    _reset()
    httpx_mock.add_exception(httpx.ConnectError("network down"))

    result = territorial._get_territorial_context("Córdoba")

    assert result["ok"] is False
    assert result["data"] is None
    assert "Nominatim request failed" in result["error"]

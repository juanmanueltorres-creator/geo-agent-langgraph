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

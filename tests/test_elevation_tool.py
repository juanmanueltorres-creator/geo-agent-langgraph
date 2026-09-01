import httpx

from geo_agent.tools.elevation import _get_elevation


def test_elevation_success(httpx_mock):
    httpx_mock.add_response(json={"elevation": [390.0]})

    result = _get_elevation(-31.42, -64.19)

    assert result["ok"] is True
    assert result["data"]["elevation_m"] == 390.0


def test_elevation_rejects_empty_payload(httpx_mock):
    httpx_mock.add_response(json={"elevation": []})

    result = _get_elevation(-31.42, -64.19)

    assert result["ok"] is False
    assert result["error"] == "Open-Meteo returned invalid elevation data"


def test_elevation_returns_structured_network_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("network down"))

    result = _get_elevation(-31.42, -64.19)

    assert result["ok"] is False
    assert result["data"] is None
    assert "Elevation request failed" in result["error"]

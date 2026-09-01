import httpx

from geo_agent.tools.weather import _get_weather


def test_weather_success(httpx_mock):
    httpx_mock.add_response(json={
        "timezone": "America/Argentina/Cordoba",
        "current": {
            "time": "2026-08-25T21:00",
            "temperature_2m": 18.4,
            "apparent_temperature": 17.9,
            "precipitation": 0.0,
            "weather_code": 1,
            "wind_speed_10m": 8.2,
        },
    })

    result = _get_weather(-31.42, -64.19)

    assert result["ok"] is True
    assert result["data"]["temperature_2m"] == 18.4


def test_weather_rejects_incomplete_payload(httpx_mock):
    httpx_mock.add_response(json={"current": {}})

    result = _get_weather(-31.42, -64.19)

    assert result["ok"] is False
    assert result["error"] == "Open-Meteo returned incomplete current weather data"


def test_weather_returns_structured_network_failure(httpx_mock):
    httpx_mock.add_exception(httpx.ConnectError("network down"))

    result = _get_weather(-31.42, -64.19)

    assert result["ok"] is False
    assert result["data"] is None
    assert "Open-Meteo request failed" in result["error"]

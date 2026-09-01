import httpx
from langchain_core.tools import tool

from .common import DEFAULT_TIMEOUT_SECONDS, ToolResult, failure, success

WEATHER_URL = "https://api.open-meteo.com/v1/forecast"
CURRENT_FIELDS = (
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
)


def _get_weather(latitude: float, longitude: float) -> ToolResult:
    try:
        response = httpx.get(
            WEATHER_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(CURRENT_FIELDS),
                "timezone": "auto",
            },
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return failure("get_weather", f"Open-Meteo request failed: {exc}")

    current = payload.get("current") or {}
    if any(field not in current for field in CURRENT_FIELDS):
        return failure("get_weather", "Open-Meteo returned incomplete current weather data")

    return success(
        "get_weather",
        {
            **{field: current[field] for field in CURRENT_FIELDS},
            "time": current.get("time"),
            "timezone": payload.get("timezone"),
        },
    )


@tool
def get_weather(latitude: float, longitude: float) -> ToolResult:
    """Get current weather for WGS84 coordinates."""
    return _get_weather(latitude, longitude)

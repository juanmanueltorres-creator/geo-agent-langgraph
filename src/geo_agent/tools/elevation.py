import httpx
from langchain_core.tools import tool

from .common import DEFAULT_TIMEOUT_SECONDS, ToolResult, failure, success

ELEVATION_URL = "https://api.open-meteo.com/v1/elevation"


def _get_elevation(latitude: float, longitude: float) -> ToolResult:
    try:
        response = httpx.get(
            ELEVATION_URL,
            params={"latitude": latitude, "longitude": longitude},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return failure("get_elevation", f"Elevation request failed: {exc}")

    values = payload.get("elevation")
    if not isinstance(values, list) or not values or not isinstance(values[0], (int, float)):
        return failure("get_elevation", "Open-Meteo returned invalid elevation data")

    return success("get_elevation", {"elevation_m": float(values[0])})


@tool
def get_elevation(latitude: float, longitude: float) -> ToolResult:
    """Get terrain elevation in metres for WGS84 coordinates."""
    return _get_elevation(latitude, longitude)

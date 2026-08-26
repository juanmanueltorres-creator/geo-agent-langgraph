from .tools.common import ToolResult

WEATHER_FIELDS = {
    "temperature_2m",
    "apparent_temperature",
    "precipitation",
    "weather_code",
    "wind_speed_10m",
}


def validate_tool_result(result: ToolResult) -> tuple[bool, str | None]:
    if not result.get("ok"):
        return False, str(result.get("error") or "Tool failed")

    data = result.get("data")
    if not isinstance(data, dict):
        return False, "Tool result data is missing"

    if result["tool"] == "get_territorial_context":
        latitude = data.get("latitude")
        longitude = data.get("longitude")
        if not isinstance(latitude, (int, float)) or not isinstance(longitude, (int, float)):
            return False, "Coordinates are missing"
        if not -90 <= latitude <= 90 or not -180 <= longitude <= 180:
            return False, "Coordinates outside WGS84 range"

    elif result["tool"] == "get_elevation":
        if not isinstance(data.get("elevation_m"), (int, float)):
            return False, "Elevation is missing or non-numeric"

    elif result["tool"] == "get_weather":
        if not WEATHER_FIELDS.issubset(data):
            return False, "Required weather fields are missing"

    return True, None

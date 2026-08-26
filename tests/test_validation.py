from geo_agent.validation import validate_tool_result


def test_rejects_failed_result():
    valid, error = validate_tool_result({
        "ok": False,
        "tool": "get_weather",
        "data": None,
        "error": "provider unavailable",
    })

    assert (valid, error) == (False, "provider unavailable")


def test_rejects_coordinates_outside_wgs84():
    valid, error = validate_tool_result({
        "ok": True,
        "tool": "get_territorial_context",
        "data": {"latitude": 120.0, "longitude": -64.0},
        "error": None,
    })

    assert (valid, error) == (False, "Coordinates outside WGS84 range")


def test_accepts_numeric_elevation():
    valid, error = validate_tool_result({
        "ok": True,
        "tool": "get_elevation",
        "data": {"elevation_m": 390.0},
        "error": None,
    })

    assert (valid, error) == (True, None)


def test_rejects_weather_missing_required_field():
    valid, error = validate_tool_result({
        "ok": True,
        "tool": "get_weather",
        "data": {"temperature_2m": 18.4},
        "error": None,
    })

    assert (valid, error) == (False, "Required weather fields are missing")

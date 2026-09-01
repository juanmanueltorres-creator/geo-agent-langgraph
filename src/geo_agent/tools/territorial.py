from functools import lru_cache
import time

import httpx
from langchain_core.tools import tool

from .common import DEFAULT_TIMEOUT_SECONDS, ToolResult, failure, success

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "geo-agent-langgraph/0.1 (+https://github.com/juanmanueltorres-creator/geo-agent-langgraph)"
_last_request_at = 0.0


def _throttle() -> None:
    global _last_request_at
    now = time.monotonic()
    elapsed = now - _last_request_at
    if _last_request_at and elapsed < 1.0:
        time.sleep(1.0 - elapsed)
    _last_request_at = time.monotonic()


@lru_cache(maxsize=128)
def _get_territorial_context(location: str) -> ToolResult:
    name = location.strip()
    if not name:
        return failure("get_territorial_context", "Location is required")

    _throttle()
    try:
        response = httpx.get(
            NOMINATIM_URL,
            params={"q": name, "format": "jsonv2", "addressdetails": 1, "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        items = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        return failure("get_territorial_context", f"Nominatim request failed: {exc}")

    if not items:
        return failure("get_territorial_context", "Location not found")

    item = items[0]
    try:
        data = {
            "latitude": float(item["lat"]),
            "longitude": float(item["lon"]),
            "display_name": item.get("display_name"),
            "category": item.get("category"),
            "type": item.get("type"),
            "address": item.get("address", {}),
        }
    except (KeyError, TypeError, ValueError):
        return failure("get_territorial_context", "Nominatim returned malformed coordinates")

    return success("get_territorial_context", data)


@tool
def get_territorial_context(location: str) -> ToolResult:
    """Resolve a place name to WGS84 coordinates and administrative context."""
    return _get_territorial_context(location)

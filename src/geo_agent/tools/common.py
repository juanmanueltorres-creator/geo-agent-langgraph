from typing import Any, TypedDict


class ToolResult(TypedDict):
    ok: bool
    tool: str
    data: dict[str, Any] | None
    error: str | None


DEFAULT_TIMEOUT_SECONDS = 10.0


def success(tool: str, data: dict[str, Any]) -> ToolResult:
    return {"ok": True, "tool": tool, "data": data, "error": None}


def failure(tool: str, message: str) -> ToolResult:
    return {"ok": False, "tool": tool, "data": None, "error": message}

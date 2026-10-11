"""Shared result contract for external intelligence clients."""
from typing import Any, Literal, TypedDict


class ToolItem(TypedDict, total=False):
    title: str
    source: str
    url: str
    date: str
    snippet: str
    source_type: str


class ToolResult(TypedDict):
    status: Literal["ok", "empty", "error"]
    mock: bool
    items: list[ToolItem]
    error: str | None

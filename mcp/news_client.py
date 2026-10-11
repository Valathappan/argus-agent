"""Search clearly labelled mock news fixtures.

The fixtures are fictional classroom data, never live reporting.
"""
from __future__ import annotations

import json
import re
from datetime import date
from pathlib import Path
from typing import Any

from mcp.result import ToolResult

_DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "mock" / "news.json"


def _load_items() -> list[dict[str, Any]]:
    with _DATA_PATH.open(encoding="utf-8-sig") as stream:
        items = json.load(stream)
    if not isinstance(items, list):
        raise ValueError("Mock news fixture must contain a JSON list")
    return items


def _matches_query(item: dict[str, Any], query: str) -> bool:
    terms = set(re.findall(r"[a-z0-9]+", query.casefold()))
    if not terms:
        return True
    searchable = " ".join(str(item.get(key, "")) for key in ("title", "snippet", "source")).casefold()
    return any(term in searchable for term in terms)


def _in_date_range(item: dict[str, Any], date_range: tuple[str | date, str | date] | None) -> bool:
    if date_range is None:
        return True
    if len(date_range) != 2:
        raise ValueError("date_range must be a (start, end) pair")
    start, end = (value if isinstance(value, date) else date.fromisoformat(value) for value in date_range)
    item_date = date.fromisoformat(item["date"])
    return start <= item_date <= end


def search_news(
    query: str,
    date_range: tuple[str | date, str | date] | None = None,
    region: str | None = None,
    *,
    simulate_failure: bool = False,
) -> ToolResult:
    """Search mock news by query, inclusive ISO date range, and region.

    Set ``simulate_failure=True`` to return a deterministic timeout result for
    testing callers' degradation behavior.
    """
    if simulate_failure:
        return {"status": "error", "mock": True, "items": [], "error": "Simulated news tool timeout"}
    try:
        items = _load_items()
        found = [
            {**item, "mock": True}
            for item in items
            if _matches_query(item, query)
            and _in_date_range(item, date_range)
            and (region is None or region.casefold() in str(item.get("region", "")).casefold())
        ]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "mock": True, "items": [], "error": f"Unable to read mock news data: {exc}"}
    return {"status": "ok" if found else "empty", "mock": True, "items": found, "error": None}

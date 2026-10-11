"""Search clearly labelled mock government and regulatory notices."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from mcp.result import ToolResult

_DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "mock" / "government_notices.json"


def _load_items() -> list[dict[str, Any]]:
    with _DATA_PATH.open(encoding="utf-8-sig") as stream:
        items = json.load(stream)
    if not isinstance(items, list):
        raise ValueError("Mock government fixture must contain a JSON list")
    return items


def _matches_query(item: dict[str, Any], query: str) -> bool:
    terms = set(re.findall(r"[a-z0-9]+", query.casefold()))
    if not terms:
        return True
    searchable = " ".join(str(item.get(key, "")) for key in ("title", "snippet", "source")).casefold()
    return any(term in searchable for term in terms)


def search_regulation(
    query: str,
    jurisdiction: str | None = None,
    *,
    simulate_failure: bool = False,
) -> ToolResult:
    """Search mock regulatory notices by query and optional jurisdiction.

    Set ``simulate_failure=True`` to return a deterministic timeout result.
    """
    if simulate_failure:
        return {"status": "error", "mock": True, "items": [], "error": "Simulated regulatory tool timeout"}
    try:
        items = _load_items()
        found = [
            {**item, "mock": True}
            for item in items
            if _matches_query(item, query)
            and (jurisdiction is None or jurisdiction.casefold() in str(item.get("jurisdiction", "")).casefold())
        ]
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "mock": True, "items": [], "error": f"Unable to read mock regulatory data: {exc}"}
    return {"status": "ok" if found else "empty", "mock": True, "items": found, "error": None}

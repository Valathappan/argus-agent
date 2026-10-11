"""Search FederalRegister.gov, or explicitly selected local mock notices."""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.result import ToolResult

_DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "mock" / "government_notices.json"
_ENDPOINT = "https://www.federalregister.gov/api/v1/documents.json"
_TIMEOUT_SECONDS = 12


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


def _live_search(query: str, jurisdiction: str | None) -> list[dict[str, Any]]:
    if jurisdiction and jurisdiction.casefold() not in {"us", "usa", "united states", "federal"}:
        return []
    params = {"per_page": "20", "order": "newest", "conditions[term]": query}
    request = Request(f"{_ENDPOINT}?{urlencode(params)}", headers={"User-Agent": "ARGUS-class-demo/1.0"})
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if isinstance(payload, dict):
        payload = payload.get("results", [])
    if not isinstance(payload, list):
        raise ValueError("Federal Register response did not contain a results list")
    found = []
    for notice in payload:
        agencies = notice.get("agencies") or []
        agency_names = [agency.get("name", "") for agency in agencies if isinstance(agency, dict)]
        found.append({
            "title": notice.get("title") or "Untitled Federal Register document",
            "source": ", ".join(agency_names) or "Federal Register",
            "url": notice.get("html_url") or notice.get("public_inspection_pdf_url", ""),
            "date": notice.get("publication_date", ""),
            "snippet": notice.get("abstract", ""),
            "source_type": "government",
            "mock": False,
        })
    return found


def search_regulation(
    query: str,
    jurisdiction: str | None = None,
    *,
    simulate_failure: bool = False,
    use_mock: bool | None = None,
) -> ToolResult:
    """Search live Federal Register notices by default; use_mock=True selects fixtures."""
    if simulate_failure:
        return {"status": "error", "mock": use_mock is not False, "items": [], "error": "Simulated regulatory tool timeout"}
    if use_mock is None:
        use_mock = os.getenv("ARGUS_MCP_MODE", "live").casefold() == "mock"
    try:
        if use_mock:
            items = _load_items()
            found = [
                {**item, "mock": True}
                for item in items
                if _matches_query(item, query)
                and (jurisdiction is None or jurisdiction.casefold() in str(item.get("jurisdiction", "")).casefold())
            ]
        else:
            found = _live_search(query, jurisdiction)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "mock": bool(use_mock), "items": [], "error": f"Regulatory search failed: {exc}"}
    return {"status": "ok" if found else "empty", "mock": bool(use_mock), "items": found, "error": None}


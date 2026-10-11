"""Search live news with GDELT, or explicitly selected local mock fixtures."""
from __future__ import annotations

import json
import os
import re
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from mcp.result import ToolResult

_DATA_PATH = Path(__file__).resolve().parents[1] / "Data" / "mock" / "news.json"
_ENDPOINT = "https://api.gdeltproject.org/api/v2/doc/doc"
_TIMEOUT_SECONDS = 12


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


def _as_date(value: str | date) -> date:
    return value if isinstance(value, date) else date.fromisoformat(value)


def _date_params(date_range: tuple[str | date, str | date] | None) -> dict[str, str]:
    if date_range is None:
        return {"timespan": "3months"}
    if len(date_range) != 2:
        raise ValueError("date_range must be a (start, end) pair")
    start, end = (_as_date(value) for value in date_range)
    if end < start:
        raise ValueError("date_range end must not be before start")
    start_dt = datetime.combine(start, time.min, tzinfo=timezone.utc)
    end_dt = datetime.combine(end + timedelta(days=1), time.min, tzinfo=timezone.utc)
    return {
        "startdatetime": start_dt.strftime("%Y%m%d%H%M%S"),
        "enddatetime": end_dt.strftime("%Y%m%d%H%M%S"),
    }


def _region_query(region: str | None) -> str:
    if not region:
        return ""
    normalized = region.strip().casefold()
    countries = {
        "us": "US", "usa": "US", "united states": "US", "north america": "US",
        "uk": "UK", "united kingdom": "UK", "canada": "CA", "china": "CH",
        "japan": "JA", "india": "IN", "australia": "AS",
    }
    country = countries.get(normalized)
    if country is None and len(normalized) == 2 and normalized.isalpha():
        country = normalized.upper()
    return f" sourcecountry:{country}" if country else ""


def _live_search(query: str, date_range: tuple[str | date, str | date] | None, region: str | None) -> list[dict[str, Any]]:
    params = {
        "query": f"{query.strip()}{_region_query(region)}".strip(),
        "mode": "artlist",
        "format": "json",
        "maxrecords": "20",
        "sort": "datedesc",
        **_date_params(date_range),
    }
    request = Request(f"{_ENDPOINT}?{urlencode(params)}", headers={"User-Agent": "ARGUS-class-demo/1.0"})
    with urlopen(request, timeout=_TIMEOUT_SECONDS) as response:
        payload = json.loads(response.read().decode("utf-8"))
    articles = payload.get("articles", [])
    if not isinstance(articles, list):
        raise ValueError("GDELT response did not contain an article list")
    found = []
    for article in articles:
        raw_date = str(article.get("seendate", ""))
        try:
            published = datetime.strptime(raw_date, "%Y%m%dT%H%M%SZ").date().isoformat()
        except ValueError:
            published = raw_date
        found.append({
            "title": article.get("title") or "Untitled article",
            "source": article.get("domain") or "GDELT indexed source",
            "url": article.get("url", ""),
            "date": published,
            "snippet": article.get("snippet", ""),
            "source_type": "news",
            "mock": False,
        })
    return found


def search_news(
    query: str,
    date_range: tuple[str | date, str | date] | None = None,
    region: str | None = None,
    *,
    simulate_failure: bool = False,
    use_mock: bool | None = None,
) -> ToolResult:
    """Search live GDELT news by default; pass use_mock=True for fixtures."""
    if simulate_failure:
        return {"status": "error", "mock": use_mock is not False, "items": [], "error": "Simulated news tool timeout"}
    if use_mock is None:
        use_mock = os.getenv("ARGUS_MCP_MODE", "live").casefold() == "mock"
    try:
        if use_mock:
            items = _load_items()
            found = [
                {**item, "mock": True}
                for item in items
                if _matches_query(item, query)
                and (region is None or region.casefold() in str(item.get("region", "")).casefold())
            ]
            if date_range is not None:
                start, end = (_as_date(value) for value in date_range)
                found = [item for item in found if start <= date.fromisoformat(item["date"]) <= end]
        else:
            found = _live_search(query, date_range, region)
    except (HTTPError, URLError, TimeoutError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
        return {"status": "error", "mock": bool(use_mock), "items": [], "error": f"News search failed: {exc}"}
    return {"status": "ok" if found else "empty", "mock": bool(use_mock), "items": found, "error": None}

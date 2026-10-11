"""Small end-to-end ARGUS external research graph.

This starter workflow calls the news and regulation MCP clients and returns
source-linked evidence. Internal retrieval and risk analysis can be added as
separate nodes when those components are ready.
"""
from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from mcp.government_client import search_regulation
from mcp.news_client import search_news


class ArgusState(TypedDict, total=False):
    question: str
    query: str
    user_query: str
    news_articles: list[dict[str, Any]]
    government_evidence: list[dict[str, Any]]
    errors: list[str]
    final_report: str
    report: str


def _query(state: ArgusState) -> str:
    return str(state.get("question") or state.get("query") or state.get("user_query") or "").strip()


def external_discovery(state: ArgusState) -> dict[str, Any]:
    query = _query(state)
    news = search_news(query)
    regulations = search_regulation(query)
    errors = []
    for label, result in (("News", news), ("Regulation", regulations)):
        if result["status"] == "error":
            errors.append(f"{label} source: {result['error']}")
    return {
        "news_articles": news["items"],
        "government_evidence": regulations["items"],
        "errors": errors,
    }


def build_report(state: ArgusState) -> dict[str, str]:
    news = state.get("news_articles", [])
    regulations = state.get("government_evidence", [])
    errors = state.get("errors", [])
    lines = [f"ARGUS research results for: {_query(state)}", ""]
    if not news and not regulations:
        lines.append("No matching external evidence was returned.")
    for heading, items in (("News", news), ("Regulatory notices", regulations)):
        lines.extend((f"{heading} ({len(items)} result(s)):",))
        if not items:
            lines.append("  No matching results.")
        for item in items:
            label = "MOCK" if item.get("mock") else "LIVE"
            lines.append(f"  [{label}] {item.get('date', 'date unavailable')} — {item.get('title', 'Untitled')}")
            lines.append(f"    Source: {item.get('source', 'unknown source')}")
            lines.append(f"    URL: {item.get('url', 'unavailable')}")
            if item.get("snippet"):
                lines.append(f"    {item['snippet']}")
        lines.append("")
    if errors:
        lines.extend(("Source errors:", *(f"  - {error}" for error in errors), ""))
    lines.append("This research summary is not a verified legal or business-impact assessment.")
    report = "\n".join(lines)
    return {"final_report": report, "report": report}


def build_graph():
    workflow = StateGraph(ArgusState)
    workflow.add_node("external_discovery", external_discovery)
    workflow.add_node("build_report", build_report)
    workflow.add_edge(START, "external_discovery")
    workflow.add_edge("external_discovery", "build_report")
    workflow.add_edge("build_report", END)
    return workflow.compile()


graph = build_graph()

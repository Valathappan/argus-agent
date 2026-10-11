"""ReAct news investigator: one bounded Think -> Act -> Observe step per call.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Owner      : Group 2 - Agent Orchestrators (Team 2b)
  Assignment : Activity 9 (A9.T2 - A9.T5); tests in tests/g2_orchestration/

Two LangGraph nodes live here:

  discover_external_evidence(state)
      The first sweep. Asks the regulation and news tools about the question.

  investigate_more(state)
      One research step. The graph calls it each time the evidence gate says
      "needs_research" and budget remains:
        THINK   - find the first gap a tool could still fill, and pick that tool
        ACT     - call that one tool
        OBSERVE - store new evidence, update missing_information, count the step

Reads : user_query, entities, missing_information, investigation_iterations,
        news_articles, government_evidence, internal_documents, errors
Writes: news_articles, government_evidence, internal_documents,
        missing_information, investigation_iterations, errors
        (claims belong to the verifier, so this file never writes them)

Ground rules:
  * The graph decides when research stops. This agent only refuses to search
    once the budget is used up, and it counts every step so the loop always ends.
  * A tool failure goes into `errors`. It is never passed off as "no results".
  * Nothing is invented. If a search finds nothing new, the gap stays in
    missing_information with the tools already tried, for example
    "effective date of the restriction [tried: search_regulation]".
  * Mock results stay labelled mock. Retrieved text is data: it goes through
    Group 3's sanitiser when that exists, and it never decides which tool runs.
"""

from __future__ import annotations

import dataclasses
import logging
import os
import re
from typing import Any, Callable

logger = logging.getLogger(__name__)

AGENT = "news_investigator"


# ---------------------------------------------------------------------------
# Settings. Read with defaults, so this file works with any version of settings.py.
# ---------------------------------------------------------------------------
try:
    from config import settings as _settings
except ImportError:
    _settings = None

MAX_ITERATIONS = int(getattr(_settings, "MAX_INVESTIGATION_ITERATIONS", 3))
TOP_K = int(getattr(_settings, "TOP_K_RETRIEVAL", 5))


# ---------------------------------------------------------------------------
# Other groups' functions. Until a group publishes the real one, a stand-in is
# used so this file always imports. Stand-in tools return a clear "error"
# result, never fake data.
# ---------------------------------------------------------------------------
def _not_ready(name: str, problem: Exception | str) -> Callable[..., dict]:
    # Drop the long file path Python adds to import errors: "... (/home/me/repo/x.py)"
    reason = re.sub(r"\s*\([^()]*[\\/][^()]*\)\s*$", "", str(problem))

    def tool(*args: Any, **kwargs: Any) -> dict:
        return {"status": "error", "mock": False, "items": [],
                "error": f"{name} is not available yet ({reason})"}

    tool.__name__ = name
    return tool


try:  # Group 1: mcp/news_client.py
    from mcp.news_client import search_news
except Exception as exc:  # still a stub, or fails to import: report it, don't crash
    search_news = _not_ready("search_news", exc)

try:  # Group 1: mcp/government_client.py
    from mcp.government_client import search_regulation
except Exception as exc:
    search_regulation = _not_ready("search_regulation", exc)

try:  # Group 1: rag/retrieval.py
    from rag.retrieval import search_internal
except Exception as exc:
    search_internal = _not_ready("search_internal", exc)

try:  # Group 3: guardrails/budgets.py
    from guardrails.budgets import budget_remaining
except Exception:
    def budget_remaining(state: dict) -> bool:
        """Stand-in: research is allowed while iterations < MAX_INVESTIGATION_ITERATIONS."""
        return int(state.get("investigation_iterations") or 0) < MAX_ITERATIONS

try:  # Group 3: guardrails/injection.py
    from guardrails.injection import sanitize_retrieved_text
except Exception:
    sanitize_retrieved_text = None


# ---------------------------------------------------------------------------
# The tools this agent can use, and the state list each one's results go into.
# The order only matters for ties: the more authoritative source goes first.
# ---------------------------------------------------------------------------
TOOL_ORDER = ["search_regulation", "search_news", "search_internal"]

RESULT_KEY = {
    "search_regulation": "government_evidence",
    "search_news": "news_articles",
    "search_internal": "internal_documents",
}

# THINK matches a gap to a tool with these words (whole words; a plural "s" is fine).
TOOL_KEYWORDS = {
    "search_regulation": [
        "regulation", "regulatory", "rule", "notice", "official", "government",
        "law", "agency", "jurisdiction", "effective date", "scope",
        "export control", "restriction", "sanction", "license", "licence", "ban",
    ],
    "search_news": [
        "news", "report", "article", "media", "press", "headline", "coverage",
        "announcement", "statement", "viral", "latest", "market",
    ],
    "search_internal": [
        "internal", "our", "we", "supplier", "product", "component", "inventory",
        "stock", "contract", "purchase order", "procurement", "exposure",
        "exposed", "bom", "document", "policy", "playbook",
    ],
}

# If a tool's evidence list is still empty, THINK treats that as a gap of its own.
EVIDENCE_GAPS = [
    ("search_regulation", "official government or regulatory source"),
    ("search_news", "recent news reports"),
    ("search_internal", "internal documents on our exposure"),
]


# ---------------------------------------------------------------------------
# Gap labels: "effective date [tried: search_news]" <-> ("effective date", ["search_news"])
# ---------------------------------------------------------------------------
_TRIED = re.compile(r"\s*\[tried: ([^\]]*)\]\s*$")


def split_gap(entry: str) -> tuple[str, list[str]]:
    """'effective date [tried: search_news]' -> ('effective date', ['search_news'])."""
    match = _TRIED.search(entry)
    if not match:
        return entry.strip(), []
    tried = [name.strip() for name in match.group(1).split(",") if name.strip()]
    return entry[: match.start()].strip(), tried


def mark_tried(gap: str, tried: list[str]) -> str:
    """('effective date', ['search_news']) -> 'effective date [tried: search_news]'."""
    return f"{gap} [tried: {', '.join(tried)}]" if tried else gap


# ---------------------------------------------------------------------------
# THINK: what is missing, and which tool should look for it?
# ---------------------------------------------------------------------------
def _keyword_hits(text: str, keywords: list[str]) -> list[str]:
    text = text.lower()
    return [word for word in keywords if re.search(rf"\b{re.escape(word)}s?\b", text)]


def choose_tools(gap: str) -> list[tuple[str, list[str]]]:
    """Tools that fit a gap, best first, each with the keywords that matched.

    A tool fits when at least one of its keywords is in the gap. When nothing
    matches at all, every tool is worth a try, most authoritative first.
    """
    scored = [(tool, _keyword_hits(gap, TOOL_KEYWORDS[tool])) for tool in TOOL_ORDER]
    fitting = [pair for pair in scored if pair[1]]
    if not fitting:
        return scored
    return sorted(fitting, key=lambda pair: len(pair[1]), reverse=True)  # ties keep TOOL_ORDER


def _failed_tools(state: dict) -> set[str]:
    """Tools this agent has already seen fail in this run (read back from `errors`)."""
    errors = [str(error) for error in state.get("errors") or []]
    return {tool for tool in TOOL_ORDER
            if any(error.startswith(f"{AGENT}: {tool} failed") for error in errors)}


def think(state: dict) -> dict | None:
    """Pick the next gap to research and the tool to use.

    Returns a plan {"entry", "gap", "tried", "tool", "why"}, or None when no
    tool could add anything. Tools that already failed in this run go last,
    so one broken tool can't block the other gaps.
    """
    entries = [str(entry) for entry in state.get("missing_information") or []]
    listed = {split_gap(entry)[0].lower() for entry in entries}
    for tool, topic in EVIDENCE_GAPS:
        if not state.get(RESULT_KEY[tool]) and topic not in listed:
            entries.append(topic)

    options = []
    for entry in entries:
        gap, tried = split_gap(entry)
        for tool, matched in choose_tools(gap):
            if tool not in tried:
                why = f"matched: {', '.join(matched)}" if matched else "no keyword matched"
                options.append({"entry": entry, "gap": gap, "tried": tried, "tool": tool, "why": why})

    failed = _failed_tools(state)
    for plan in options:
        if plan["tool"] not in failed:
            return plan
    return options[0] if options else None  # only failed tools left: retry one


def build_query(gap: str, state: dict) -> str:
    """Search text: the gap plus what the question is about (the supervisor's entities)."""
    entities = [e.strip() for e in state.get("entities") or [] if isinstance(e, str) and e.strip()]
    subject = " ".join(entities) or str(state.get("user_query") or "").strip()
    if not gap:
        return subject
    if not subject or subject.lower() in gap.lower():
        return gap
    return f"{gap} {subject}"


# ---------------------------------------------------------------------------
# ACT: call one tool and always get a ToolResult back (Assignment 4.2).
# ---------------------------------------------------------------------------
def _simulated_failures() -> set[str]:
    """Tools to fail on purpose for demos, e.g. ARGUS_SIMULATE_TOOL_FAILURE=search_news."""
    raw = os.getenv("ARGUS_SIMULATE_TOOL_FAILURE", "")
    return {name.strip() for name in raw.split(",") if name.strip()}


def _as_dict(item: Any) -> dict:
    if isinstance(item, dict):
        return dict(item)
    if hasattr(item, "model_dump"):  # pydantic model (models/schemas.py)
        return item.model_dump()
    if dataclasses.is_dataclass(item):  # dataclass (rag/models.py)
        return dataclasses.asdict(item)
    return {"text": str(item)}


def _as_tool_result(raw: Any) -> dict:
    """Turn whatever a tool returned into {"status", "mock", "items", "error"}."""
    if hasattr(raw, "model_dump"):
        raw = raw.model_dump()
    if isinstance(raw, list):  # search_internal returns a plain list of chunks
        items = [_as_dict(item) for item in raw]
        return {"status": "ok" if items else "empty", "mock": False, "items": items, "error": None}
    if isinstance(raw, dict) and raw.get("status") in ("ok", "empty", "error"):
        items = [_as_dict(item) for item in raw.get("items") or []]
        status = "empty" if raw["status"] == "ok" and not items else raw["status"]
        return {"status": status, "mock": bool(raw.get("mock")), "items": items,
                "error": raw.get("error")}
    return {"status": "error", "mock": False, "items": [],
            "error": f"unexpected tool output: {raw!r:.80}"}


def act(tool: str, query: str) -> dict:
    """Call one tool. A crash or a simulated failure comes back as status "error"."""
    if tool in _simulated_failures():
        return {"status": "error", "mock": True, "items": [],
                "error": "simulated failure (ARGUS_SIMULATE_TOOL_FAILURE)"}
    try:
        if tool == "search_regulation":
            raw = search_regulation(query)
        elif tool == "search_news":
            raw = search_news(query)
        elif tool == "search_internal":
            raw = search_internal(query, top_k=TOP_K)
        else:
            raise ValueError(f"unknown tool {tool!r}")
    except Exception as exc:  # a broken tool must not crash the investigation
        return {"status": "error", "mock": False, "items": [],
                "error": f"{type(exc).__name__}: {exc}"}
    return _as_tool_result(raw)


# ---------------------------------------------------------------------------
# OBSERVE: write what was found back into the state.
# ---------------------------------------------------------------------------
def _item_key(item: dict) -> str:
    """Same URL or source id = same item. The same story from different outlets is kept."""
    return str(item.get("url") or item.get("source_id")
               or (item.get("source"), item.get("title"), item.get("date")))


def _clean(item: dict) -> dict:
    """Run Group 3's injection check over the text fields, when it exists."""
    if sanitize_retrieved_text is None:
        return item
    for field in ("snippet", "text"):
        if isinstance(item.get(field), str):
            checked = sanitize_retrieved_text(item[field])
            item[field] = checked.get("text", item[field])
            if checked.get("flagged"):
                item["injection_flagged"] = True
    return item


def observe(state: dict, plan: dict, query: str, result: dict, iteration: int) -> dict:
    """Record one tool result. Returns only the state keys that changed."""
    tool, gap, entry = plan["tool"], plan["gap"], plan["entry"]
    updates: dict[str, Any] = {}

    # 1. Store new evidence, labelled with how it was found.
    key = RESULT_KEY[tool]
    existing = list(state.get(key) or [])
    seen = {_item_key(item) for item in existing}
    new_items = []
    if result["status"] == "ok":
        for item in result["items"]:
            if _item_key(item) in seen:
                continue
            seen.add(_item_key(item))
            if result["mock"]:
                item.setdefault("mock", True)
            item["found_by"] = {"agent": AGENT, "tool": tool, "query": query, "iteration": iteration}
            new_items.append(_clean(item))
    if new_items:
        updates[key] = existing + new_items

    # 2. Update the gaps: answered -> remove; failed -> keep for a retry; nothing new -> mark tried.
    old_gaps = [str(entry) for entry in state.get("missing_information") or []]
    if new_items:
        replacement = None
    elif result["status"] == "error":
        replacement = entry
    else:
        replacement = mark_tried(gap, plan["tried"] + [tool])
    gaps = list(old_gaps)
    if entry in gaps:
        position = gaps.index(entry)
        gaps[position:position + 1] = [replacement] if replacement else []
    elif replacement:
        gaps.append(replacement)  # a gap THINK spotted on its own (an empty evidence list)
    if gaps != old_gaps:
        updates["missing_information"] = gaps

    # 3. Record failures honestly.
    if result["status"] == "error":
        updates["errors"] = list(state.get("errors") or []) + [
            f"{AGENT}: {tool} failed while looking for '{gap}': {result['error']}"
        ]
    return updates


# ---------------------------------------------------------------------------
# LangGraph nodes
# ---------------------------------------------------------------------------
def investigate_more(state: dict) -> dict:
    """One bounded Think -> Act -> Observe step (Assignment A9.T2)."""
    if not budget_remaining(state):
        logger.info("[%s] budget used up, no new search", AGENT)
        return {}
    iteration = int(state.get("investigation_iterations") or 0) + 1
    updates: dict[str, Any] = {"investigation_iterations": iteration}

    plan = think(state)
    if plan is None:
        logger.info("[%s] step %d THINK: nothing left that a tool could find", AGENT, iteration)
        return updates

    query = build_query(plan["gap"], state)
    logger.info("[%s] step %d THINK: '%s' -> %s (%s)",
                AGENT, iteration, plan["gap"], plan["tool"], plan["why"])
    logger.info("[%s] step %d ACT: %s(%r)", AGENT, iteration, plan["tool"], query)
    result = act(plan["tool"], query)
    logger.info("[%s] step %d OBSERVE: %s, %d item(s)%s", AGENT, iteration, result["status"],
                len(result["items"]), f" - {result['error']}" if result["error"] else "")
    updates.update(observe(state, plan, query, result, iteration))
    return updates


def discover_external_evidence(state: dict) -> dict:
    """First sweep: ask the official and news sources about the question.

    It searches with the user's own question, so the first look is broad; the
    follow-up steps in investigate_more use short, targeted queries. This sweep
    is not counted as a research iteration; the budget is for investigate_more.
    """
    query = str(state.get("user_query") or "").strip() or build_query("", state)
    working = dict(state)
    updates: dict[str, Any] = {}
    for tool, topic in EVIDENCE_GAPS[:2]:  # official source first, then news
        plan = {"entry": topic, "gap": topic, "tried": [], "tool": tool}
        result = act(tool, query)
        logger.info("[%s] first sweep: %s(%r) -> %s, %d item(s)",
                    AGENT, tool, query, result["status"], len(result["items"]))
        step = observe(working, plan, query, result, iteration=0)
        working.update(step)
        updates.update(step)
    return updates


if __name__ == "__main__":
    # Try it from the repo root:  python -m agents.news_investigator
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    demo: dict[str, Any] = {
        "user_query": "There are reports of new semiconductor export restrictions. Investigate "
                      "what changed, check whether our suppliers/products may be exposed, "
                      "estimate risk and recommend next actions.",
        "entities": ["semiconductor", "export restrictions"],
        "missing_information": ["effective date of the restriction",
                                "which of our products use the affected components"],
        "investigation_iterations": 0,
    }
    demo.update(discover_external_evidence(demo))
    for _ in range(MAX_ITERATIONS):
        demo.update(investigate_more(demo))
    print()
    for name in ("government_evidence", "news_articles", "internal_documents"):
        print(f"{name}: {len(demo.get(name) or [])} item(s)")
    print("missing_information:", demo.get("missing_information"))
    print("errors:", *(demo.get("errors") or ["none"]), sep="\n  ")
"""CLI / service entrypoint: load config, build the graph, run one investigation end to end.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (shared)
  Blueprint reference : §5, §8
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, Iterable, Optional


def _load_question(raw: Optional[str]) -> str:
    """Normalize the user question from CLI args or stdin."""
    if raw:
        return raw.strip()

    try:
        data = sys.stdin.read().strip()
    except Exception:
        data = ""
    if data:
        return data

    raise ValueError("A user question is required. Pass it as a positional argument or via stdin.")


def _build_state(question: str) -> Dict[str, Any]:
    """Create the intelligence state expected by the LangGraph app.

    This keeps the entrypoint compatible with small and large graphs by
    supporting multiple common schema names.
    """
    state: Dict[str, Any] = {
        "question": question,
        "query": question,
        "user_question": question,
        "input": question,
        "status": "ready",
        "messages": [{"role": "user", "content": question}],
    }
    return state


def _resolve_app():
    """Return the compiled LangGraph app, if available.

    The project layout is intentionally not hard-coded here; we support a few
    common entrypoint names while failing gracefully if no graph has been built.
    """
    candidates = (
        ("app", "compiled_app"),
        ("app", "app"),
        ("graph", "compiled_graph"),
        ("graph", "graph"),
        ("main", "app"),
        ("agent", "app"),
        ("orchestrator", "app"),
    )

    for module_name, attr_name in candidates:
        try:
            module = __import__(module_name, fromlist=[attr_name])
            app = getattr(module, attr_name, None)
            if app is not None:
                return app
        except Exception:
            continue

    return None


def _extract_report(result: Any) -> str:
    """Convert graph output into a plain-text executive report."""
    if result is None:
        return "No executive report was produced."

    if isinstance(result, str):
        return result

    if isinstance(result, dict):
        for key in ("executive_report", "report", "final_report", "answer", "output"):
            value = result.get(key)
            if value is not None:
                return str(value)
        return json.dumps(result, indent=2, ensure_ascii=False)

    if hasattr(result, "dict"):
        try:
            payload = result.dict()
            return _extract_report(payload)
        except Exception:
            pass

    if hasattr(result, "model_dump"):
        try:
            payload = result.model_dump()
            return _extract_report(payload)
        except Exception:
            pass

    return str(result)


def main(argv: Optional[Iterable[str]] = None) -> int:
    """Parse the question, construct state, invoke the compiled graph, and print output."""
    parser = argparse.ArgumentParser(description="ARGUS investigation runner")
    parser.add_argument("question", nargs="?", help="User question to investigate")
    parser.add_argument("--config", default=None, help="Optional config path; if omitted, project config is loaded by the app module.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        question = _load_question(args.question)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    if args.config:
        os.environ.setdefault("ARGUS_CONFIG", args.config)

    app = _resolve_app()
    if app is None:
        print(
            "Error: no compiled LangGraph app was found. "
            "Expose a callable like `compiled_app` or `app` from the project module.",
            file=sys.stderr,
        )
        return 1

    state = _build_state(question)

    try:
        if hasattr(app, "invoke"):
            result = app.invoke(state)
        elif callable(app):
            result = app(state)
        else:
            raise TypeError("Resolved app is not callable and has no .invoke() method")
    except Exception as exc:
        print(f"Error while invoking the LangGraph app: {exc}", file=sys.stderr)
        return 1

    print(_extract_report(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

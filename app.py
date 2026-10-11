"""CLI entrypoint for one ARGUS external research query."""
from __future__ import annotations

import argparse
import sys
from typing import Iterable, Optional


def _resolve_app():
    """Load the compiled graph object, not its containing Python module."""
    try:
        from graph.graph import graph as compiled_graph
        return compiled_graph
    except Exception as exc:
        print(f"Unable to load the ARGUS graph: {exc}", file=sys.stderr)
        return None


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="ARGUS live research runner")
    parser.add_argument("question", help="Question to search in news and government sources")
    args = parser.parse_args(list(argv) if argv is not None else None)
    app = _resolve_app()
    if app is None:
        return 1
    state = {"question": args.question, "query": args.question, "user_query": args.question}
    try:
        result = app.invoke(state)
    except Exception as exc:
        print(f"Error while invoking ARGUS: {exc}", file=sys.stderr)
        return 1
    report = result.get("final_report") or result.get("report") or "No report was produced."
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

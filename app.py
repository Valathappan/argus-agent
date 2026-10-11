"""Interactive CLI for repeated ARGUS research questions."""
from __future__ import annotations

import argparse
import os
import sys
from typing import Iterable, Optional

from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()
EXIT_COMMANDS = {"exit", "quit", "/quit", "/exit"}


def _resolve_app():
    """Load the compiled LangGraph object."""
    try:
        from graph.graph import graph as compiled_graph
        return compiled_graph
    except Exception as exc:
        console.print(f"Could not load the ARGUS graph: {exc}", style="bold red")
        return None


def _ask(app, question: str) -> None:
    """Run one query and show a source-linked report."""
    state = {"question": question, "query": question, "user_query": question}
    try:
        with console.status("Searching news and government sources...", spinner="dots"):
            result = app.invoke(state)
    except Exception as exc:
        console.print(f"This question failed: {exc}", style="bold red")
        return

    report = result.get("final_report") or result.get("report") or "No report was produced."
    console.print(Panel(Text(str(report)), title="ARGUS results", border_style="cyan", expand=False))


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Ask ARGUS questions about current news and government notices."
    )
    parser.add_argument("question", nargs="?", help="ask one question and exit")
    parser.add_argument(
        "--mode",
        choices=("live", "mock"),
        default=os.getenv("ARGUS_MCP_MODE", "live").casefold(),
        help="use live feeds (default) or local mock fixtures",
    )
    parser.add_argument("--config", default=None, help="optional project config path")
    args = parser.parse_args(list(argv) if argv is not None else None)

    os.environ["ARGUS_MCP_MODE"] = args.mode
    if args.config:
        os.environ["ARGUS_CONFIG"] = args.config

    app = _resolve_app()
    if app is None:
        return 1

    if args.question:
        _ask(app, args.question.strip())
        return 0

    console.print(Panel.fit(
        "Ask a research question. Type [bold]exit[/bold], [bold]quit[/bold], or [bold]/quit[/bold] to leave.",
        title="ARGUS research assistant",
        border_style="bright_cyan",
    ))
    while True:
        try:
            question = console.input("\n[bold cyan]You > [/bold cyan]").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\nGoodbye.", style="cyan")
            break

        if question.casefold() in EXIT_COMMANDS:
            console.print("Goodbye.", style="cyan")
            break
        if not question:
            continue
        _ask(app, question)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

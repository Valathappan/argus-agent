"""graph/routing.py - conditional edges and the BOUNDED research loop (owner: Group 2).
 
Routers are pure functions of the state: they read it and return the name of the next
node. They never change the state. Every path they return ends at END.
"""
from future import annotations
from typing import Callable

 
from config.settings import MAX_INVESTIGATION_ITERATIONS
from graph._loader import load_callable
from graph.stub_nodes import stub_budget_remaining

 
def _budget_check() -> Callable[[dict], bool]:
    # Group 3's guardrails/budgets.py when it exists, otherwise the stub (uses settings).
    return load_callable("guardrails.budgets", "budget_remaining", stub_budget_remaining)
 
 
def route_after_input(state: dict) -> str:
    """Rejected questions skip all research and go straight to a refusal message."""
    return "analyze_query" if state.get("input_allowed", True) else "reject_request"
 
 
def route_after_gate(state: dict) -> str:
    """The evidence gate decides; the budget has the last word.
 
    * "needs_research" AND budget remains -> loop back to investigate_more
    * "needs_research" but budget exhausted -> continue (the report will state the limits)
    * "pass" / "stop_with_uncertainty"      -> continue to risk assessment
    """
    result = state.get("evidence_gate_result", "needs_research")
    if result == "needs_research":
        iterations = state.get("investigation_iterations", 0)
        # Hard stop independent of any guardrail module: the loop can never run forever.
        if iterations >= MAX_INVESTIGATION_ITERATIONS:
            return "assess_risk"
        if _budget_check()(state):
            return "investigate_more"
    return "assess_risk"
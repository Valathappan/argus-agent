"""Wire nodes and conditional edges into the LangGraph StateGraph and compile it.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (Pair A / tech lead)
  Blueprint reference : §5, §8
"""

from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph


class RoutingState(TypedDict, total=False):
    """Routing metadata carried by the graph state."""

    next_step: str


class ArgusState(TypedDict, total=False):
    """State for the ARGUS investigation workflow."""

    query: str
    routing: RoutingState
    evidence_sufficient: bool
    findings: list[str]
    claims: list[str]
    evidence: list[str]
    contradictions: list[str]
    exposure: dict[str, Any]
    risk: dict[str, Any]
    recommendation: dict[str, Any]
    report: str


def _next_step(state: ArgusState, step: str) -> dict[str, Any]:
    return {"routing": {"next_step": step}}


def query_analyzer(state: ArgusState) -> dict[str, Any]:
    return {"query": state.get("query", ""), **_next_step(state, "planner")}


def planner(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "external_discovery")


def external_discovery(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "internal_retrieval")


def internal_retrieval(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "claim_extraction")


def claim_extraction(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "verification")


def verification(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "contradiction_detection")


def contradiction_detection(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "evidence_sufficiency_gate")


def evidence_sufficiency_gate(state: ArgusState) -> dict[str, Any]:
    evidence_sufficient = bool(state.get("evidence_sufficient", False))
    next_step = "exposure_analysis" if evidence_sufficient else "react_research_loop"
    return {
        "evidence_sufficient": evidence_sufficient,
        "routing": {"next_step": next_step},
    }


def route_after_evidence_gate(state: ArgusState) -> str:
    next_step = state.get("routing", {}).get("next_step")
    if next_step in {"react_research_loop", "exposure_analysis"}:
        return next_step
    return "exposure_analysis" if state.get("evidence_sufficient") else "react_research_loop"


def react_research_loop(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "external_discovery")


def exposure_analysis(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "risk_assessment")


def risk_assessment(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "recommendation")


def recommendation(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "final_evaluation")


def final_evaluation(state: ArgusState) -> dict[str, Any]:
    return _next_step(state, "executive_report")


def executive_report(state: ArgusState) -> dict[str, Any]:
    return {"report": state.get("report", ""), "routing": {"next_step": "END"}}


def build_graph():
    """Build the ARGUS workflow graph from the §8 investigation pipeline."""

    graph = StateGraph(ArgusState)

    graph.add_node("query_analyzer", query_analyzer)
    graph.add_node("planner", planner)
    graph.add_node("external_discovery", external_discovery)
    graph.add_node("internal_retrieval", internal_retrieval)
    graph.add_node("claim_extraction", claim_extraction)
    graph.add_node("verification", verification)
    graph.add_node("contradiction_detection", contradiction_detection)
    graph.add_node("evidence_sufficiency_gate", evidence_sufficiency_gate)
    graph.add_node("react_research_loop", react_research_loop)
    graph.add_node("exposure_analysis", exposure_analysis)
    graph.add_node("risk_assessment", risk_assessment)
    graph.add_node("recommendation", recommendation)
    graph.add_node("final_evaluation", final_evaluation)
    graph.add_node("executive_report", executive_report)

    graph.add_edge(START, "query_analyzer")
    graph.add_edge("query_analyzer", "planner")
    graph.add_edge("planner", "external_discovery")
    graph.add_edge("external_discovery", "internal_retrieval")
    graph.add_edge("internal_retrieval", "claim_extraction")
    graph.add_edge("claim_extraction", "verification")
    graph.add_edge("verification", "contradiction_detection")
    graph.add_edge("contradiction_detection", "evidence_sufficiency_gate")

    graph.add_conditional_edges(
        "evidence_sufficiency_gate",
        route_after_evidence_gate,
        {
            "react_research_loop": "react_research_loop",
            "exposure_analysis": "exposure_analysis",
        },
    )

    graph.add_edge("react_research_loop", "external_discovery")
    graph.add_edge("exposure_analysis", "risk_assessment")
    graph.add_edge("risk_assessment", "recommendation")
    graph.add_edge("recommendation", "final_evaluation")
    graph.add_edge("final_evaluation", "executive_report")
    graph.add_edge("executive_report", END)

    return graph.compile()


graph = build_graph()


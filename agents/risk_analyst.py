"""
ARGUS: Guardrails, Evidence Sufficiency, Risk Scoring, and Human Approval
Python 3.10+

This is a standalone reference implementation. It does not call live MCP servers,
FAISS, or an LLM. Connect those integrations in your LangGraph nodes.
"""

from typing import Any


# -------------------- Configuration --------------------

MIN_CONFIDENCE = 0.75
MAX_INVESTIGATION_ITERATIONS = 5

RISK_WEIGHTS = {
    "impact": 0.40,
    "probability": 0.35,
    "urgency": 0.25,
}

APPROVAL_REQUIRED_ACTIONS = {
    "supplier_communication",
    "procurement_change",
    "legal_escalation",
    "external_write",
    "financial_commitment",
}


# -------------------- 1. Guardrails --------------------

def validate_claims(claims: list[dict[str, Any]]) -> list[str]:
    """Return guardrail warnings for claims with missing or conflicting evidence."""
    warnings = []

    for index, claim in enumerate(claims, start=1):
        claim_name = claim.get("claim", f"Claim {index}")

        if not str(claim.get("claim", "")).strip():
            warnings.append(f"{claim_name}: missing claim text")

        if not claim.get("sources"):
            warnings.append(f"{claim_name}: missing source provenance")

        if claim.get("contradiction", False):
            warnings.append(f"{claim_name}: unresolved contradiction")

        # Source content is untrusted data, not instructions to the agent.
        source_text = str(claim.get("source_text", "")).lower()
        suspicious_phrases = [
            "ignore previous instructions",
            "reveal system prompt",
            "bypass approval",
            "reveal credentials",
        ]
        if any(phrase in source_text for phrase in suspicious_phrases):
            warnings.append(
                f"{claim_name}: possible prompt injection in retrieved content"
            )

    return warnings


def retry_policy(attempt: int, max_attempts: int = 3) -> dict[str, Any]:
    """Bounded exponential backoff metadata for a failed MCP/RAG call."""
    if attempt >= max_attempts:
        return {
            "retry": False,
            "delay_seconds": 0,
            "fallback": "use_alternate_source_or_report_uncertainty",
        }

    return {
        "retry": True,
        "delay_seconds": min(2 ** max(0, attempt - 1), 8),
        "fallback": None,
    }


# -------------------- 2. Evidence sufficiency --------------------

def check_evidence_sufficiency(
    confidence: float,
    missing_information: list[str],
    unresolved_conflicts: list[str],
    investigation_iterations: int,
    guardrail_warnings: list[str] | None = None,
) -> dict[str, Any]:
    """Decide whether to research further or proceed with uncertainty."""
    warnings = guardrail_warnings or []

    if any("unauthorized sensitive data" in item.lower() for item in warnings):
        return {
            "sufficient": False,
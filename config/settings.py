"""Configurable runtime knobs for evidence gating, research, and retries.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (shared)
  Blueprint reference : §17, §21

Environment variables prefixed with ``ARGUS_`` can override the defaults.
The orchestration graph, rather than the language model, controls termination.
"""

import os


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


# Investigation and budget limits.
MAX_INVESTIGATION_ITERATIONS = int(os.getenv("MAX_INVESTIGATION_ITERATIONS", 3))
TOP_K_RETRIEVAL = int(os.getenv("TOP_K_RETRIEVAL", 5))
TOOL_TIMEOUT_SECONDS = int(os.getenv("TOOL_TIMEOUT_SECONDS", 10))

# Scoring weights.
RISK_WEIGHT_IMPACT = 0.4
RISK_WEIGHT_PROBABILITY = 0.4
RISK_WEIGHT_URGENCY = 0.2

# §17: evidence sufficiency gate.
CONFIDENCE_THRESHOLD = _env_float("ARGUS_CONFIDENCE_THRESHOLD", 0.75)
MAX_ITERATIONS = _env_int("ARGUS_MAX_ITERATIONS", 10)

# §21: bounded research and tool retry budgets.
RESEARCH_BUDGET = _env_int("ARGUS_RESEARCH_BUDGET", 20)
MCP_NEWS_TIMEOUT_SECONDS = _env_float("ARGUS_MCP_NEWS_TIMEOUT_SECONDS", 20.0)
MCP_MAX_RETRIES = _env_int("ARGUS_MCP_MAX_RETRIES", 3)
RETRY_BACKOFF_BASE_SECONDS = _env_float("ARGUS_RETRY_BACKOFF_BASE_SECONDS", 1.0)
RETRY_BACKOFF_MAX_SECONDS = _env_float("ARGUS_RETRY_BACKOFF_MAX_SECONDS", 8.0)

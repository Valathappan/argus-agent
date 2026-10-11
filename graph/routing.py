"""Conditional-edge functions — above all the evidence-sufficiency gate (graph, not LLM, decides when to stop).

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (Pair A / tech lead)
  Blueprint reference : §17

TODO (tomorrow):
  - Implement next_step(state) from §17: iteration cap, confidence floor,
    missing info, unresolved conflicts.
"""

# These defaults can be overridden per state with ``max_iterations`` and
# ``confidence_floor``.


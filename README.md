# ARGUS — Autonomous Risk & Global Unified Surveillance Agent

Class build for the Agentic AI cohort. ARGUS is a **governed agentic system**:
it takes an open-ended business question (e.g. "do new semiconductor export
restrictions affect us?"), investigates across live external sources and
internal knowledge, validates claims against primary sources, surfaces
contradictions, scores risk **and** confidence separately, and recommends
actions — with human approval gates for consequential steps.

This repository is the **scaffold**: every file is a stub whose top-of-file
docstring states its role, the blueprint section it implements, and the
work-stream / pair that owns it.

## Tech stack (per the blueprint)

LangGraph (orchestration) · ReAct (dynamic investigation) · FAISS RAG
(internal knowledge) · MCP (external tools) · model cascading (cost) ·
evaluators + guardrails (quality & safety).

## Layout

```
argus/
├── app.py            Entrypoint: build the graph, run one investigation
├── config/           Model registry + runtime settings (thresholds, budgets)
├── graph/            LangGraph state, graph wiring, routing, checkpoints
├── agents/           Supervisor + ReAct agents (news, internal, verify, risk, recommend, judge)
├── rag/              FAISS ingestion, retrieval, metadata-aware reranking
├── mcp/              News / government / market / company tool clients
├── models/           Claim schema + model-cascade router
├── guardrails/       Evidence gate helpers, injection defence, access control, budgets
├── evaluation/       Metrics, regression harness, benchmark datasets (seeded hard cases)
└── tests/            Unit tests (gate, claims)
```

## Work-stream → pair ownership (for tomorrow)

| Work-stream | Directories | Pair |
|---|---|---|
| Orchestration / platform | `graph/`, `models/schemas.py`, `config/settings.py` | Pair A (tech lead) |
| RAG / knowledge | `rag/` | Pair B |
| MCP / integrations | `mcp/` | Pair C |
| Agents / reasoning | `agents/` | Pair D |
| Guardrails / governance | `guardrails/` | Pair E |
| Model economics / eval | `models/cascade.py`, `config/models.py`, `evaluation/` | Pair F |

**Frozen interfaces — do not change without the tech lead:** `graph/state.py`
(`IntelligenceState`, §7), `models/schemas.py` (`Claim`, §15), and the MCP tool
signatures (§12). Everyone builds against these, so lock them first and let
other pairs work off stubs/mocks until live versions land.

## Build order (blueprint §26)

1. **Phase 1 — Foundation:** state, supervisor, FAISS ingest/retrieve, one news MCP.
2. **Phase 2 — Agentic research:** ReAct loop, structured claims, evidence gate, bounded retries.
3. **Phase 3 — Intelligence quality:** contradiction detection, credibility scoring, verification, evaluator.
4. **Phase 4 — Model economics:** tiered cascade, confidence-based escalation, cost telemetry.
5. **Phase 5 — Enterprise controls:** human approval, checkpointing, observability, injection defence.
6. **Phase 6 — Autonomous mode:** scheduled discovery, clustering, impact ranking.

For the 2-hour session, aim for a **walking skeleton** (Phases 1–2) that passes
the seeded contradiction scenario in `evaluation/datasets/`.

## Getting started

```bash
python -m venv .venv
```

Activate the environment:

```powershell
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux, use:

```bash
source .venv/bin/activate
```

Then install dependencies and run the app:

```bash
pip install -r requirements.txt
python app.py "Do new semiconductor export restrictions affect our suppliers?"
```

> The local FAISS index and its JSON chunk-metadata sidecar are written to
> `faiss_db/`. Run `python -m rag.ingest` to build or replace the index before
> querying; the embedding model is downloaded on first use.

## Running the graph test

The graph test uses mocked news and regulation responses, so it does not call live services or require API credentials. From the repository root, activate the project virtual environment and run:

```powershell
.\.venv\Scripts\Activate.ps1
python -m pytest tests/test_graph.py -v
```

If pytest is not installed in the environment, install the test extra with `python -m pip install -e ".[test]"` (or install `pytest` directly).

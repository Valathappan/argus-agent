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

```text
argus/
├── app.py            Entrypoint: build the graph, run one investigation
├── config/           Model registry + runtime settings (thresholds, budgets)
├── graph/            State, graph wiring, routing, checkpoints
├── agents/           Supervisor and research agents
├── rag/              FAISS ingestion, retrieval, metadata-aware reranking
├── mcp/              News, government, market and company tool clients
├── models/           Claim schema and model-cascade router
├── guardrails/       Evidence gate, injection defence, access control, budgets
├── evaluation/       Metrics, regression harness and benchmark datasets
└── tests/            Unit and integration tests
```

## Getting started

Create and activate a virtual environment:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux, activate it with `source .venv/bin/activate`. Then install
project dependencies and run the app:

```powershell
python -m pip install -r requirements.txt
python app.py "Do new semiconductor export restrictions affect our suppliers?"
```

## RAG data and index

The PDF input defaults to `data/pdfs` and can be overridden with
`ARGUS_PDF_DIR`. Markdown documents under `data/ARGUS_sample_knowledge_base`
are also used by the internal knowledge retrieval pipeline. Their front matter
provides supplier, product, region, type, date and version metadata.

The FAISS index and its metadata sidecar default to `faiss_db/`. Run
`python -m rag.ingest` to build or replace the PDF index; the embedding model
is downloaded on first use. `rag.retrieval.search_internal(query, top_k,
filters)` returns retrieved chunks and a reason when no sufficiently relevant
result is found.

## Running the tests

Activate the virtual environment from the repository root, then run a test
with `python -m pytest <test-file> -v -s`. The `-s` option displays progress
logs printed by tests. These focused tests are available:

```powershell
python -m pytest tests/test_graph.py -v -s
python -m pytest tests/test_rag_pipeline.py -v -s
python -m pytest tests/test_faiss_store.py -v -s
```

The graph test mocks external sources. The RAG pipeline test reads the bundled
PDFs and checks extracted text and chunk metadata. The FAISS test builds a
temporary real FAISS index using deterministic test embeddings, so it does not
download the embedding model. FAISS and NumPy must be installed to run it.


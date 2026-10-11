"""Runtime knobs: confidence threshold, MAX_ITERATIONS, research budget, retry/backoff, paths.

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
import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    llm_provider: str = os.getenv("LLM_PROVIDER", "openai").lower()
    openai_agent_model: str = os.getenv("OPENAI_AGENT_MODEL", "gpt-5.1")
    openai_guardrail_model: str = os.getenv("OPENAI_GUARDRAIL_MODEL", "gpt-5.4-nano")
    ollama_agent_model: str = os.getenv("OLLAMA_AGENT_MODEL", "gemma3:4b")
    ollama_guardrail_model: str = os.getenv("OLLAMA_GUARDRAIL_MODEL", "gemma3:4b")

    chunk_size: int = int(os.getenv("CHUNK_SIZE", "200"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "40"))
    top_k: int = int(os.getenv("TOP_K", "4"))

    pdf_dir: Path = PROJECT_ROOT / "data" / "pdfs"
    training_csv: Path = PROJECT_ROOT / "data" / "guardrail_training.csv"
    faiss_dir: Path = PROJECT_ROOT / "faiss_db"
    faiss_index_name: str = "argus_docs"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"


settings = Settings()

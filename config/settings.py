"""Configurable runtime settings for ARGUS."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")


def _env_int(name: str, default: int) -> int:
    return int(os.getenv(name, str(default)))


def _env_float(name: str, default: float) -> float:
    return float(os.getenv(name, str(default)))


def _env_int_first(names: tuple[str, ...], default: int) -> int:
    for name in names:
        value = os.getenv(name)
        if value is not None:
            return int(value)
    return default


@dataclass(frozen=True)
class Settings:
    llm_provider: str
    openai_agent_model: str
    openai_guardrail_model: str
    ollama_agent_model: str
    ollama_guardrail_model: str
    pdf_dir: Path
    training_csv: Path
    chunk_size: int
    chunk_overlap: int
    top_k: int
    embedding_model: str
    faiss_dir: Path
    faiss_index_name: str


settings = Settings(
    llm_provider=os.getenv("LLM_PROVIDER", "openai").lower(),
    openai_agent_model=os.getenv("OPENAI_AGENT_MODEL", "gpt-5.1"),
    openai_guardrail_model=os.getenv("OPENAI_GUARDRAIL_MODEL", "gpt-5.4-nano"),
    ollama_agent_model=os.getenv("OLLAMA_AGENT_MODEL", "gemma3:4b"),
    ollama_guardrail_model=os.getenv("OLLAMA_GUARDRAIL_MODEL", "gemma3:4b"),
    pdf_dir=Path(os.getenv("ARGUS_PDF_DIR", str(PROJECT_ROOT / "data" / "pdfs"))),
    training_csv=Path(
        os.getenv(
            "ARGUS_TRAINING_CSV",
            str(PROJECT_ROOT / "Data" / "guardrail_training.csv"),
        )
    ),
    chunk_size=_env_int("CHUNK_SIZE", 200),
    chunk_overlap=_env_int("CHUNK_OVERLAP", 40),
    top_k=_env_int("TOP_K", _env_int("TOP_K_RETRIEVAL", 4)),
    embedding_model=os.getenv(
        "ARGUS_EMBEDDING_MODEL",
        "sentence-transformers/all-MiniLM-L6-v2",
    ),
    faiss_dir=Path(os.getenv("ARGUS_FAISS_DIR", str(PROJECT_ROOT / "Data" / "index"))),
    faiss_index_name=os.getenv("ARGUS_FAISS_INDEX_NAME", "argus"),
)

# Module-level values are kept for orchestration modules that import constants.
CONFIDENCE_THRESHOLD = _env_float("ARGUS_CONFIDENCE_THRESHOLD", 0.75)
# Keep one canonical research limit while accepting both branch naming conventions.
MAX_INVESTIGATION_ITERATIONS = _env_int_first(
    ("ARGUS_MAX_ITERATIONS", "MAX_INVESTIGATION_ITERATIONS", "MAX_ITERATIONS"),
    10,
)
MAX_ITERATIONS = MAX_INVESTIGATION_ITERATIONS
TOP_K_RETRIEVAL = settings.top_k
TOOL_TIMEOUT_SECONDS = _env_int("TOOL_TIMEOUT_SECONDS", 10)
RESEARCH_BUDGET = _env_int("ARGUS_RESEARCH_BUDGET", 20)
MCP_NEWS_TIMEOUT_SECONDS = _env_float("ARGUS_MCP_NEWS_TIMEOUT_SECONDS", 20.0)
MCP_MAX_RETRIES = _env_int("ARGUS_MCP_MAX_RETRIES", 3)
RETRY_BACKOFF_BASE_SECONDS = _env_float("ARGUS_RETRY_BACKOFF_BASE_SECONDS", 1.0)
RETRY_BACKOFF_MAX_SECONDS = _env_float("ARGUS_RETRY_BACKOFF_MAX_SECONDS", 8.0)
RISK_WEIGHT_IMPACT = _env_float("ARGUS_RISK_WEIGHT_IMPACT", 0.4)
RISK_WEIGHT_PROBABILITY = _env_float("ARGUS_RISK_WEIGHT_PROBABILITY", 0.4)
RISK_WEIGHT_URGENCY = _env_float("ARGUS_RISK_WEIGHT_URGENCY", 0.2)

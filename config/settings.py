"""Runtime knobs: confidence threshold, MAX_ITERATIONS, research budget, retry/backoff, paths.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (shared)
  Blueprint reference : §17, §21

TODO (tomorrow):
  - Centralise every tunable number the blueprint says must be
    configurable (gate thresholds, budgets).
"""
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

    pdf_dir: Path = PROJECT_ROOT / "Data" / "pdfs"
    knowledge_base_dir: Path = PROJECT_ROOT / "Data" / "ARGUS_sample_knowledge_base"
    training_csv: Path = PROJECT_ROOT / "data" / "guardrail_training.csv"
    faiss_dir: Path = PROJECT_ROOT / "faiss_db"
    faiss_index_name: str = "argus_docs"
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    retrieval_min_score: float = float(os.getenv("RETRIEVAL_MIN_SCORE", "0.25"))


settings = Settings()

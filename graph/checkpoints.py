"""Checkpointer setup so runs are resumable and auditable.

ARGUS - Autonomous Risk & Global Unified Surveillance Agent (class build).

  Work-stream / owner : Orchestration (Pair A / tech lead)
  Blueprint reference : §21, §23

TODO (tomorrow):
  - Configure a LangGraph checkpointer (memory/sqlite) keyed by
    investigation id.
"""
from __future__ import annotations
 
import json
import os
import re
import time
from pathlib import Path
from typing import Any, Callable, Optional
 
from graph.state import apply_update
 
DEFAULT_DIR = os.getenv("ARGUS_CHECKPOINT_DIR", "checkpoints")
 
 
# --------------------------------------------------------------------------- #
# 1. LangGraph-native persistence
# --------------------------------------------------------------------------- #
def thread_config(thread_id: str, recursion_limit: Optional[int] = None) -> dict:
    """Config for ``invoke`` so LangGraph files all checkpoints of one run under ``thread_id``."""
    config: dict[str, Any] = {"configurable": {"thread_id": thread_id}}
    if recursion_limit is not None:
        config["recursion_limit"] = recursion_limit
    return config
 
 
def make_checkpointer(backend: str = "memory", sqlite_path: str = "checkpoints/argus.sqlite"):
    """Return a LangGraph checkpointer, or None when persistence is off / unavailable.
 
    backend: "none" | "memory" (lost when the process ends) | "sqlite" (survives restarts).
    Needs the real packages: ``langgraph`` (memory) and ``langgraph-checkpoint-sqlite`` (sqlite).
    """
    backend = backend.lower()
    if backend == "none":
        return None
    if backend == "memory":
        try:
            from langgraph.checkpoint.memory import MemorySaver
        except ModuleNotFoundError:
            return None
        return MemorySaver()
    if backend == "sqlite":
        try:
            import sqlite3
            from langgraph.checkpoint.sqlite import SqliteSaver
        except ModuleNotFoundError:
            return None
        Path(sqlite_path).parent.mkdir(parents=True, exist_ok=True)
        return SqliteSaver(sqlite3.connect(sqlite_path, check_same_thread=False))
    raise ValueError(f"unknown checkpoint backend: {backend!r}")
 
 
# --------------------------------------------------------------------------- #
# 2. JSON snapshots (audit trail + resume)
# --------------------------------------------------------------------------- #
_SAFE = re.compile(r"[^A-Za-z0-9_.-]")
 
 
def _safe(name: str) -> str:
    return _SAFE.sub("_", name) or "run"
 
 
class JsonCheckpointStore:
    """One folder per run, one JSON file per completed node, plus ``latest.json``."""
 
    def __init__(self, root: str = DEFAULT_DIR):
        self.root = Path(root)
 
    # ---- writing -----------------------------------------------------------------------
    def _run_dir(self, run_id: str) -> Path:
        return self.root / _safe(run_id)
 
    def save(self, run_id: str, node: str, state: dict, update_keys: Optional[list[str]] = None) -> Path:
        run_dir = self._run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=True)
        step = len(self.history(run_id)) + 1
        record = {"run_id": run_id, "step": step, "node": node, "saved_at": time.time(),
                  "update_keys": update_keys or [], "state": state}
        path = run_dir / f"step_{step:03d}_{_safe(node)}.json"
        self._atomic_write(path, record)
        self._atomic_write(run_dir / "latest.json", record)
        return path
 
    @staticmethod
    def _atomic_write(path: Path, record: dict) -> None:
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        os.replace(tmp, path)        # a crash never leaves a half-written checkpoint
 
    # ---- reading -----------------------------------------------------------------------
    def history(self, run_id: str) -> list[dict]:
        run_dir = self._run_dir(run_id)
        if not run_dir.exists():
            return []
        files = sorted(run_dir.glob("step_*.json"))
        return [json.loads(f.read_text(encoding="utf-8")) for f in files]
 
    def latest(self, run_id: str) -> Optional[dict]:
        path = self._run_dir(run_id) / "latest.json"
        return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None
 
    def list_runs(self) -> list[str]:
        return sorted(p.name for p in self.root.iterdir() if p.is_dir()) if self.root.exists() else []
 
    def clear(self, run_id: str) -> None:
        run_dir = self._run_dir(run_id)
        if run_dir.exists():
            for f in run_dir.iterdir():
                f.unlink()
            run_dir.rmdir()
 
 
def checkpointed(node_name: str, fn: Callable[[dict], dict], store: JsonCheckpointStore,
                 run_id: str) -> Callable[[dict], dict]:
    """Wrap a node so the state AFTER it ran is saved. The node's own return value is unchanged.
 
    If the node raises, nothing is saved for it, so the last snapshot is the last GOOD state.
    """
    def wrapper(state: dict) -> dict:
        update = fn(state) or {}
        store.save(run_id, node_name, apply_update(state, update), sorted(update))
        return update
    return wrapper
 
 
def resume_point(store: JsonCheckpointStore, run_id: str) -> Optional[tuple[dict, str]]:
    """Return (state, last_completed_node) for a run, or None if it has no checkpoints."""
    record = store.latest(run_id)
    return (record["state"], record["node"]) if record else None
 
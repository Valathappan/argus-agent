"""Offline integration test for FAISS persistence and vector search.

Run from the repository root with:
    python -m pytest tests/test_faiss_store.py -v -s

Uses real FAISS and deterministic test vectors; it does not download an embedding model.
"""

import numpy as np

from rag import faiss_store
from rag.models import Chunk


class TinyEmbeddingModel:
    """Map alpha queries and documents to one vector, all others to another."""

    def get_sentence_embedding_dimension(self):
        return 2

    def encode(self, texts, convert_to_numpy=True, normalize_embeddings=True):
        vectors = [
            [1.0, 0.0] if "alpha" in text.casefold() else [0.0, 1.0]
            for text in texts
        ]
        return np.asarray(vectors, dtype=np.float32)


def test_faiss_store_persists_and_returns_nearest_chunk(tmp_path, monkeypatch):
    index_file = tmp_path / "test.faiss"
    metadata_file = tmp_path / "test.json"
    monkeypatch.setattr(faiss_store, "_index_path", lambda: index_file)
    monkeypatch.setattr(faiss_store, "_metadata_path", lambda: metadata_file)
    monkeypatch.setattr(faiss_store, "_get_embedding_model", lambda: TinyEmbeddingModel())
    monkeypatch.setattr(faiss_store, "_index", None)
    monkeypatch.setattr(faiss_store, "_indexed_chunks", None)

    chunks = [
        Chunk(id="alpha-p1-c0", text="alpha supplier evidence", source="alpha.pdf", page=1),
        Chunk(id="beta-p2-c0", text="beta market evidence", source="beta.pdf", page=2),
    ]
    stored = faiss_store.store_chunks(chunks)
    print(f"\n[FAISS] Stored chunks: {stored}")
    print(f"[FAISS] Index created: {index_file.exists()} ({index_file})")
    print(f"[FAISS] Metadata created: {metadata_file.exists()} ({metadata_file})")
    assert stored == 2
    assert index_file.is_file()
    assert metadata_file.is_file()

    # Clear the in-memory objects so query_index must load the persisted files.
    faiss_store._index = None
    faiss_store._indexed_chunks = None
    matches = faiss_store.query_index("alpha lookup", top_k=2)

    print("[FAISS] Search query: alpha lookup")
    for rank, (match, score) in enumerate(matches, start=1):
        print(f"  {rank}. {match['metadata']['source']} page {match['metadata']['page']} (score={score:.3f})")
        print(f"     {match['text']}")

    assert len(matches) == 2
    best_chunk, best_score = matches[0]
    assert best_chunk["text"] == "alpha supplier evidence"
    assert best_chunk["metadata"] == {"source": "alpha.pdf", "page": 1}
    assert best_score > matches[1][1]
    assert best_score == 1.0

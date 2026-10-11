import json
import logging
from pathlib import Path
from typing import Any, TypedDict

from config.settings import settings
from rag.models import Chunk


class IndexedChunk(TypedDict):
    text: str
    metadata: dict[str, Any]


logger = logging.getLogger(__name__)


_embedding_model: Any | None = None
_index: Any | None = None
_indexed_chunks: list[IndexedChunk] | None = None


def _get_embedding_model() -> Any:
    global _embedding_model
    if _embedding_model is None:
        from sentence_transformers import SentenceTransformer

        _embedding_model = SentenceTransformer(settings.embedding_model)
    return _embedding_model


def _index_path() -> Path:
    return settings.faiss_dir / f"{settings.faiss_index_name}.faiss"


def _metadata_path() -> Path:
    return settings.faiss_dir / f"{settings.faiss_index_name}.json"


def store_chunks(chunks: list[Chunk]) -> int:
    """Embed chunks and persist a FAISS index with aligned JSON metadata."""
    import faiss
    import numpy as np

    model = _get_embedding_model()
    dimension = model.get_sentence_embedding_dimension()
    if dimension is None:
        raise RuntimeError("The embedding model did not provide an embedding dimension.")

    index = faiss.IndexFlatIP(dimension)
    if chunks:
        embeddings = np.asarray(
            model.encode(
                [chunk.text for chunk in chunks],
                convert_to_numpy=True,
                normalize_embeddings=True,
            ),
            dtype=np.float32,
        )
        index.add(embeddings)

    indexed_chunks = [
        IndexedChunk(
            text=chunk.text,
            metadata={
                **chunk.metadata,
                "source": chunk.source,
                "page": chunk.page,
            },
        )
        for chunk in chunks
    ]

    settings.faiss_dir.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(_index_path()))
    _metadata_path().write_text(
        json.dumps(indexed_chunks, ensure_ascii=False),
        encoding="utf-8",
    )

    global _index, _indexed_chunks
    _index = index
    _indexed_chunks = indexed_chunks
    return len(indexed_chunks)


def load_index() -> tuple[Any, list[IndexedChunk]]:
    """Load the persisted FAISS index and its aligned chunk metadata."""
    global _index, _indexed_chunks
    if _index is None or _indexed_chunks is None:
        index_path = _index_path()
        metadata_path = _metadata_path()
        if not index_path.is_file() or not metadata_path.is_file():
            raise FileNotFoundError(
                f"FAISS index not found in {settings.faiss_dir}; run `python -m rag.ingest` first."
            )

        import faiss

        _index = faiss.read_index(str(index_path))
        _indexed_chunks = json.loads(metadata_path.read_text(encoding="utf-8"))
        if _index.ntotal != len(_indexed_chunks):
            _index = None
            _indexed_chunks = None
            raise ValueError("FAISS index and chunk metadata contain different numbers of entries.")

    return _index, _indexed_chunks


def query_index(query: str, top_k: int | None) -> list[tuple[IndexedChunk, float]]:
    """Return the nearest chunks and cosine-similarity scores."""
    if top_k is not None and top_k <= 0:
        return []

    import numpy as np

    index, indexed_chunks = load_index()
    if index.ntotal == 0:
        return []

    model = _get_embedding_model()
    query_embedding = np.asarray(
        model.encode([query], convert_to_numpy=True, normalize_embeddings=True),
        dtype=np.float32,
    )
    result_count = index.ntotal if top_k is None else min(top_k, index.ntotal)
    scores, positions = index.search(query_embedding, result_count)
    return [
        (indexed_chunks[int(position)], float(score))
        for position, score in zip(positions[0], scores[0])
        if position >= 0
    ]

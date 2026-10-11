from rag.models import Chunk
from rag.faiss_store import store_chunks as store_faiss_chunks


def store_chunks(chunks: list[Chunk]) -> int:
    """Embed the chunks and replace the persisted FAISS index."""
    return store_faiss_chunks(chunks)

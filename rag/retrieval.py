from rag.models import RetrievedChunk
from rag.faiss_store import query_index


def retrieve(query: str, top_k: int) -> list[RetrievedChunk]:
    """Return the `top_k` closest chunks in the standard retrieved-chunk shape."""
    metadata_fields = ("doc_type", "supplier", "product", "region", "doc_date", "version")
    retrieved = []
    for chunk, score in query_index(query, top_k):
        meta = chunk["metadata"]
        retrieved.append(
            RetrievedChunk(
                text=chunk["text"],
                source_id=f"{meta['source']}#p{meta['page']}",
                metadata={field: meta.get(field) for field in metadata_fields},
                score=score,
            )
        )
    return retrieved

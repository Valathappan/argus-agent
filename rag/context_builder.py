from rag.models import RetrievedChunk


def build_context(chunks: list[RetrievedChunk]) -> str:
    """Join the retrieved chunks into one numbered block of text the LLM can cite from."""
    sections = [
        f"[{number}] Source: {chunk['source_id']}\n{chunk['text']}"
        for number, chunk in enumerate(chunks, start=1)
    ]
    return "\n\n".join(sections)

import logging
from datetime import date
from typing import Any

from config.settings import settings
from rag.faiss_store import query_index
from rag.models import RetrievedChunk
from rag.models import SearchResponse
from rag.reranker import rerank

logger = logging.getLogger(__name__)

_FILTER_ALIASES = {
    "document_type": "doc_type",
    "date": "doc_date",
    "effective_date": "doc_date",
}
_RESULT_METADATA_FIELDS = (
    "doc_type",
    "supplier",
    "product",
    "region",
    "doc_date",
    "version",
)


def _as_values(value: Any) -> list[object]:
    return value if isinstance(value, list) else [value]


def _parse_iso_date(value: object) -> date:
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError as error:
        raise ValueError(f"Date filters must use ISO format (YYYY-MM-DD): {value}") from error


def _validate_filters(filters: dict[str, Any] | None) -> None:
    if filters is None:
        return
    allowed = {"supplier", "product", "region", "doc_type", "doc_date"}
    for requested_key, criterion in filters.items():
        key = _FILTER_ALIASES.get(requested_key, requested_key)
        if key not in allowed:
            raise ValueError(f"Unsupported retrieval filter: {requested_key}")
        if key != "doc_date":
            continue
        if isinstance(criterion, dict):
            start = criterion.get("from", criterion.get("start"))
            end = criterion.get("to", criterion.get("end"))
            if start is None and end is None:
                raise ValueError("A date range filter must include 'from'/'to' or 'start'/'end'.")
            if start is not None:
                _parse_iso_date(start)
            if end is not None:
                _parse_iso_date(end)
        else:
            _parse_iso_date(criterion)


def _matches_date(value: object, criterion: object) -> bool:
    if isinstance(criterion, dict):
        start = criterion.get("from", criterion.get("start"))
        end = criterion.get("to", criterion.get("end"))
        parsed_value = _parse_iso_date(value) if value else None
        if parsed_value is None:
            return False
        return (
            (start is None or parsed_value >= _parse_iso_date(start))
            and (end is None or parsed_value <= _parse_iso_date(end))
        )

    return str(value).casefold() == str(criterion).casefold()


def _matches_filters(metadata: dict[str, Any], filters: dict[str, Any]) -> bool:
    for requested_key, criterion in filters.items():
        key = _FILTER_ALIASES.get(requested_key, requested_key)
        if key not in {"supplier", "product", "region", "doc_type", "doc_date"}:
            raise ValueError(f"Unsupported retrieval filter: {requested_key}")

        actual = metadata.get(key)
        if key == "doc_date":
            if not _matches_date(actual, criterion):
                return False
            continue

        requested_values = [str(value).casefold() for value in _as_values(criterion)]
        actual_values = [str(value).casefold() for value in _as_values(actual)] if actual is not None else []
        if not any(value in actual_values for value in requested_values):
            return False

    return True


def _to_retrieved_chunk(chunk: dict[str, Any], score: float) -> RetrievedChunk:
    metadata = chunk["metadata"]
    return RetrievedChunk(
        text=chunk["text"],
        source_id=f"{metadata['source']}#p{metadata['page']}",
        metadata={field: metadata.get(field) for field in _RESULT_METADATA_FIELDS},
        score=score,
    )


def search_internal(
    query: str,
    top_k: int,
    filters: dict[str, Any] | None = None,
) -> SearchResponse:
    """Search internal documents, optionally filter metadata, and explain empty results."""
    if top_k < 0:
        raise ValueError("top_k must be zero or greater.")
    _validate_filters(filters)
    if not query.strip():
        return {"results": [], "reason": "The search query is empty."}
    if top_k == 0:
        return {"results": [], "reason": "top_k is zero, so no results were requested."}

    candidate_pairs = [
        (_to_retrieved_chunk(chunk, score), chunk["metadata"])
        for chunk, score in query_index(query, None)
        if filters is None or _matches_filters(chunk["metadata"], filters)
    ]
    if not candidate_pairs:
        reason = (
            "No indexed chunks matched the supplied metadata filters."
            if filters
            else "The internal knowledge index contains no chunks."
        )
        return {"results": [], "reason": reason}

    minimum_score = settings.retrieval_min_score
    candidate_pairs = [
        (chunk, metadata)
        for chunk, metadata in candidate_pairs
        if chunk["score"] >= minimum_score
    ]
    if not candidate_pairs:
        return {
            "results": [],
            "reason": f"No relevant chunks met the minimum similarity score ({minimum_score:.2f}).",
        }

    try:
        candidates = rerank(
            [chunk for chunk, _ in candidate_pairs],
            [metadata for _, metadata in candidate_pairs],
        )
    except Exception:
        logger.warning("Reranking failed; returning the basic similarity ranking.", exc_info=True)
        candidates = [chunk for chunk, _ in candidate_pairs]

    return {"results": candidates[:top_k], "reason": None}


def retrieve(query: str, top_k: int) -> list[RetrievedChunk]:
    """Backward-compatible list-only wrapper; use search_internal for empty-result reasons."""
    return search_internal(query, top_k)["results"]

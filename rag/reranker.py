import re
from datetime import date, datetime
from typing import Any, Callable

from rag.models import RetrievedChunk


def _version(value: object) -> tuple[int, ...] | None:
    if not isinstance(value, str):
        return None
    numbers = re.findall(r"\d+", value)
    return tuple(int(number) for number in numbers) if numbers else None


def _date(value: object) -> date | None:
    if not isinstance(value, str):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def _normalized_ranks(
    values: list[object],
    parser: Callable[[object], Any | None],
) -> list[float]:
    parsed = [parser(value) for value in values]
    available = [value for value in parsed if value is not None]
    if not available:
        return [0.0] * len(values)

    ordered = sorted(set(available))
    if len(ordered) == 1:
        return [1.0 if value is not None else 0.0 for value in parsed]
    positions = {value: position for position, value in enumerate(ordered)}
    return [
        positions[value] / (len(ordered) - 1) if value is not None else 0.0
        for value in parsed
    ]


def rerank(
    chunks: list[RetrievedChunk],
    source_metadata: list[dict[str, Any]] | None = None,
) -> list[RetrievedChunk]:
    """Slightly favor newer, higher-version, active documents without replacing relevance."""
    ranking_metadata = source_metadata or [chunk["metadata"] for chunk in chunks]
    if len(ranking_metadata) != len(chunks):
        raise ValueError("Each chunk must have matching reranking metadata.")

    versions = _normalized_ranks(
        [metadata.get("version") for metadata in ranking_metadata],
        _version,
    )
    dates = _normalized_ranks(
        [
            metadata.get("doc_date") or metadata.get("effective_date")
            for metadata in ranking_metadata
        ],
        _date,
    )

    ranked = []
    for position, (chunk, metadata, version_rank, date_rank) in enumerate(
        zip(chunks, ranking_metadata, versions, dates)
    ):
        status = str(metadata.get("status", "")).casefold()
        expiry = _date(metadata.get("expiry_date"))
        expired = expiry is not None and expiry < datetime.now().date()
        status_bonus = (
            0.03
            if status == "active" and not expired
            else -0.05
            if status == "expired" or expired
            else 0.0
        )
        rerank_score = (
            chunk["score"]
            + 0.03 * version_rank
            + 0.03 * date_rank
            + status_bonus
        )
        ranked.append((rerank_score, position, chunk))

    ranked.sort(key=lambda entry: (-entry[0], entry[1]))
    return [chunk for _, _, chunk in ranked]

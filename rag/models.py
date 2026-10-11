from dataclasses import dataclass, field
from typing import Any, TypedDict


@dataclass(frozen=True)
class Page:
    text: str
    source: str
    page: int
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str
    page: int
    metadata: dict[str, Any] = field(default_factory=dict)


class RetrievedChunk(TypedDict):
    text: str
    source_id: str
    metadata: dict[str, str | list[str] | None]
    score: float


class SearchResponse(TypedDict):
    results: list[RetrievedChunk]
    reason: str | None

from dataclasses import dataclass
from typing import TypedDict


@dataclass(frozen=True)
class Page:
    text: str
    source: str
    page: int


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    source: str
    page: int


class RetrievedChunk(TypedDict):
    text: str
    source_id: str
    metadata: dict[str, str | None]
    score: float

"""Find internal evidence and attribute retrieved sources to affected suppliers/products."""

from typing import Any

from config.settings import settings
from rag.retrieval import search_internal


def _names(value: Any) -> list[str]:
    if isinstance(value, str):
        return [part.strip() for part in value.split(";") if part.strip()]
    if isinstance(value, list):
        return [str(part).strip() for part in value if str(part).strip()]
    return []


def _impacted_entities(documents: list[dict[str, Any]], field: str) -> list[dict[str, Any]]:
    entities: dict[str, dict[str, Any]] = {}
    for document in documents:
        for name in _names(document["metadata"].get(field)):
            key = name.casefold()
            entity = entities.setdefault(key, {"name": name, "source_ids": []})
            if document["source_id"] not in entity["source_ids"]:
                entity["source_ids"].append(document["source_id"])
    return list(entities.values())


def analyze_internal(state: dict[str, Any]) -> dict[str, Any]:
    """Return the graph-state updates produced by internal document retrieval."""
    query = str(state.get("user_query", "")).strip()
    response = search_internal(query, settings.top_k)
    documents = response["results"]

    updates: dict[str, Any] = {
        "internal_documents": documents,
        "impacted_suppliers": _impacted_entities(documents, "supplier"),
        "impacted_products": _impacted_entities(documents, "product"),
    }
    if response["reason"]:
        updates["missing_information"] = [
            *state.get("missing_information", []),
            response["reason"],
        ]
    return updates

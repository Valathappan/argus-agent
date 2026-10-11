"""Turn an executive question into an objective, entities, and evidence needs."""

from __future__ import annotations

import re
from typing import Any


_ENTITY_PATTERN = re.compile(r"\b[A-Z][A-Za-z0-9&.'-]*(?:\s+[A-Z][A-Za-z0-9&.'-]*)*")
_NON_ENTITIES = {
  "a", "an", "and", "are", "can", "does", "how", "i", "is", "our", "the", "this", "we", "what", "when", "where", "which", "will", "would",
}


def _extract_entities(query: str, existing: list[str]) -> list[str]:
  entities = list(existing)
  seen = {entity.casefold() for entity in entities}
  for match in _ENTITY_PATTERN.finditer(query):
    words = match.group(0).split()
    while words and words[0].casefold() in _NON_ENTITIES:
      words.pop(0)
    entity = " ".join(words).strip()
    if not entity or entity.casefold() in seen:
      continue
    seen.add(entity.casefold())
    entities.append(entity)
  return entities


def _evidence_needs(query: str) -> list[str]:
  normalized = query.casefold()
  needs = ["source provenance and independent corroboration"]

  if re.search(r"regulat|export|sanction|restriction|\bban\b|\blaw\b|\brule\b", normalized):
    needs.append("current official or regulatory sources and effective dates")
  else:
    needs.append("relevant current external sources and publication dates")

  if re.search(r"affect|impact|expos|supplier|product|company|our", normalized):
    needs.append("internal company, supplier, and product exposure records")
  else:
    needs.append("internal context relevant to the question")

  needs.append("conflicting claims and any unresolved uncertainty")
  return needs


def analyze_query(state: dict[str, Any]) -> dict[str, Any]:
  """Analyze the query deterministically and return supervisor-owned fields."""
  query = str(state.get("user_query", "")).strip()
  existing_entities = state.get("entities", [])
  if not isinstance(existing_entities, list):
    existing_entities = []

  return {
    "investigation_objective": query,
    "entities": _extract_entities(query, existing_entities),
    "evidence_needed": _evidence_needs(query),
  }

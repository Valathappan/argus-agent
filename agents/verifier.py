"""Extract sourced claims and report disagreements without forcing a resolution."""

from __future__ import annotations

import re
from typing import Any


_DATE_PATTERN = re.compile(
  r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
  r"immediate(?:ly)?|effective\s+(?:immediately|on\s+\w+\s+\d{1,2},?\s+\d{4}))\b",
  re.IGNORECASE,
)
_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9])")
_AUTHORITY_RANK = {"unknown": 0, "secondary": 1, "primary": 2}


def _evidence_items(value: Any) -> list[dict[str, Any]]:
  if isinstance(value, dict):
    items = value.get("items")
    if isinstance(items, list):
      return [item for item in items if isinstance(item, dict)]
    return [value]
  if isinstance(value, list):
    return [item for item in value if isinstance(item, dict)]
  return []


def _source_ids(record: dict[str, Any]) -> list[str]:
  supplied = record.get("source_ids")
  if isinstance(supplied, list):
    return list(dict.fromkeys(str(value).strip() for value in supplied if str(value).strip()))
  for key in ("source_id", "url", "source", "id"):
    value = record.get(key)
    if value:
      return [str(value).strip()]
  return []


def _authority(record: dict[str, Any], collection: str) -> str:
  value = str(record.get("source_authority", "")).casefold()
  if value in _AUTHORITY_RANK:
    return value
  if record.get("primary_source") is True or record.get("official") is True:
    return "primary"
  source_type = str(record.get("source_type", "")).casefold()
  source_name = str(record.get("source", "")).casefold()
  if collection == "government_evidence" or source_type in {"government", "regulatory", "official"}:
    return "primary"
  if any(token in source_name for token in ("government", "regulator", "official", "gov_notice")):
    return "primary"
  if collection in {"news_articles", "market_evidence"} or source_type in {"news", "market"}:
    return "secondary"
  return "unknown"


def _claim_type(record: dict[str, Any], text: str) -> str:
  explicit = record.get("claim_type", record.get("field", record.get("attribute")))
  if explicit:
    return str(explicit).casefold()
  lowered = text.casefold()
  if any(word in lowered for word in ("effective date", "takes effect", "effective on", "starts on", "deadline")):
    return "effective_date"
  if any(word in lowered for word in ("scope", "applies to", "covers", "categories", "includes")):
    return "scope"
  if any(word in lowered for word in ("unaffected", "affected", "impact", "impacting", "exposed")):
    return "impact"
  if any(word in lowered for word in ("severity", "severe", "critical")):
    return "severity"
  return "statement"


def _sentences(text: str) -> list[str]:
  return [sentence.strip() for sentence in _SENTENCE_SPLIT.split(text.strip()) if sentence.strip()]


def _records_from_item(item: dict[str, Any], collection: str) -> list[dict[str, Any]]:
  nested_claims = item.get("claims")
  if isinstance(nested_claims, list):
    result: list[dict[str, Any]] = []
    for nested in nested_claims:
      if isinstance(nested, dict):
        result.extend(_records_from_item({**item, **nested, "claims": None}, collection))
      elif isinstance(nested, str):
        result.extend(_records_from_item({**item, "claims": None, "text": nested}, collection))
    return result

  if "claim_type" in item or ("field" in item and "value" in item):
    text = str(item.get("text") or item.get("claim") or f"{item.get('claim_type', item.get('field'))}: {item.get('value', '')}").strip()
    return [{**item, "text": text, "_collection": collection}]

  text = item.get("text") or item.get("snippet") or item.get("content") or item.get("description")
  if not isinstance(text, str):
    return []
  return [
    {**item, "text": sentence, "_collection": collection}
    for sentence in _sentences(text)
  ]


def _normalized_record(record: dict[str, Any], index: int) -> dict[str, Any] | None:
  source_ids = _source_ids(record)
  if not source_ids:
    return None

  text = re.sub(r"\s+", " ", str(record.get("text", "")).strip())
  if not text:
    return None
  claim_type = _claim_type(record, text)
  value = record.get("value")
  if value is None:
    date_match = _DATE_PATTERN.search(text)
    if claim_type == "effective_date" and date_match:
      value = date_match.group(0)
    elif claim_type == "impact":
      lowered = text.casefold()
      value = "unaffected" if "unaffected" in lowered else "affected" if "affected" in lowered else text
    else:
      value = text

  authority = _authority(record, str(record.get("_collection", "")))
  confidence = record.get("confidence")
  if not isinstance(confidence, (int, float)) or not 0.0 <= confidence <= 1.0:
    confidence = {"primary": 0.75, "secondary": 0.55, "unknown": 0.35}[authority]

  subject = str(record.get("subject", record.get("entity", ""))).strip().casefold()
  canonical_text = re.sub(r"\W+", " ", text.casefold()).strip()
  return {
    "claim_id": str(record.get("claim_id") or f"claim-{index}"),
    "text": text,
    "source_ids": source_ids,
    "source_authority": authority,
    "source_date": record.get("source_date", record.get("date")),
    "confidence": float(confidence),
    "status": "supported" if authority == "primary" else "unverified",
    "_claim_type": claim_type,
    "_value": value,
    "_subject": subject,
    "_dedupe_key": (subject, claim_type, canonical_text),
  }


def _conflict_value(record: dict[str, Any]) -> str:
  value = str(record["_value"]).strip()
  if record["_claim_type"] == "effective_date":
    match = _DATE_PATTERN.search(value)
    if match:
      return match.group(0).casefold()
  return re.sub(r"\s+", " ", value.casefold())


def verify_claims(state: dict[str, Any]) -> dict[str, Any]:
  """Extract claims from evidence, attach provenance, and flag conflicts."""
  candidates: list[dict[str, Any]] = []
  for collection in ("news_articles", "government_evidence", "market_evidence", "internal_documents"):
    for item in _evidence_items(state.get(collection, [])):
      candidates.extend(_records_from_item(item, collection))
  for item in _evidence_items(state.get("claims", [])):
    candidates.extend(_records_from_item(item, str(item.get("_collection", ""))))

  claims: list[dict[str, Any]] = []
  by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
  for index, candidate in enumerate(candidates, start=1):
    record = _normalized_record(candidate, index)
    if record is None:
      continue
    duplicate = by_key.get(record["_dedupe_key"])
    if duplicate is not None:
      duplicate["source_ids"] = list(dict.fromkeys(duplicate["source_ids"] + record["source_ids"]))
      if _AUTHORITY_RANK[record["source_authority"]] > _AUTHORITY_RANK[duplicate["source_authority"]]:
        duplicate["source_authority"] = record["source_authority"]
        duplicate["status"] = "supported" if record["source_authority"] == "primary" else "unverified"
      duplicate["confidence"] = max(duplicate["confidence"], record["confidence"])
      if not duplicate["source_date"]:
        duplicate["source_date"] = record["source_date"]
      continue
    by_key[record["_dedupe_key"]] = record
    claims.append(record)

  groups: dict[tuple[str, str], dict[str, list[dict[str, Any]]]] = {}
  for claim in claims:
    if claim["_claim_type"] == "statement":
      continue
    group_key = (claim["_subject"], claim["_claim_type"])
    value_key = _conflict_value(claim)
    groups.setdefault(group_key, {}).setdefault(value_key, []).append(claim)

  conflicts: list[dict[str, Any]] = []
  for (_, claim_type), values in groups.items():
    if len(values) < 2:
      continue
    conflicting = [claim for same_value in values.values() for claim in same_value]
    for claim in conflicting:
      claim["status"] = "contradicted"
    conflicts.append({
      "conflict_type": claim_type,
      "claim_ids": [claim["claim_id"] for claim in conflicting],
      "source_ids": list(dict.fromkeys(source_id for claim in conflicting for source_id in claim["source_ids"])),
      "values": [str(value) for value in values],
      "resolution": None,
    })

  public_claims = [
    {key: value for key, value in claim.items() if not key.startswith("_")}
    for claim in claims
  ]
  return {"claims": public_claims, "conflicting_claims": conflicts}

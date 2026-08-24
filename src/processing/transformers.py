
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any


def _coerce_bson_safe(value: Any) -> Any:

    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day, tzinfo=timezone.utc)
    if isinstance(value, dict):
        return {k: _coerce_bson_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_coerce_bson_safe(v) for v in value]
    return value


def make_bson_safe(document: dict[str, Any]) -> dict[str, Any]:
    return _coerce_bson_safe(document)


@dataclass
class DeduplicationResult:
    unique_documents: list[dict[str, Any]] = field(default_factory=list)
    duplicate_count: int = 0


def deduplicate_batch(
    documents: list[dict[str, Any]], key: str = "gkg_record_id"
) -> DeduplicationResult:
    """Remove in-batch duplicates by `key`, keeping the first occurrence.

    This handles duplicates WITHIN a single batch/run. Cross-run duplicates
    (the same GKG record collected by two different runs) are handled at the
    database level via a unique index on `gkg_record_id`
    (see src/database/collections.py and docs/mongodb.md).
    """
    seen: set[Any] = set()
    unique: list[dict[str, Any]] = []
    duplicates = 0

    for doc in documents:
        identifier = doc.get(key)
        if identifier is None:
            # Can't dedupe without an identifier; keep it and let quality
            # validation decide whether it's acceptable.
            unique.append(doc)
            continue
        if identifier in seen:
            duplicates += 1
            continue
        seen.add(identifier)
        unique.append(doc)

    return DeduplicationResult(unique_documents=unique, duplicate_count=duplicates)


def prepare_batch_for_storage(
    documents: list[dict[str, Any]], dedupe_key: str = "gkg_record_id"
) -> DeduplicationResult:
    """Convenience helper combining BSON-safety coercion + deduplication,
    in the order the pipeline needs them applied."""
    safe_documents = [make_bson_safe(doc) for doc in documents]
    return deduplicate_batch(safe_documents, key=dedupe_key)

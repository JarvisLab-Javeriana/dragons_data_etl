

from __future__ import annotations

from dataclasses import dataclass, field

import pymongo
from pymongo.database import Database


@dataclass(frozen=True)
class IndexSpec:
    keys: list[tuple[str, int]]
    unique: bool = False
    name: str | None = None


GKG_RECORDS_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("gkg_record_id", pymongo.ASCENDING)], unique=True, name="uniq_gkg_record_id"),
    IndexSpec(keys=[("document_identifier", pymongo.ASCENDING)], name="idx_document_identifier"),
    IndexSpec(keys=[("source_common_name", pymongo.ASCENDING)], name="idx_source_common_name"),
    IndexSpec(keys=[("date", pymongo.DESCENDING)], name="idx_date"),
    IndexSpec(keys=[("run_id", pymongo.ASCENDING)], name="idx_run_id"),
]

EXECUTION_METRICS_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("run_id", pymongo.ASCENDING)], unique=True, name="uniq_run_id"),
    IndexSpec(keys=[("source", pymongo.ASCENDING)], name="idx_source"),
    IndexSpec(keys=[("status", pymongo.ASCENDING)], name="idx_status"),
]


def ensure_indexes(
    database: Database,
    gkg_records_collection: str,
    execution_metrics_collection: str,
) -> None:
    gkg_collection = database[gkg_records_collection]
    for spec in GKG_RECORDS_INDEXES:
        gkg_collection.create_index(spec.keys, unique=spec.unique, name=spec.name)

    metrics_collection = database[execution_metrics_collection]
    for spec in EXECUTION_METRICS_INDEXES:
        metrics_collection.create_index(spec.keys, unique=spec.unique, name=spec.name)

from __future__ import annotations

from dataclasses import dataclass

import pymongo
from pymongo.database import Database

from src.gdelt.common.config import MongoDBConfig


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

CRAWLED_DATA_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("gkg_record_id", pymongo.ASCENDING)], unique=True, name="uniq_crawled_gkg_record_id"),
    IndexSpec(keys=[("document_identifier", pymongo.ASCENDING)], name="idx_crawled_document_identifier"),
    IndexSpec(keys=[("run_id", pymongo.ASCENDING)], name="idx_crawled_run_id"),
    IndexSpec(keys=[("status", pymongo.ASCENDING)], name="idx_crawled_status"),
]

EVENTOS_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("id", pymongo.ASCENDING)], unique=True, name="uniq_evento_id"),
    IndexSpec(keys=[("pais", pymongo.ASCENDING)], name="idx_evento_pais"),
]

QUERIES_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("id", pymongo.ASCENDING)], unique=True, name="uniq_query_id"),
    IndexSpec(keys=[("id_evento", pymongo.ASCENDING)], name="idx_query_evento"),
]

WHITELIST_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("id", pymongo.ASCENDING)], unique=True, name="uniq_whitelist_id"),
    IndexSpec(keys=[("hash", pymongo.ASCENDING)], unique=True, name="uniq_whitelist_hash"),
    IndexSpec(keys=[("id_query", pymongo.ASCENDING)], name="idx_whitelist_query"),
    IndexSpec(keys=[("id_metric", pymongo.ASCENDING)], name="idx_whitelist_metric"),
    IndexSpec(keys=[("url", pymongo.ASCENDING)], name="idx_whitelist_url"),
]

SCRAPPER_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("id", pymongo.ASCENDING)], unique=True, name="uniq_scrapper_id"),
    IndexSpec(keys=[("hash_whitelist", pymongo.ASCENDING)], unique=True, name="uniq_scrapper_hash"),
]

METRICS_INDEXES: list[IndexSpec] = [
    IndexSpec(keys=[("id", pymongo.ASCENDING)], unique=True, name="uniq_metrics_id"),
    IndexSpec(keys=[("id_query", pymongo.ASCENDING)], unique=True, name="uniq_metrics_query"),
]


def _apply_indexes(database: Database, collection_name: str, specs: list[IndexSpec]) -> None:
    collection = database[collection_name]
    for spec in specs:
        collection.create_index(spec.keys, unique=spec.unique, name=spec.name)


def ensure_indexes(
    database: Database,
    config: MongoDBConfig,
) -> None:
    _apply_indexes(database, config.gkg_records_collection, GKG_RECORDS_INDEXES)
    _apply_indexes(database, config.execution_metrics_collection, EXECUTION_METRICS_INDEXES)
    _apply_indexes(database, config.crawled_data_collection, CRAWLED_DATA_INDEXES)
    _apply_indexes(database, config.eventos_collection, EVENTOS_INDEXES)
    _apply_indexes(database, config.queries_collection, QUERIES_INDEXES)
    _apply_indexes(database, config.whitelist_collection, WHITELIST_INDEXES)
    _apply_indexes(database, config.scrapper_collection, SCRAPPER_INDEXES)
    _apply_indexes(database, config.metrics_collection, METRICS_INDEXES)

"""
Repository tests using `mongomock` so no real MongoDB instance is required.
If `mongomock` is not installed, these tests are skipped (see conftest-style
guard below) -- CI environments should install it as a dev dependency
(see pyproject.toml [project.optional-dependencies].test).
"""

from __future__ import annotations

import pytest

mongomock = pytest.importorskip("mongomock")

from src.gdelt.common.config import MongoDBConfig  # noqa: E402
from src.gdelt.database.mongodb import MongoDBConnection  # noqa: E402
from src.gdelt.database.repositories import (  # noqa: E402
    CrawledDataRepository,
    EventosRepository,
    ExecutionMetricsRepository,
    GkgRecordsRepository,
    MetricsRepository,
    QueriesRepository,
    ScrapperRepository,
    WhitelistRepository,
    initialize_database,
)
from src.gdelt.common.utils import hash_identifier  # noqa: E402


def _mongo_config(**overrides) -> MongoDBConfig:
    values = dict(
        uri="mongodb://localhost:27017",
        database="test_db",
        gkg_records_collection="gkg_records",
        execution_metrics_collection="execution_metrics",
        crawled_data_collection="crawled_data",
        eventos_collection="eventos",
        queries_collection="queries",
        whitelist_collection="whitelist",
        scrapper_collection="scrapper",
        metrics_collection="metrics",
        connect_timeout_ms=1000,
        server_selection_timeout_ms=1000,
        ordered_inserts=False,
        ensure_indexes_on_startup=True,
    )
    values.update(overrides)
    return MongoDBConfig(**values)


@pytest.fixture
def mongo_connection(monkeypatch):
    config = _mongo_config()
    connection = MongoDBConnection(config)
    # Inject a mongomock client instead of a real MongoClient.
    connection._client = mongomock.MongoClient()
    initialize_database(connection, config)
    return connection, config


def test_insert_batch_inserts_documents(mongo_connection):
    connection, config = mongo_connection
    repo = GkgRecordsRepository(connection, config)

    result = repo.insert_batch(
        [{"gkg_record_id": "a", "run_id": "run_1"}, {"gkg_record_id": "b", "run_id": "run_1"}]
    )

    assert result.attempted == 2
    assert result.inserted == 2
    assert repo.count_by_run("run_1") == 2


def test_insert_batch_counts_duplicate_key_errors(mongo_connection):
    connection, config = mongo_connection
    repo = GkgRecordsRepository(connection, config)

    repo.insert_batch([{"gkg_record_id": "dup", "run_id": "run_1"}])
    result = repo.insert_batch([{"gkg_record_id": "dup", "run_id": "run_1"}])

    assert result.duplicate_key_errors == 1
    assert result.inserted == 0


def test_execution_metrics_repository_upserts_by_run_id(mongo_connection):
    connection, config = mongo_connection
    repo = ExecutionMetricsRepository(connection, config)

    repo.save({"run_id": "run_1", "status": "running"})
    repo.save({"run_id": "run_1", "status": "success"})

    stored = repo.get_by_run_id("run_1")
    assert stored["status"] == "success"


def test_list_http_document_urls_filters_and_limits(mongo_connection):
    connection, config = mongo_connection
    repo = GkgRecordsRepository(connection, config)
    repo.insert_batch(
        [
            {"gkg_record_id": "a", "document_identifier": "https://example.com/a"},
            {"gkg_record_id": "b", "document_identifier": "not-a-url"},
            {"gkg_record_id": "c", "document_identifier": "https://example.com/c"},
        ]
    )

    urls = repo.list_http_document_urls(limit=1)

    assert len(urls) == 1
    assert urls[0]["document_identifier"].startswith("https://")


def test_crawled_data_repository_inserts_documents(mongo_connection):
    connection, config = mongo_connection
    repo = CrawledDataRepository(connection, config)
    result = repo.insert_batch(
        [
            {
                "gkg_record_id": "a",
                "document_identifier": "https://example.com/a",
                "status": "success",
                "text": "hello",
            }
        ]
    )
    assert result.inserted == 1
    assert repo.collection.count_documents({}) == 1


def test_eventos_upsert_and_get(mongo_connection):
    connection, config = mongo_connection
    repo = EventosRepository(connection, config)
    repo.upsert_many(
        [{"id": "UK-01", "pais": "United Kingdom", "evento": {"en": "Brexit"}}]
    )
    repo.upsert_many(
        [{"id": "UK-01", "pais": "United Kingdom", "evento": {"en": "Brexit updated"}}]
    )
    stored = repo.get_by_id("UK-01")
    assert stored["evento"]["en"] == "Brexit updated"
    assert len(repo.list_all()) == 1


def test_whitelist_and_metrics_and_scrapper(mongo_connection):
    connection, config = mongo_connection
    queries = QueriesRepository(connection, config)
    whitelist = WhitelistRepository(connection, config)
    metrics = MetricsRepository(connection, config)
    scrapper = ScrapperRepository(connection, config)

    queries.insert({"id": "q1", "id_evento": "UK-01", "consulta": "SELECT 1"})
    whitelist_id = "gkg-1"
    digest = hash_identifier(whitelist_id)
    result = whitelist.insert_batch(
        [
            {
                "id": whitelist_id,
                "hash": digest,
                "url": "https://example.com/a",
                "id_query": "q1",
                "id_scrapper": None,
                "id_metric": "m1",
            }
        ]
    )
    assert result.inserted == 1
    metrics.save({"id": "m1", "id_query": "q1", "query": {"rows_returned": 1}})
    scrapper.insert(
        {"id": "s_gkg-1", "hash_whitelist": digest, "contenido": {"text": "hello"}}
    )
    whitelist.set_scrapper_id(whitelist_id, "s_gkg-1")
    stored = whitelist.collection.find_one({"id": whitelist_id})
    assert stored["id_scrapper"] == "s_gkg-1"
    assert stored["id_query"] == "q1"
    assert stored["id_metric"] == "m1"

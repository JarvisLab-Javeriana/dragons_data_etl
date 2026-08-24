"""
Repository tests using `mongomock` so no real MongoDB instance is required.
If `mongomock` is not installed, these tests are skipped (see conftest-style
guard below) -- CI environments should install it as a dev dependency
(see pyproject.toml [project.optional-dependencies].test).
"""

from __future__ import annotations

import pytest

mongomock = pytest.importorskip("mongomock")

from src.common.config import MongoDBConfig  # noqa: E402
from src.database.mongodb import MongoDBConnection  # noqa: E402
from src.database.repositories import (  # noqa: E402
    ExecutionMetricsRepository,
    GkgRecordsRepository,
    initialize_database,
)


@pytest.fixture
def mongo_connection(monkeypatch):
    config = MongoDBConfig(
        uri="mongodb://localhost:27017",
        database="test_db",
        gkg_records_collection="gkg_records",
        execution_metrics_collection="execution_metrics",
        connect_timeout_ms=1000,
        server_selection_timeout_ms=1000,
        ordered_inserts=False,
        ensure_indexes_on_startup=True,
    )
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

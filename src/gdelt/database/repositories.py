
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from pymongo.errors import BulkWriteError, PyMongoError

from src.gdelt.common.config import MongoDBConfig
from src.gdelt.common.exceptions import MongoDBError
from src.gdelt.database.collections import ensure_indexes
from src.gdelt.database.mongodb import MongoDBConnection

logger = logging.getLogger(__name__)


@dataclass
class InsertBatchResult:
    attempted: int = 0
    inserted: int = 0
    failed: int = 0
    duplicate_key_errors: int = 0
    errors: list[str] = field(default_factory=list)


class BaseRepository:
    def __init__(self, connection: MongoDBConnection, collection_name: str) -> None:
        self._connection = connection
        self._collection_name = collection_name

    @property
    def collection(self):
        return self._connection.database[self._collection_name]


class GkgRecordsRepository(BaseRepository):
    """Persistence for normalized GDELT GKG documents."""

    def __init__(self, connection: MongoDBConnection, config: MongoDBConfig) -> None:
        super().__init__(connection, config.gkg_records_collection)
        self._ordered = config.ordered_inserts

    def insert_batch(self, documents: list[dict[str, Any]]) -> InsertBatchResult:
        """Insert a batch of already-validated, BSON-safe documents.

        Uses `ordered=False` by default (configurable) so that a single
        duplicate-key or malformed document does not abort the whole batch
        -- individual failures are counted instead, matching the
        "documents_failed" metric in section 13 of the project spec.
        """
        result = InsertBatchResult(attempted=len(documents))
        if not documents:
            return result

        try:
            insert_result = self.collection.insert_many(
                documents, ordered=self._ordered
            )
            result.inserted = len(insert_result.inserted_ids)
            result.failed = result.attempted - result.inserted
        except BulkWriteError as exc:
            write_errors = exc.details.get("writeErrors", [])
            result.failed = len(write_errors)
            result.inserted = result.attempted - result.failed
            for err in write_errors:
                code = err.get("code")
                message = err.get("errmsg", "unknown error")
                if code == 11000:  # duplicate key
                    result.duplicate_key_errors += 1
                else:
                    result.errors.append(message)
            logger.warning(
                "Batch insert had %s failures (%s duplicate key) out of %s",
                result.failed,
                result.duplicate_key_errors,
                result.attempted,
            )
        except PyMongoError as exc:
            raise MongoDBError(f"Failed to insert batch into gkg_records: {exc}") from exc

        return result

    def count_by_run(self, run_id: str) -> int:
        return self.collection.count_documents({"run_id": run_id})


class ExecutionMetricsRepository(BaseRepository):
    """Persistence for the execution_metrics collection."""

    def __init__(self, connection: MongoDBConnection, config: MongoDBConfig) -> None:
        super().__init__(connection, config.execution_metrics_collection)

    def save(self, metrics_document: dict[str, Any]) -> None:
        try:
            self.collection.update_one(
                {"run_id": metrics_document["run_id"]},
                {"$set": metrics_document},
                upsert=True,
            )
        except PyMongoError as exc:
            raise MongoDBError(f"Failed to save execution metrics: {exc}") from exc

    def get_by_run_id(self, run_id: str) -> dict[str, Any] | None:
        return self.collection.find_one({"run_id": run_id})


def initialize_database(connection: MongoDBConnection, config: MongoDBConfig) -> None:
    """Ensure collections/indexes exist. Safe to call on every startup."""
    if config.ensure_indexes_on_startup:
        ensure_indexes(
            connection.database,
            config.gkg_records_collection,
            config.execution_metrics_collection,
        )

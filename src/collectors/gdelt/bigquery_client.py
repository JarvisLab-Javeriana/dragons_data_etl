from __future__ import annotations

import logging
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any

from google.api_core.exceptions import GoogleAPIError
from google.cloud import bigquery

from src.collectors.gdelt.query_builder import PreparedQuery
from src.common.exceptions import BigQueryError

logger = logging.getLogger(__name__)


@dataclass
class BigQueryJobMetrics:


    job_id: str | None = None
    started_at: float | None = None
    finished_at: float | None = None
    duration_seconds: float | None = None
    rows_returned: int | None = None
    bytes_processed: int | None = None
    bytes_billed: int | None = None
    slot_ms: int | None = None
    cache_hit: bool | None = None
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": self.duration_seconds,
            "rows_returned": self.rows_returned,
            "bytes_processed": self.bytes_processed,
            "bytes_billed": self.bytes_billed,
            "slot_ms": self.slot_ms,
            "cache_hit": self.cache_hit,
            "error": self.error,
        }


@dataclass
class BigQueryQueryResult:

    rows: Iterator[dict[str, Any]]
    metrics: BigQueryJobMetrics


class BigQueryGdeltClient:


    def __init__(self, client: bigquery.Client | None = None) -> None:
        # Allow dependency injection for tests; otherwise build a real client
        # lazily using Application Default Credentials
        # (GOOGLE_APPLICATION_CREDENTIALS env var -- see .env.example).
        self._client = client
        self._owns_client = client is None

    @property
    def client(self) -> bigquery.Client:
        if self._client is None:
            self._client = bigquery.Client()
        return self._client

    def close(self) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()
            self._client = None

    def estimate_bytes(self, prepared: PreparedQuery) -> int:
        job_config = bigquery.QueryJobConfig(
            query_parameters=prepared.parameters,
            dry_run=True,
            use_query_cache=False,
        )
        try:
            job = self.client.query(prepared.sql, job_config=job_config)
            return int(job.total_bytes_processed or 0)
        except GoogleAPIError as exc:
            raise BigQueryError(f"Dry-run estimation failed: {exc}") from exc

    def run_query(
        self,
        prepared: PreparedQuery,
        *,
        max_bytes_billed: int | None = None,
        page_size: int = 1000,
    ) -> BigQueryQueryResult:

        job_config = bigquery.QueryJobConfig(
            query_parameters=prepared.parameters,
            maximum_bytes_billed=max_bytes_billed,
        )

        metrics = BigQueryJobMetrics()
        started = time.monotonic()
        metrics.started_at = started

        try:
            job = self.client.query(prepared.sql, job_config=job_config)
            metrics.job_id = job.job_id

            result = job.result(page_size=page_size)  # blocks until done, but doesn't fetch all rows into memory

            finished = time.monotonic()
            metrics.finished_at = finished
            metrics.duration_seconds = finished - started
            metrics.rows_returned = result.total_rows
            metrics.bytes_processed = job.total_bytes_processed
            metrics.bytes_billed = job.total_bytes_billed
            metrics.slot_ms = job.slot_millis
            metrics.cache_hit = job.cache_hit

            logger.info(
                "BigQuery job %s finished: rows=%s bytes_processed=%s "
                "bytes_billed=%s slot_ms=%s cache_hit=%s duration=%.2fs",
                metrics.job_id,
                metrics.rows_returned,
                metrics.bytes_processed,
                metrics.bytes_billed,
                metrics.slot_ms,
                metrics.cache_hit,
                metrics.duration_seconds,
            )

            def _row_iterator() -> Iterator[dict[str, Any]]:
                for row in result:
                    yield dict(row.items())

            return BigQueryQueryResult(rows=_row_iterator(), metrics=metrics)

        except GoogleAPIError as exc:
            finished = time.monotonic()
            metrics.finished_at = finished
            metrics.duration_seconds = finished - started
            metrics.error = str(exc)
            logger.error("BigQuery job failed: %s", exc)
            raise BigQueryError(f"BigQuery query failed: {exc}") from exc

    def run_scalar_query(
        self, prepared: PreparedQuery
    ) -> tuple[list[dict[str, Any]], BigQueryJobMetrics]:
        result = self.run_query(prepared)
        rows = list(result.rows)
        return rows, result.metrics

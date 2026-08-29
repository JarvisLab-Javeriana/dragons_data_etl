
from __future__ import annotations

import logging
import time
from typing import Any

from src.gdelt.collectors.gdelt.collector import GdeltCollector
from src.gdelt.common.config import (
    GdeltSourceConfig,
    MongoDBConfig,
    PipelineConfig,
    load_gdelt_config,
    load_mongodb_config,
    load_pipeline_config,
)
from src.gdelt.common.exceptions import DragonsDataETLError, ResourceLimitError
from src.gdelt.common.utils import chunked, new_run_id, utcnow
from src.gdelt.database.mongodb import MongoDBConnection
from src.gdelt.database.repositories import (
    ExecutionMetricsRepository,
    GkgRecordsRepository,
    initialize_database,
)
from src.gdelt.monitoring import execution_logger
from src.gdelt.monitoring.metrics import ErrorInfo, ExecutionMetrics
from src.gdelt.monitoring.system_metrics import SystemMonitor
from src.gdelt.processing.normalizer import normalize_gkg_row
from src.gdelt.processing.transformers import prepare_batch_for_storage
from src.gdelt.quality.checks import run_quality_checks

logger = logging.getLogger(__name__)


class GdeltPipeline:
    """Orchestrates a single end-to-end GDELT run (test or ingestion)."""

    def __init__(
        self,
        gdelt_config: GdeltSourceConfig | None = None,
        mongodb_config: MongoDBConfig | None = None,
        pipeline_config: PipelineConfig | None = None,
    ) -> None:
        self.gdelt_config = gdelt_config or load_gdelt_config()
        self.pipeline_config = pipeline_config or load_pipeline_config()
        # MongoDB config/connection is only required in ingestion mode, but
        # we still allow it to be loaded for metrics persistence in test
        # mode if the caller wants that (save_metrics=true).
        self._mongodb_config = mongodb_config

    def run(self) -> dict[str, Any]:
        run_id = new_run_id(self.pipeline_config.run_id_prefix)
        metrics = ExecutionMetrics(run_id=run_id, source="gdelt", source_type="gkg")
        metrics.parameters = {
            "keywords": self.gdelt_config.keywords,
            "date_range": {
                "start": str(self.gdelt_config.date_range.start),
                "end": str(self.gdelt_config.date_range.end),
            },
            "max_rows": self.gdelt_config.max_rows,
            "batch_size": self.gdelt_config.batch_size,
            "mode": self.gdelt_config.mode,
        }

        monitor = SystemMonitor(
            interval_seconds=self.pipeline_config.system_monitor_interval_seconds
        )
        monitor.start()

        mongo_connection: MongoDBConnection | None = None
        metrics_repository: ExecutionMetricsRepository | None = None
        gkg_repository: GkgRecordsRepository | None = None
        collector: GdeltCollector | None = None

        try:
            mongo_connection, metrics_repository, gkg_repository = self._maybe_connect_mongodb()

            collector = GdeltCollector(self.gdelt_config)

            logger.info(
                "Starting GDELT run %s (mode=%s, keywords=%s, range=%s..%s)",
                run_id,
                self.gdelt_config.mode,
                self.gdelt_config.keywords,
                self.gdelt_config.date_range.start,
                self.gdelt_config.date_range.end,
            )

            collection_result = collector.collect_articles()
            bq_metrics = collection_result.metrics
            metrics.query.job_id = bq_metrics.job_id
            metrics.query.query_description = "GDELT GKG extraction"
            metrics.query.started_at = bq_metrics.started_at
            metrics.query.finished_at = bq_metrics.finished_at
            metrics.query.duration_seconds = bq_metrics.duration_seconds
            metrics.query.rows_returned = bq_metrics.rows_returned
            metrics.query.bytes_processed = bq_metrics.bytes_processed
            metrics.query.bytes_billed = bq_metrics.bytes_billed
            metrics.query.slot_ms = bq_metrics.slot_ms
            metrics.query.cache_hit = bq_metrics.cache_hit

            self._process_and_store(
                rows=collection_result.rows,
                run_id=run_id,
                metrics=metrics,
                gkg_repository=gkg_repository,
                monitor=monitor,
            )

            if gkg_repository is not None:
                self._collect_mongodb_metrics(mongo_connection, gkg_repository, metrics)

            metrics.mark_success()

        except DragonsDataETLError as exc:
            logger.error("GDELT run %s failed at stage=%s: %s", run_id, exc.stage, exc)
            metrics.mark_failed(
                ErrorInfo(type=type(exc).__name__, message=str(exc), stage=exc.stage)
            )
            metrics.system = monitor.stop()
            self._persist_metrics(metrics, metrics_repository)
            self._close_all(mongo_connection, collector)
            raise
        except Exception as exc:  # unexpected error: still record it, then re-raise
            logger.exception("GDELT run %s failed with an unexpected error", run_id)
            metrics.mark_failed(
                ErrorInfo(type=type(exc).__name__, message=str(exc), stage="processing")
            )
            metrics.system = monitor.stop()
            self._persist_metrics(metrics, metrics_repository)
            self._close_all(mongo_connection, collector)
            raise

        metrics.system = monitor.stop()
        self._persist_metrics(metrics, metrics_repository)
        self._close_all(mongo_connection, collector)

        logger.info("GDELT run %s finished with status=%s", run_id, metrics.status)
        return metrics.to_dict()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _maybe_connect_mongodb(
        self,
    ) -> tuple[MongoDBConnection | None, ExecutionMetricsRepository | None, GkgRecordsRepository | None]:
        needs_mongo = self.gdelt_config.is_ingestion or self.gdelt_config.save_metrics
        if not needs_mongo:
            return None, None, None

        mongodb_config = self._mongodb_config or load_mongodb_config()
        connection = MongoDBConnection(mongodb_config)
        initialize_database(connection, mongodb_config)

        metrics_repository = ExecutionMetricsRepository(connection, mongodb_config)
        gkg_repository = (
            GkgRecordsRepository(connection, mongodb_config)
            if self.gdelt_config.is_ingestion
            else None
        )
        return connection, metrics_repository, gkg_repository

    def _process_and_store(
        self,
        rows,
        run_id: str,
        metrics: ExecutionMetrics,
        gkg_repository: GkgRecordsRepository | None,
        monitor: SystemMonitor,
    ) -> None:
        collected_at = utcnow()
        processing_start = time.monotonic()

        for batch_number, raw_batch in enumerate(
            chunked(rows, self.gdelt_config.batch_size), start=1
        ):
            if not monitor.check_disk_guard(self.pipeline_config.min_free_disk_bytes):
                raise ResourceLimitError(
                    "Available disk space dropped below the configured "
                    "min_free_disk_bytes guard; aborting run.",
                    stage="processing",
                )

            metrics.processing.rows_received += len(raw_batch)

            normalized_batch = [
                normalize_gkg_row(row, run_id=run_id, collected_at=collected_at)
                for row in raw_batch
            ]

            quality_result = run_quality_checks(normalized_batch)
            metrics.processing.rows_processed += quality_result.valid_count
            metrics.processing.rows_failed += quality_result.invalid_count

            dedupe_result = prepare_batch_for_storage(quality_result.valid_documents)
            metrics.processing.duplicates += dedupe_result.duplicate_count

            if gkg_repository is not None and dedupe_result.unique_documents:
                insert_result = gkg_repository.insert_batch(dedupe_result.unique_documents)
                metrics.mongodb.documents_attempted += insert_result.attempted
                metrics.mongodb.documents_inserted += insert_result.inserted
                metrics.mongodb.documents_failed += insert_result.failed
                metrics.mongodb.duplicates += insert_result.duplicate_key_errors
                metrics.processing.rows_inserted += insert_result.inserted

            metrics.processing.batches_processed = batch_number
            metrics.processing.batch_size = self.gdelt_config.batch_size

            logger.debug(
                "Batch %s: received=%s valid=%s invalid=%s duplicates=%s",
                batch_number,
                len(raw_batch),
                quality_result.valid_count,
                quality_result.invalid_count,
                dedupe_result.duplicate_count,
            )

        metrics.processing.processing_duration_seconds = time.monotonic() - processing_start

    def _collect_mongodb_metrics(
        self,
        connection: MongoDBConnection | None,
        gkg_repository: GkgRecordsRepository,
        metrics: ExecutionMetrics,
    ) -> None:
        if connection is None:
            return
        try:
            stats = connection.get_server_stats()
            metrics.mongodb.collection_size_bytes = stats.get("dataSize")
            metrics.mongodb.storage_size_bytes = stats.get("storageSize")
            metrics.mongodb.index_size_bytes = stats.get("indexSize")
        except DragonsDataETLError as exc:
            logger.warning("Could not collect MongoDB server stats: %s", exc)

    def _persist_metrics(
        self, metrics: ExecutionMetrics, repository: ExecutionMetricsRepository | None
    ) -> None:
        if not self.gdelt_config.save_metrics:
            execution_logger.log_summary(metrics)
            return
        execution_logger.persist(metrics, repository)

    def _close_all(
        self, connection: MongoDBConnection | None, collector: GdeltCollector | None
    ) -> None:
        if collector is not None:
            collector.close()
        if connection is not None:
            connection.close()

from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from pathlib import Path
from typing import Any

from src.gdelt.collectors.gdelt.collector import GdeltCollector
from src.gdelt.collectors.gdelt.query_builder import PreparedQuery, build_event_articles_query
from src.gdelt.collectors.web.scraper import NewsArticleScraper
from src.gdelt.common.config import (
    GdeltSourceConfig,
    MongoDBConfig,
    PipelineConfig,
    load_gdelt_config,
    load_mongodb_config,
    load_pipeline_config,
)
from src.gdelt.common.exceptions import DragonsDataETLError, MongoDBError, ResourceLimitError
from src.gdelt.common.utils import chunked, hash_identifier, new_run_id, utcnow
from src.gdelt.database.mongodb import MongoDBConnection
from src.gdelt.database.repositories import (
    EventosRepository,
    MetricsRepository,
    QueriesRepository,
    ScrapperRepository,
    WhitelistRepository,
    initialize_database,
)
from src.gdelt.monitoring import execution_logger
from src.gdelt.monitoring.metrics import ErrorInfo, ExecutionMetrics
from src.gdelt.monitoring.system_metrics import SystemMonitor
from src.gdelt.processing.event_csv import (
    DEFAULT_EVENTS_CSV,
    SAMPLE_ROW_LIMIT,
    load_events_from_csv,
    location_terms_for_country,
    merged_keywords,
)
from src.gdelt.processing.normalizer import normalize_gkg_row
from src.gdelt.processing.transformers import prepare_batch_for_storage
from src.gdelt.quality.checks import run_quality_checks

logger = logging.getLogger(__name__)


def _prepared_consulta(prepared: PreparedQuery) -> dict[str, Any]:
    parameters: dict[str, Any] = {}
    for parameter in prepared.parameters:
        value = getattr(parameter, "value", None)
        if value is None and hasattr(parameter, "values"):
            value = list(parameter.values)
        if isinstance(value, date):
            value = value.isoformat()
        parameters[parameter.name] = value
    return {"sql": prepared.sql, "parameters": parameters, "description": prepared.description}


def _to_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


class GdeltPipeline:
    """Event-driven GDELT run: eventos -> queries -> whitelist + metrics -> scrapper."""

    def __init__(
        self,
        gdelt_config: GdeltSourceConfig | None = None,
        mongodb_config: MongoDBConfig | None = None,
        pipeline_config: PipelineConfig | None = None,
        scraper: NewsArticleScraper | None = None,
    ) -> None:
        self.gdelt_config = gdelt_config or load_gdelt_config()
        self.pipeline_config = pipeline_config or load_pipeline_config()
        self._mongodb_config = mongodb_config
        self._scraper = scraper

    def run(
        self,
        *,
        csv_path: str | Path = DEFAULT_EVENTS_CSV,
        event_ids: list[str] | None = None,
        max_events: int | None = None,
        row_limit: int = SAMPLE_ROW_LIMIT,
        skip_scrape: bool = False,
        seed_only: bool = False,
    ) -> dict[str, Any]:
        run_id = new_run_id(self.pipeline_config.run_id_prefix)
        mongodb_config = self._mongodb_config or load_mongodb_config()
        connection = MongoDBConnection(mongodb_config)
        initialize_database(connection, mongodb_config)
        eventos_repo = EventosRepository(connection, mongodb_config)
        queries_repo = QueriesRepository(connection, mongodb_config)
        whitelist_repo = WhitelistRepository(connection, mongodb_config)
        scrapper_repo = ScrapperRepository(connection, mongodb_config)
        metrics_repo = MetricsRepository(connection, mongodb_config)

        seed_result = eventos_repo.upsert_many(load_events_from_csv(csv_path))
        events = self._select_events(eventos_repo, event_ids=event_ids, max_events=max_events)

        summary: dict[str, Any] = {
            "run_id": run_id,
            "status": "success",
            "seeded": seed_result.inserted,
            "events": len(events),
            "queries": 0,
            "whitelist": 0,
            "scrapper": 0,
            "event_results": [],
        }
        if seed_only:
            connection.close()
            return summary

        collector = GdeltCollector(self.gdelt_config)
        scraper = None if skip_scrape else (self._scraper or NewsArticleScraper())
        try:
            for event in events:
                event_summary = self._run_event(
                    event=event,
                    run_id=run_id,
                    row_limit=row_limit,
                    collector=collector,
                    scraper=scraper,
                    queries_repo=queries_repo,
                    whitelist_repo=whitelist_repo,
                    scrapper_repo=scrapper_repo,
                    metrics_repo=metrics_repo,
                    connection=connection,
                )
                summary["queries"] += 1
                summary["whitelist"] += int(event_summary.get("whitelist") or 0)
                summary["scrapper"] += int(event_summary.get("scrapper") or 0)
                summary["event_results"].append(event_summary)
                if event_summary.get("quota_exceeded"):
                    summary["status"] = "quota_exceeded"
                    break
        finally:
            collector.close()
            if scraper is not None and self._scraper is None:
                scraper.close()
            connection.close()
        return summary

    def _select_events(
        self,
        eventos_repo: EventosRepository,
        *,
        event_ids: list[str] | None,
        max_events: int | None,
    ) -> list[dict[str, Any]]:
        if event_ids:
            selected = []
            for event_id in event_ids:
                document = eventos_repo.get_by_id(event_id)
                if document is None:
                    raise DragonsDataETLError(
                        f"Unknown event id: {event_id}", stage="config"
                    )
                selected.append(document)
            return selected
        events = eventos_repo.list_all()
        if max_events is not None:
            return events[:max_events]
        return events

    def _run_event(
        self,
        *,
        event: dict[str, Any],
        run_id: str,
        row_limit: int,
        collector: GdeltCollector,
        scraper: NewsArticleScraper | None,
        queries_repo: QueriesRepository,
        whitelist_repo: WhitelistRepository,
        scrapper_repo: ScrapperRepository,
        metrics_repo: MetricsRepository,
        connection: MongoDBConnection,
    ) -> dict[str, Any]:
        event_id = event["id"]
        query_id = f"q_{event_id}_{uuid.uuid4().hex[:8]}"
        metric_id = f"m_{query_id}"
        start = _to_date(event["periodo"]["start"])
        end = _to_date(event["periodo"]["end"])
        keywords = merged_keywords(event)
        locations = location_terms_for_country(event.get("pais") or "")
        prepared = build_event_articles_query(
            self.gdelt_config.dataset,
            start,
            end,
            keywords,
            row_limit,
            locations=locations,
        )
        queries_repo.insert(
            {
                "id": query_id,
                "id_evento": event_id,
                "consulta": _prepared_consulta(prepared),
            }
        )

        metrics = ExecutionMetrics(run_id=run_id, source="gdelt", source_type="gkg")
        metrics.parameters = {
            "event_id": event_id,
            "query_id": query_id,
            "keywords": keywords,
            "date_range": {"start": start.isoformat(), "end": end.isoformat()},
            "locations": locations,
            "max_rows": row_limit,
        }
        monitor = SystemMonitor(
            interval_seconds=self.pipeline_config.system_monitor_interval_seconds
        )
        monitor.start()
        scraped = 0
        quota_exceeded = False
        try:
            collection_result = collector.collect_event_articles(
                start_date=start,
                end_date=end,
                keywords=keywords,
                row_limit=row_limit,
                locations=locations,
            )
            bq_metrics = collection_result.metrics
            metrics.query.job_id = bq_metrics.job_id
            metrics.query.query_description = prepared.description
            metrics.query.started_at = bq_metrics.started_at
            metrics.query.finished_at = bq_metrics.finished_at
            metrics.query.duration_seconds = bq_metrics.duration_seconds
            metrics.query.rows_returned = bq_metrics.rows_returned
            metrics.query.bytes_processed = bq_metrics.bytes_processed
            metrics.query.bytes_billed = bq_metrics.bytes_billed
            metrics.query.slot_ms = bq_metrics.slot_ms
            metrics.query.cache_hit = bq_metrics.cache_hit

            whitelist_docs = self._store_whitelist(
                rows=collection_result.rows,
                run_id=run_id,
                query_id=query_id,
                metric_id=metric_id,
                metrics=metrics,
                whitelist_repo=whitelist_repo,
                monitor=monitor,
            )
            quota_exceeded = metrics.mongodb.quota_reached
            if scraper is not None and not quota_exceeded:
                scraped = self._scrape_whitelist(
                    whitelist_docs,
                    scraper=scraper,
                    scrapper_repo=scrapper_repo,
                    whitelist_repo=whitelist_repo,
                    metrics=metrics,
                )
            metrics.mark_success()
        except DragonsDataETLError as exc:
            logger.error("Event %s query %s failed: %s", event_id, query_id, exc)
            metrics.mark_failed(
                ErrorInfo(type=type(exc).__name__, message=str(exc), stage=exc.stage)
            )
        except Exception as exc:
            logger.exception("Event %s query %s failed unexpectedly", event_id, query_id)
            metrics.mark_failed(
                ErrorInfo(type=type(exc).__name__, message=str(exc), stage="processing")
            )
        metrics.system = monitor.stop()
        self._persist_query_metrics(metrics, metrics_repo, metric_id=metric_id, query_id=query_id)
        return {
            "event_id": event_id,
            "query_id": query_id,
            "metric_id": metric_id,
            "status": metrics.status,
            "whitelist": metrics.processing.rows_inserted,
            "scrapper": scraped,
            "quota_exceeded": quota_exceeded,
        }

    def _store_whitelist(
        self,
        rows,
        run_id: str,
        query_id: str,
        metric_id: str,
        metrics: ExecutionMetrics,
        whitelist_repo: WhitelistRepository,
        monitor: SystemMonitor,
    ) -> list[dict[str, Any]]:
        collected_at = utcnow()
        processing_start = time.monotonic()
        stored: list[dict[str, Any]] = []
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
            documents = [
                _whitelist_document(document, query_id=query_id, metric_id=metric_id)
                for document in dedupe_result.unique_documents
            ]
            if documents:
                insert_result = whitelist_repo.insert_batch(documents)
                metrics.mongodb.documents_attempted += insert_result.attempted
                metrics.mongodb.documents_inserted += insert_result.inserted
                metrics.mongodb.documents_failed += insert_result.failed
                metrics.mongodb.duplicates += insert_result.duplicate_key_errors
                metrics.processing.rows_inserted += insert_result.inserted
                stored.extend(documents)
                if insert_result.quota_exceeded:
                    metrics.mongodb.quota_reached = True
                    break
            metrics.processing.batches_processed = batch_number
            metrics.processing.batch_size = self.gdelt_config.batch_size
        metrics.processing.processing_duration_seconds = time.monotonic() - processing_start
        return stored

    def _scrape_whitelist(
        self,
        documents: list[dict[str, Any]],
        *,
        scraper: NewsArticleScraper,
        scrapper_repo: ScrapperRepository,
        whitelist_repo: WhitelistRepository,
        metrics: ExecutionMetrics,
    ) -> int:
        inserted = 0
        for document in documents:
            url = str(document.get("url") or "").strip()
            if not url.lower().startswith(("http://", "https://")):
                continue
            metrics.mongodb.crawled_attempted += 1
            scraped = scraper.scrape(url)
            if scraped.get("status") == "success":
                metrics.mongodb.crawled_succeeded += 1
            scrapper_id = f"s_{document['id']}"
            scrapper_repo.insert(
                {
                    "id": scrapper_id,
                    "hash_whitelist": document["hash"],
                    "contenido": scraped,
                    "id_whitelist": document["id"],
                    "url": url,
                }
            )
            whitelist_repo.set_scrapper_id(document["id"], scrapper_id)
            metrics.mongodb.crawled_inserted += 1
            inserted += 1
        return inserted

    def _persist_query_metrics(
        self,
        metrics: ExecutionMetrics,
        repository: MetricsRepository,
        *,
        metric_id: str,
        query_id: str,
    ) -> None:
        document = metrics.to_dict()
        document["id"] = metric_id
        document["id_query"] = query_id
        if not self.gdelt_config.save_metrics:
            execution_logger.log_summary(metrics)
            return
        try:
            execution_logger.log_summary(metrics)
            repository.save(document)
        except MongoDBError as exc:
            logger.warning("Could not persist metrics: %s", exc)


def _whitelist_document(
    normalized: dict[str, Any],
    *,
    query_id: str,
    metric_id: str,
) -> dict[str, Any]:
    whitelist_id = str(normalized.get("gkg_record_id") or uuid.uuid4().hex)
    url = str(normalized.get("document_identifier") or "").strip()
    return {
        "id": whitelist_id,
        "hash": hash_identifier(whitelist_id),
        "url": url,
        "id_query": query_id,
        "id_scrapper": None,
        "id_metric": metric_id,
        **normalized,
    }

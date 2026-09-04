
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from src.gdelt.common.utils import utcnow


@dataclass
class QueryMetrics:
    job_id: str | None = None
    query_description: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
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
            "query_description": self.query_description,
            "parameters": self.parameters,
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
class ProcessingMetrics:
    rows_received: int = 0
    rows_processed: int = 0
    rows_inserted: int = 0
    rows_failed: int = 0
    duplicates: int = 0
    batches_processed: int = 0
    batch_size: int = 0
    processing_duration_seconds: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "rows_received": self.rows_received,
            "rows_processed": self.rows_processed,
            "rows_inserted": self.rows_inserted,
            "rows_failed": self.rows_failed,
            "duplicates": self.duplicates,
            "batches_processed": self.batches_processed,
            "batch_size": self.batch_size,
            "processing_duration_seconds": self.processing_duration_seconds,
        }


@dataclass
class MongoDBMetrics:
    documents_attempted: int = 0
    documents_inserted: int = 0
    documents_failed: int = 0
    duplicates: int = 0
    quota_reached: bool = False
    crawled_attempted: int = 0
    crawled_succeeded: int = 0
    crawled_inserted: int = 0
    collection_size_bytes: int | None = None
    storage_size_bytes: int | None = None
    index_size_bytes: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "documents_attempted": self.documents_attempted,
            "documents_inserted": self.documents_inserted,
            "documents_failed": self.documents_failed,
            "duplicates": self.duplicates,
            "quota_reached": self.quota_reached,
            "crawled_attempted": self.crawled_attempted,
            "crawled_succeeded": self.crawled_succeeded,
            "crawled_inserted": self.crawled_inserted,
            "collection_size_bytes": self.collection_size_bytes,
            "storage_size_bytes": self.storage_size_bytes,
            "index_size_bytes": self.index_size_bytes,
        }


@dataclass
class SystemMetrics:
    ram_before_bytes: int | None = None
    ram_after_bytes: int | None = None
    ram_peak_bytes: int | None = None
    disk_free_before_bytes: int | None = None
    disk_free_after_bytes: int | None = None
    disk_free_minimum_bytes: int | None = None
    cpu_percent_avg: float | None = None
    cpu_count: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ram_before_bytes": self.ram_before_bytes,
            "ram_after_bytes": self.ram_after_bytes,
            "ram_peak_bytes": self.ram_peak_bytes,
            "disk_free_before_bytes": self.disk_free_before_bytes,
            "disk_free_after_bytes": self.disk_free_after_bytes,
            "disk_free_minimum_bytes": self.disk_free_minimum_bytes,
            "cpu_percent_avg": self.cpu_percent_avg,
            "cpu_count": self.cpu_count,
        }


@dataclass
class ErrorInfo:
    type: str
    message: str
    stage: str

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "message": self.message, "stage": self.stage}


@dataclass
class ExecutionMetrics:
    """Top-level container matching the execution_metrics document shape
    described in project spec sections 10-11."""

    run_id: str
    source: str = "gdelt"
    source_type: str = "gkg"
    status: str = "running"  # running | success | failed

    parameters: dict[str, Any] = field(default_factory=dict)
    query: QueryMetrics = field(default_factory=QueryMetrics)
    processing: ProcessingMetrics = field(default_factory=ProcessingMetrics)
    mongodb: MongoDBMetrics = field(default_factory=MongoDBMetrics)
    system: SystemMetrics = field(default_factory=SystemMetrics)

    started_at: datetime = field(default_factory=utcnow)
    finished_at: datetime | None = None

    error: ErrorInfo | None = None

    def mark_success(self) -> None:
        self.status = "success"
        self.finished_at = utcnow()

    def mark_failed(self, error: ErrorInfo) -> None:
        self.status = "failed"
        self.error = error
        self.finished_at = utcnow()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "source": self.source,
            "source_type": self.source_type,
            "status": self.status,
            "parameters": self.parameters,
            "query": self.query.to_dict(),
            "processing": self.processing.to_dict(),
            "mongodb": self.mongodb.to_dict(),
            "system": self.system.to_dict(),
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "error": self.error.to_dict() if self.error else None,
        }

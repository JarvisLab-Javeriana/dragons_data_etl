
from __future__ import annotations

import logging
from typing import Any

from src.database.repositories import ExecutionMetricsRepository
from src.monitoring.metrics import ExecutionMetrics

logger = logging.getLogger(__name__)


def log_summary(metrics: ExecutionMetrics) -> None:
    logger.info(
        "run_id=%s status=%s rows_returned=%s rows_inserted=%s "
        "bytes_billed=%s duration=%.2fs",
        metrics.run_id,
        metrics.status,
        metrics.query.rows_returned,
        metrics.processing.rows_inserted,
        metrics.query.bytes_billed,
        metrics.query.duration_seconds or 0.0,
    )


def persist(
    metrics: ExecutionMetrics, repository: ExecutionMetricsRepository | None
) -> None:

    log_summary(metrics)
    if repository is None:
        logger.debug("No ExecutionMetricsRepository provided; skipping persistence.")
        return
    repository.save(metrics.to_dict())
    logger.info("Execution metrics for run_id=%s persisted to MongoDB.", metrics.run_id)

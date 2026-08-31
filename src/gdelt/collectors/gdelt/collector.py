from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any

from src.gdelt.collectors.gdelt import query_builder
from src.gdelt.collectors.gdelt.bigquery_client import BigQueryGdeltClient, BigQueryJobMetrics
from src.gdelt.common.config import GdeltSourceConfig
from src.gdelt.common.exceptions import BigQueryError, ResourceLimitError

logger = logging.getLogger(__name__)


@dataclass
class GdeltCollectionResult:
    """What GdeltCollector.collect_articles() hands back to the pipeline."""

    rows: Iterator[dict[str, Any]]
    metrics: BigQueryJobMetrics


class GdeltCollector:
    """High-level façade over GDELT GKG acquisition via BigQuery."""

    def __init__(
        self,
        config: GdeltSourceConfig,
        bq_client: BigQueryGdeltClient | None = None,
    ) -> None:
        self.config = config
        self.bq_client = bq_client or BigQueryGdeltClient()

    # ------------------------------------------------------------------
    # Metadata / discovery helpers
    # ------------------------------------------------------------------

    def get_min_max_date(self) -> dict[str, Any]:
        prepared = query_builder.build_min_max_date_query(self.config.dataset)
        rows, _metrics = self.bq_client.run_scalar_query(prepared)
        return rows[0] if rows else {}

    def list_tables(self) -> list[dict[str, Any]]:
        prepared = query_builder.build_tables_query(self.config.dataset)
        rows, _metrics = self.bq_client.run_scalar_query(prepared)
        return rows

    def list_columns(self, table_name: str | None = None) -> list[dict[str, Any]]:
        prepared = query_builder.build_columns_query(self.config.dataset, table_name)
        rows, _metrics = self.bq_client.run_scalar_query(prepared)
        return rows

    # ------------------------------------------------------------------
    # Analysis helpers (cheap, used for experimentation / stress testing)
    # ------------------------------------------------------------------

    def get_yearly_counts(self) -> list[dict[str, Any]]:
        prepared = query_builder.build_yearly_count_query(
            self.config.dataset,
            self.config.date_range.start,
            self.config.date_range.end,
        )
        rows, _metrics = self.bq_client.run_scalar_query(prepared)
        return rows

    def get_keyword_count(self) -> tuple[int, BigQueryJobMetrics]:
        prepared = query_builder.build_keyword_count_query(
            self.config.dataset,
            self.config.date_range.start,
            self.config.date_range.end,
            self.config.keywords,
        )
        rows, metrics = self.bq_client.run_scalar_query(prepared)
        count = rows[0]["matching_row_count"] if rows else 0
        return count, metrics

    def count_for_range(
        self, start_date, end_date, keywords: list[str] | None = None
    ) -> tuple[int, BigQueryJobMetrics]:
        """Used by scripts/test_gdelt_history.py to characterize arbitrary
        historical windows without going through the main config."""
        prepared = query_builder.build_keyword_count_query(
            self.config.dataset, start_date, end_date, keywords or self.config.keywords
        )
        rows, metrics = self.bq_client.run_scalar_query(prepared)
        count = rows[0]["matching_row_count"] if rows else 0
        return count, metrics

    # ------------------------------------------------------------------
    # Extraction (the "real" data acquisition path)
    # ------------------------------------------------------------------

    def collect_articles(self) -> GdeltCollectionResult:
        """Execute the extraction query and return a lazy row iterator.

        Enforces `max_bytes_billed` (if configured) via a dry-run estimate
        BEFORE executing the real, billable query -- this protects against
        accidentally running an unbounded historical query.
        """
        prepared = query_builder.build_articles_query(
            self.config.dataset,
            self.config.date_range.start,
            self.config.date_range.end,
            self.config.keywords,
            self.config.max_rows,
        )

        if self.config.max_bytes_billed is not None:
            estimated = self.bq_client.estimate_bytes(prepared)
            if estimated > self.config.max_bytes_billed:
                raise ResourceLimitError(
                    f"Estimated bytes processed ({estimated}) exceeds "
                    f"configured max_bytes_billed ({self.config.max_bytes_billed}). "
                    "Narrow the date range/keywords or raise the limit in "
                    "config/sources/gdelt.yaml.",
                    stage="bigquery",
                )
            logger.info("Dry-run estimate: %s bytes (within limit)", estimated)

        try:
            result = self.bq_client.run_query(
                prepared,
                max_bytes_billed=self.config.max_bytes_billed,
                page_size=self.config.batch_size,
            )
        except BigQueryError:
            raise

        return GdeltCollectionResult(rows=result.rows, metrics=result.metrics)

    def close(self) -> None:
        self.bq_client.close()

    def __enter__(self) -> "GdeltCollector":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

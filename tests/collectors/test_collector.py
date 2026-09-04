"""Unit tests for GdeltCollector using a mocked BigQueryGdeltClient (no real
BigQuery connection is made)."""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.gdelt.collectors.gdelt.bigquery_client import BigQueryJobMetrics, BigQueryQueryResult
from src.gdelt.collectors.gdelt.collector import GdeltCollector
from src.gdelt.common.config import DatasetConfig, DateRangeConfig, GdeltSourceConfig
from src.gdelt.common.exceptions import ResourceLimitError


def make_config(**overrides) -> GdeltSourceConfig:
    defaults = dict(
        dataset=DatasetConfig(project="gdelt-bq", dataset="gdeltv2", table="gkg_partitioned"),
        keywords=["biodiversity"],
        date_range=DateRangeConfig(start=date(2020, 1, 1), end=date(2020, 2, 1)),
        max_rows=100,
        batch_size=10,
        mode="test",
        save_to_mongodb=False,
        save_metrics=False,
        max_bytes_billed=None,
    )
    defaults.update(overrides)
    return GdeltSourceConfig(**defaults)


def test_collect_articles_returns_rows_and_metrics():
    mock_bq_client = MagicMock()
    mock_bq_client.run_query.return_value = BigQueryQueryResult(
        rows=iter([{"GKGRECORDID": "abc"}]),
        metrics=BigQueryJobMetrics(job_id="job123", rows_returned=1),
    )

    collector = GdeltCollector(make_config(), bq_client=mock_bq_client)
    result = collector.collect_articles()

    rows = list(result.rows)
    assert rows == [{"GKGRECORDID": "abc"}]
    assert result.metrics.job_id == "job123"
    mock_bq_client.run_query.assert_called_once()


def test_collect_articles_enforces_max_bytes_billed():
    mock_bq_client = MagicMock()
    mock_bq_client.estimate_bytes.return_value = 10_000_000_000  # 10 GB estimate

    collector = GdeltCollector(
        make_config(max_bytes_billed=1_000_000_000), bq_client=mock_bq_client
    )

    with pytest.raises(ResourceLimitError):
        collector.collect_articles()

    mock_bq_client.run_query.assert_not_called()


def test_get_keyword_count_reads_first_row():
    mock_bq_client = MagicMock()
    mock_bq_client.run_scalar_query.return_value = (
        [{"matching_row_count": 42}],
        BigQueryJobMetrics(job_id="job456"),
    )
    collector = GdeltCollector(make_config(), bq_client=mock_bq_client)

    count, metrics = collector.get_keyword_count()

    assert count == 42
    assert metrics.job_id == "job456"

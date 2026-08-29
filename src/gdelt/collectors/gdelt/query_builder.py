from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from google.cloud import bigquery

from src.gdelt.common.config import DatasetConfig, PROJECT_ROOT

QUERIES_DIR = PROJECT_ROOT / "queries" / "gdelt"


@dataclass(frozen=True)
class PreparedQuery:
    """A query ready to be sent to BigQuery."""

    sql: str
    parameters: list[bigquery.query._AbstractQueryParameter]
    description: str


def _read_sql(relative_path: str) -> str:
    full_path = QUERIES_DIR / relative_path
    return full_path.read_text(encoding="utf-8")


def _interpolate_identifiers(sql: str, dataset: DatasetConfig, table_override: str | None = None) -> str:
    return sql.format(
        project=dataset.project,
        dataset=dataset.dataset,
        table=table_override or dataset.table,
    )


def build_min_max_date_query(dataset: DatasetConfig) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("metadata/min_max_date.sql"), dataset)
    return PreparedQuery(sql=sql, parameters=[], description="min/max available DATE in GKG table")


def build_tables_query(dataset: DatasetConfig) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("metadata/tables.sql"), dataset)
    return PreparedQuery(sql=sql, parameters=[], description="tables available in dataset")


def build_columns_query(dataset: DatasetConfig, table_name: str | None = None) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("metadata/columns.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("table_name", "STRING", table_name or dataset.table),
    ]
    return PreparedQuery(sql=sql, parameters=parameters, description="columns for table")


def build_yearly_count_query(
    dataset: DatasetConfig, start_date: date, end_date: date
) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("analysis/yearly_count.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
    ]
    return PreparedQuery(sql=sql, parameters=parameters, description="row count per year")


def build_keyword_count_query(
    dataset: DatasetConfig, start_date: date, end_date: date, keywords: list[str]
) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("analysis/keyword_count.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ArrayQueryParameter("keywords", "STRING", keywords),
    ]
    return PreparedQuery(sql=sql, parameters=parameters, description="row count matching keywords")


def build_articles_query(
    dataset: DatasetConfig,
    start_date: date,
    end_date: date,
    keywords: list[str],
    row_limit: int,
) -> PreparedQuery:
    sql = _interpolate_identifiers(_read_sql("extraction/articles.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ArrayQueryParameter("keywords", "STRING", keywords),
        bigquery.ScalarQueryParameter("row_limit", "INT64", row_limit),
    ]
    return PreparedQuery(sql=sql, parameters=parameters, description="GKG article extraction")

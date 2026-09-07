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


def build_client_articles_query(
    dataset: DatasetConfig,
    start_date: date,
    end_date: date,
    keywords: list[str],
    row_limit: int,
    tags: list[str] | None = None,
    media: list[str] | None = None,
    languages: list[str] | None = None,
) -> PreparedQuery:
    tags = [t for t in (tags or []) if t]
    media = [m for m in (media or []) if m]
    languages = [lang for lang in (languages or []) if lang]
    sql = _interpolate_identifiers(_read_sql("extraction/articles_client.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ArrayQueryParameter("keywords", "STRING", keywords),
        bigquery.ScalarQueryParameter("apply_tags", "BOOL", bool(tags)),
        bigquery.ArrayQueryParameter("tags", "STRING", tags or [""]),
        bigquery.ScalarQueryParameter("apply_media", "BOOL", bool(media)),
        bigquery.ArrayQueryParameter("media", "STRING", media or [""]),
        bigquery.ScalarQueryParameter("apply_languages", "BOOL", bool(languages)),
        bigquery.ArrayQueryParameter("languages", "STRING", languages or [""]),
        bigquery.ScalarQueryParameter("row_limit", "INT64", row_limit),
    ]
    return PreparedQuery(
        sql=sql, parameters=parameters, description="GKG article extraction for news_client"
    )


def build_event_articles_query(
    dataset: DatasetConfig,
    start_date: date,
    end_date: date,
    keywords: list[str],
    row_limit: int,
    locations: list[str] | None = None,
) -> PreparedQuery:
    locations = [item for item in (locations or []) if item]
    sql = _interpolate_identifiers(_read_sql("extraction/articles_by_event.sql"), dataset)
    parameters = [
        bigquery.ScalarQueryParameter("start_date", "DATE", start_date),
        bigquery.ScalarQueryParameter("end_date", "DATE", end_date),
        bigquery.ArrayQueryParameter("keywords", "STRING", keywords),
        bigquery.ScalarQueryParameter("apply_locations", "BOOL", bool(locations)),
        bigquery.ArrayQueryParameter("locations", "STRING", locations or [""]),
        bigquery.ScalarQueryParameter("row_limit", "INT64", row_limit),
    ]
    return PreparedQuery(
        sql=sql,
        parameters=parameters,
        description="GKG article extraction for a biodiversity event",
    )

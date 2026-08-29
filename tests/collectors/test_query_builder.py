"""Unit tests for src.collectors.gdelt.query_builder.

These tests only check SQL text assembly and parameter construction; they
never touch a real BigQuery connection.
"""

from __future__ import annotations

from datetime import date

from src.gdelt.collectors.gdelt import query_builder
from src.gedelt.collectors.common.config import DatasetConfig

DATASET = DatasetConfig(project="gdelt-bq", dataset="gdeltv2", table="gkg_partitioned")


def test_build_min_max_date_query_interpolates_identifiers():
    prepared = query_builder.build_min_max_date_query(DATASET)
    assert "gdelt-bq.gdeltv2.gkg_partitioned" in prepared.sql
    assert prepared.parameters == []


def test_build_articles_query_has_expected_parameters():
    prepared = query_builder.build_articles_query(
        DATASET,
        start_date=date(2020, 1, 1),
        end_date=date(2020, 2, 1),
        keywords=["biodiversity", "climate"],
        row_limit=100,
    )
    param_names = {p.name for p in prepared.parameters}
    assert param_names == {"start_date", "end_date", "keywords", "row_limit"}
    assert "_PARTITIONTIME" in prepared.sql
    assert "LIMIT" in prepared.sql


def test_build_columns_query_uses_scalar_table_name_parameter():
    prepared = query_builder.build_columns_query(DATASET, table_name="gkg_partitioned")
    assert len(prepared.parameters) == 1
    assert prepared.parameters[0].name == "table_name"
    assert prepared.parameters[0].value == "gkg_partitioned"

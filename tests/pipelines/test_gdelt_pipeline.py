from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

import pytest

from src.gdelt.collectors.gdelt.bigquery_client import BigQueryJobMetrics, BigQueryQueryResult
from src.gdelt.collectors.gdelt.collector import GdeltCollector
from src.gdelt.common.config import (
    DatasetConfig,
    DateRangeConfig,
    GdeltSourceConfig,
    MongoDBConfig,
    PipelineConfig,
)
from src.gdelt.pipelines.gdelt_pipeline import GdeltPipeline

mongomock = pytest.importorskip("mongomock")


def _gdelt_config() -> GdeltSourceConfig:
    return GdeltSourceConfig(
        dataset=DatasetConfig(project="gdelt-bq", dataset="gdeltv2", table="gkg_partitioned"),
        keywords=["biodiversity"],
        date_range=DateRangeConfig(start=date(2016, 1, 1), end=date(2017, 1, 1)),
        max_rows=100,
        batch_size=10,
        mode="ingestion",
        save_to_mongodb=True,
        save_metrics=True,
        max_bytes_billed=None,
    )


def _mongo_config() -> MongoDBConfig:
    return MongoDBConfig(
        uri="mongodb://localhost:27017",
        database="test_db",
        gkg_records_collection="gkg_records",
        execution_metrics_collection="execution_metrics",
        crawled_data_collection="crawled_data",
        eventos_collection="eventos",
        queries_collection="queries",
        whitelist_collection="whitelist",
        scrapper_collection="scrapper",
        metrics_collection="metrics",
        connect_timeout_ms=1000,
        server_selection_timeout_ms=1000,
        ordered_inserts=False,
        ensure_indexes_on_startup=True,
    )


class _FakeMongo:
    def __init__(self, config: MongoDBConfig) -> None:
        self.config = config
        self._client = mongomock.MongoClient()

    @property
    def client(self):
        return self._client

    @property
    def database(self):
        return self._client[self.config.database]

    def close(self) -> None:
        return None

    def get_server_stats(self) -> dict:
        return {}


def test_pipeline_sample_persists_query_whitelist_metrics_and_scrapper(monkeypatch, tmp_path):
    csv_path = tmp_path / "events.csv"
    csv_path.write_text(
        "title\n"
        "ID,Country,Year,Period,Spatial level,Valence,Event (EN),Event (ES),Event (HU),"
        "Event type,What happened (plain language),Why it could enter public discourse,"
        "Dominant framing / narrative,Sector linkage,Climate-biodiversity link,"
        "Keyword hooks (EN),Keyword hooks (ES),Keyword hooks (HU),Source / starting point,Origin\n"
        "UK-01,United Kingdom,2016,2016 (Jun),National,Mixed,Brexit,,,Political,"
        "happened,why,framing,sector,Indirect,Brexit environment; Habitats Directive,"
        "Brexit medio ambiente,Brexit környezetvédelem,https://example.com,New\n",
        encoding="utf-8",
    )

    fake = _FakeMongo(_mongo_config())
    monkeypatch.setattr(
        "src.gdelt.pipelines.gdelt_pipeline.MongoDBConnection",
        lambda config: fake,
    )

    mock_bq = MagicMock()
    mock_bq.run_query.return_value = BigQueryQueryResult(
        rows=iter(
            [
                {
                    "GKGRECORDID": "20160601-1",
                    "DATE": "20160601120000",
                    "SourceCommonName": "bbc.co.uk",
                    "DocumentIdentifier": "https://example.com/article",
                    "V2Themes": "ENV_BIODIVERSITY",
                    "V2Locations": "United Kingdom",
                    "V2Persons": "",
                    "V2Organizations": "",
                    "V2Tone": "1,1,0,1,0,0,10",
                }
            ]
        ),
        metrics=BigQueryJobMetrics(job_id="job-1", rows_returned=1, duration_seconds=0.1),
    )
    monkeypatch.setattr(
        "src.gdelt.pipelines.gdelt_pipeline.GdeltCollector",
        lambda config: GdeltCollector(config, bq_client=mock_bq),
    )

    scraper = MagicMock()
    scraper.scrape.return_value = {
        "url": "https://example.com/article",
        "contenido": "article body",
        "status": "success",
    }

    pipeline = GdeltPipeline(
        gdelt_config=_gdelt_config(),
        mongodb_config=_mongo_config(),
        pipeline_config=PipelineConfig(
            run_id_prefix="test",
            experiments_output_dir="docs/experiments",
            system_monitor_interval_seconds=60,
            min_free_disk_bytes=None,
        ),
        scraper=scraper,
    )
    summary = pipeline.run(csv_path=csv_path, event_ids=["UK-01"], row_limit=100)

    assert summary["queries"] == 1
    assert summary["whitelist"] == 1
    assert summary["scrapper"] == 1
    db = fake.database
    assert db["queries"].count_documents({}) == 1
    whitelist = db["whitelist"].find_one({"id": "20160601-1"})
    assert whitelist["url"] == "https://example.com/article"
    assert whitelist["id_query"]
    assert whitelist["id_metric"]
    assert whitelist["id_scrapper"]
    assert db["metrics"].count_documents({"id_query": whitelist["id_query"]}) == 1
    assert db["scrapper"].count_documents({"hash_whitelist": whitelist["hash"]}) == 1
    mock_bq.run_query.assert_called_once()
    limit = next(
        parameter.value
        for parameter in mock_bq.run_query.call_args.args[0].parameters
        if parameter.name == "row_limit"
    )
    assert limit == 100

from __future__ import annotations

import logging
from typing import Any

from src.gdelt.collectors.web.crawler import ArticleCrawler
from src.gdelt.common.config import (
    CrawlerConfig,
    MongoDBConfig,
    load_crawler_config,
    load_mongodb_config,
)
from src.gdelt.common.utils import new_run_id
from src.gdelt.database.mongodb import MongoDBConnection
from src.gdelt.database.repositories import CrawledDataRepository, GkgRecordsRepository

logger = logging.getLogger(__name__)

_LOCAL_ONLY_FIELDS = {"html_path", "text_path", "metadata_path"}


def _mongo_documents(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    documents = []
    for record in records:
        documents.append(
            {key: value for key, value in record.items() if key not in _LOCAL_ONLY_FIELDS}
        )
    return documents


class CrawlPipeline:
    """Read GDELT URLs and persist crawled text/metadata to MongoDB crawled_data."""

    def __init__(
        self,
        crawler_config: CrawlerConfig | None = None,
        mongodb_config: MongoDBConfig | None = None,
        crawler: ArticleCrawler | None = None,
    ) -> None:
        self.crawler_config = crawler_config or load_crawler_config()
        self._mongodb_config = mongodb_config
        self._crawler = crawler

    def run(
        self,
        limit: int | None = None,
        targets: list[dict[str, Any]] | None = None,
        run_id: str | None = None,
        persist_to_mongodb: bool = True,
    ) -> dict[str, Any]:
        crawl_limit = limit if limit is not None else self.crawler_config.limit
        crawl_run_id = run_id or new_run_id("crawl")
        mongodb_config = self._mongodb_config or load_mongodb_config()
        connection: MongoDBConnection | None = None
        crawler = self._crawler or ArticleCrawler(self.crawler_config)
        try:
            if targets is None:
                connection = MongoDBConnection(mongodb_config)
                gkg_repository = GkgRecordsRepository(connection, mongodb_config)
                targets = gkg_repository.list_http_document_urls(crawl_limit)
            else:
                targets = targets[:crawl_limit]

            logger.info("Crawling %s URLs (limit=%s)", len(targets), crawl_limit)
            if not targets:
                return {
                    "run_id": crawl_run_id,
                    "status": "success",
                    "attempted": 0,
                    "succeeded": 0,
                    "inserted": 0,
                    "message": "No HTTP document_identifier values to crawl.",
                }

            summary = crawler.crawl(targets, run_id=crawl_run_id)
            records = summary.pop("records", [])
            inserted = 0
            quota_exceeded = False
            if persist_to_mongodb:
                if connection is None:
                    connection = MongoDBConnection(mongodb_config)
                crawled_repository = CrawledDataRepository(connection, mongodb_config)
                insert_result = crawled_repository.insert_batch(_mongo_documents(records))
                inserted = insert_result.inserted
                quota_exceeded = insert_result.quota_exceeded
                logger.info(
                    "Inserted %s/%s crawled documents into crawled_data",
                    inserted,
                    insert_result.attempted,
                )

            summary["status"] = "success"
            summary["inserted"] = inserted
            summary["quota_exceeded"] = quota_exceeded
            return summary
        finally:
            crawler.close()
            if connection is not None:
                connection.close()

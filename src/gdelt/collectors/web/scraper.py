from __future__ import annotations

import logging
from typing import Any

from src.gdelt.collectors.web.news_extractor import (
    BrowserFallback,
    DomainRateLimiter,
    RobotsCache,
    create_session,
    download_article,
)

logger = logging.getLogger(__name__)


class NewsArticleScraper:
    """Thin adapter over the news_extractor module from test/news-scraper-pipeline."""

    def __init__(self, delay_seconds: float = 2.5, timeout_seconds: int = 25) -> None:
        self.timeout_seconds = timeout_seconds
        self.session = create_session()
        self.limiter = DomainRateLimiter(delay_seconds)
        self.robots = RobotsCache(self.session, self.limiter, timeout_seconds)
        self.browser = BrowserFallback(timeout_seconds)

    def scrape(self, url: str) -> dict[str, Any]:
        try:
            content = download_article(
                self.session,
                self.browser,
                self.limiter,
                self.robots,
                url,
                self.timeout_seconds,
            )
            if content:
                return {"url": url, "contenido": content, "status": "success"}
            return {"url": url, "contenido": None, "status": "empty"}
        except Exception as exc:
            logger.warning("Scrape failed for %s: %s", url, exc)
            return {
                "url": url,
                "contenido": None,
                "status": "error",
                "error": str(exc),
            }

    def close(self) -> None:
        self.browser.close()
        self.session.close()

    def __enter__(self) -> "NewsArticleScraper":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

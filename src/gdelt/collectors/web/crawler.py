from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from trafilatura import extract, extract_metadata

from src.gdelt.common.config import CrawlerConfig, PROJECT_ROOT
from src.gdelt.common.utils import utcnow

logger = logging.getLogger(__name__)

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass
class ExtractedPage:
    title: str | None
    author: str | None
    date: str | None
    language: str | None
    text: str | None
    final_url: str


class RobotsCache:
    """Per-host robots.txt cache. Fail-closed if robots.txt cannot be read."""

    def __init__(self, session: requests.Session, timeout_seconds: float, user_agent: str) -> None:
        self._session = session
        self._timeout_seconds = timeout_seconds
        self._user_agent = user_agent
        self._parsers: dict[str, RobotFileParser | None] = {}

    def is_allowed(self, url: str) -> tuple[bool, str | None]:
        parsed = urlparse(url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return False, "invalid_url"
        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self._load(origin)
        if parser is None:
            return False, "robots_unavailable"
        if not parser.can_fetch(self._user_agent, url):
            return False, "robots_disallowed"
        return True, None

    def _load(self, origin: str) -> RobotFileParser | None:
        if origin in self._parsers:
            return self._parsers[origin]
        robots_url = f"{origin}/robots.txt"
        try:
            response = self._session.get(
                robots_url,
                timeout=self._timeout_seconds,
                allow_redirects=True,
            )
            parser = RobotFileParser()
            parser.set_url(robots_url)
            if response.status_code >= 400:
                # Missing robots.txt is treated as allow-all.
                parser.parse([])
            else:
                parser.parse(response.text.splitlines())
            self._parsers[origin] = parser
            return parser
        except requests.RequestException as exc:
            logger.warning("Could not fetch robots.txt for %s: %s", origin, exc)
            self._parsers[origin] = None
            return None


def safe_dirname(gkg_record_id: str | None, fallback: str) -> str:
    raw = (gkg_record_id or fallback).strip() or fallback
    cleaned = _UNSAFE_FILENAME.sub("_", raw)
    return cleaned[:180]


_HTML_LANG = re.compile(r"<html[^>]*\blang=['\"]([a-zA-Z-]+)", re.IGNORECASE)


def _detect_language(html: str, text: str | None) -> str | None:
    html_match = _HTML_LANG.search(html or "")
    if html_match:
        return html_match.group(1).lower()
    sample = (text or "").strip()
    if len(sample) < 40:
        return None
    try:
        from langdetect import detect

        return detect(sample)
    except Exception:
        return None


def extract_page(html: str, url: str) -> ExtractedPage:
    metadata = extract_metadata(html, default_url=url)
    text = extract(
        html,
        url=url,
        include_comments=False,
        include_tables=False,
        favor_precision=True,
    )
    title = getattr(metadata, "title", None) if metadata else None
    author = getattr(metadata, "author", None) if metadata else None
    date = getattr(metadata, "date", None) if metadata else None
    language = getattr(metadata, "language", None) if metadata else None
    if not language:
        language = _detect_language(html, text)
    meta_url = getattr(metadata, "url", None) if metadata else None
    return ExtractedPage(
        title=title,
        author=author,
        date=date,
        language=language,
        text=text,
        final_url=meta_url or url,
    )


class ArticleCrawler:
    """Fetch GDELT document_identifier URLs and persist HTML + metadata locally."""

    def __init__(
        self,
        config: CrawlerConfig,
        session: requests.Session | None = None,
        output_root: Path | None = None,
    ) -> None:
        self.config = config
        self._owns_session = session is None
        self.session = session or requests.Session()
        self.session.headers.update({"User-Agent": config.user_agent})
        self.robots = RobotsCache(
            self.session, config.request_timeout_seconds, config.user_agent
        )
        root = output_root or Path(config.output_dir)
        self.output_root = root if root.is_absolute() else PROJECT_ROOT / root

    def close(self) -> None:
        if self._owns_session:
            self.session.close()

    def crawl(self, targets: list[dict[str, Any]], run_id: str | None = None) -> dict[str, Any]:
        run_id = run_id or utcnow().strftime("crawl_%Y%m%dT%H%M%SZ")
        run_dir = self.output_root / run_id
        pages_dir = run_dir / "pages"
        pages_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = run_dir / "manifest.jsonl"

        summary = {
            "run_id": run_id,
            "output_dir": str(run_dir),
            "attempted": 0,
            "succeeded": 0,
            "robots_disallowed": 0,
            "robots_unavailable": 0,
            "http_error": 0,
            "invalid_url": 0,
            "empty": 0,
        }

        records: list[dict[str, Any]] = []
        with manifest_path.open("w", encoding="utf-8") as manifest:
            for index, target in enumerate(targets):
                summary["attempted"] += 1
                tagged = {**target, "run_id": target.get("run_id") or run_id}
                record = self._crawl_one(tagged, pages_dir)
                records.append(record)
                status = record["status"]
                if status == "success":
                    summary["succeeded"] += 1
                elif status in summary:
                    summary[status] += 1
                else:
                    summary[status] = summary.get(status, 0) + 1
                manifest_record = {k: v for k, v in record.items() if k != "text"}
                manifest.write(json.dumps(manifest_record, ensure_ascii=False, default=str) + "\n")
                logger.info(
                    "[%s/%s] %s %s",
                    index + 1,
                    len(targets),
                    record["status"],
                    record.get("source_url"),
                )
                if index < len(targets) - 1 and self.config.delay_seconds > 0:
                    time.sleep(self.config.delay_seconds)

        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        summary["records"] = records
        return summary

    def _crawl_one(self, target: dict[str, Any], pages_dir: Path) -> dict[str, Any]:
        source_url = str(target.get("document_identifier") or "").strip()
        gkg_record_id = target.get("gkg_record_id")
        crawled_at = datetime.now(timezone.utc).isoformat()
        base = {
            "gkg_record_id": gkg_record_id,
            "document_identifier": source_url,
            "source_url": source_url,
            "source_common_name": target.get("source_common_name"),
            "gkg_date": target.get("date"),
            "crawled_at": crawled_at,
            "run_id": target.get("run_id"),
        }

        parsed = urlparse(source_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            return {**base, "status": "invalid_url", "error": "document_identifier is not an HTTP URL"}

        if self.config.respect_robots_txt:
            allowed, robots_status = self.robots.is_allowed(source_url)
            if not allowed:
                return {**base, "status": robots_status or "robots_disallowed"}

        try:
            response = self.session.get(
                source_url,
                timeout=self.config.request_timeout_seconds,
                allow_redirects=True,
            )
        except requests.RequestException as exc:
            return {**base, "status": "http_error", "error": str(exc)}

        if len(response.content) > self.config.max_html_bytes:
            return {
                **base,
                "status": "http_error",
                "http_status": response.status_code,
                "final_url": response.url,
                "error": f"response larger than max_html_bytes ({self.config.max_html_bytes})",
            }

        if response.status_code >= 400 or not response.content:
            return {
                **base,
                "status": "http_error",
                "http_status": response.status_code,
                "final_url": response.url,
                "error": f"HTTP {response.status_code}",
            }

        html = response.text
        extracted = extract_page(html, response.url)
        if not extracted.text and not extracted.title:
            record = {
                **base,
                "status": "empty",
                "http_status": response.status_code,
                "final_url": response.url,
                "title": extracted.title,
                "author": extracted.author,
                "date": extracted.date,
                "language": extracted.language,
                "text": extracted.text,
                "text_length": len(extracted.text or ""),
            }
            self._write_page_files(pages_dir, gkg_record_id, source_url, html, record, extracted.text)
            return record

        record = {
            **base,
            "status": "success",
            "http_status": response.status_code,
            "final_url": response.url,
            "title": extracted.title,
            "author": extracted.author,
            "date": extracted.date,
            "language": extracted.language,
            "text": extracted.text,
            "text_length": len(extracted.text or ""),
        }
        paths = self._write_page_files(
            pages_dir, gkg_record_id, source_url, html, record, extracted.text
        )
        record.update(paths)
        return record

    def _write_page_files(
        self,
        pages_dir: Path,
        gkg_record_id: str | None,
        source_url: str,
        html: str,
        metadata: dict[str, Any],
        text: str | None,
    ) -> dict[str, str]:
        dirname = safe_dirname(gkg_record_id, urlparse(source_url).netloc)
        page_dir = pages_dir / dirname
        page_dir.mkdir(parents=True, exist_ok=True)
        html_path = page_dir / "page.html"
        text_path = page_dir / "content.txt"
        meta_path = page_dir / "metadata.json"
        html_path.write_text(html, encoding="utf-8", errors="replace")
        text_path.write_text(text or "", encoding="utf-8", errors="replace")
        meta_path.write_text(
            json.dumps({**metadata, "html_path": str(html_path), "text_path": str(text_path)}, indent=2, default=str),
            encoding="utf-8",
        )
        return {"html_path": str(html_path), "text_path": str(text_path), "metadata_path": str(meta_path)}

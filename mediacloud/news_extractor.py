from __future__ import annotations

import argparse
import csv
import hashlib
import logging
import os
import re
import socket
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import certifi
import requests
import trafilatura
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient
from pymongo.errors import PyMongoError
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


# ============================================================================
# CONFIG
# ============================================================================

LANGUAGE_BY_FOLDER = {
    "spanish": "es",
    "english": "en",
    "hungarian": "hu",
}

WHITELIST_FIELDS = [
    "eid",
    "indexed_date",
    "media_name",
    "media_url",
    "publish_date",
    "title",
    "url",
]

HEADER_ALIASES = {
    "id": "eid",
    "eid": "eid",
    "indexed_date": "indexed_date",
    "indexed date": "indexed_date",
    "media_name": "media_name",
    "media name": "media_name",
    "media_url": "media_url",
    "media url": "media_url",
    "publish_date": "publish_date",
    "publish date": "publish_date",
    "title": "title",
    "url": "url",
    "language": "language",
}

REQUEST_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/152.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,*/*;q=0.8"
    ),
    "Accept-Language": "en-US,en;q=0.9,es;q=0.8",
    "Upgrade-Insecure-Requests": "1",
    "Connection": "keep-alive",
}

TRANSIENT_STATUS_CODES = [
    429,
    500,
    502,
    503,
    504,
]


# ============================================================================
# GENERAL HELPERS
# ============================================================================

def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = re.sub(
        r"[ \t\r\f\v]+",
        " ",
        str(value),
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    text = text.strip()

    return text or None


def normalize_header(
    header: str | None,
) -> str:
    if header is None:
        return ""

    normalized = (
        header
        .replace("\ufeff", "")
        .strip()
        .lower()
    )

    return HEADER_ALIASES.get(
        normalized,
        normalized,
    )


def is_valid_http_url(
    url: str,
) -> bool:
    try:
        parsed = urlparse(
            url
        )

        return (
            parsed.scheme
            in {"http", "https"}
            and bool(parsed.netloc)
        )

    except ValueError:
        return False


def domain_from_url(
    url: str,
) -> str:
    return urlparse(
        url
    ).netloc.lower()



def hash_url(
    url: str,
) -> str:
    """
    Return a deterministic SHA-256 hash of the URL.

    The original URL is preserved in `url`; this field is only an
    additional stable identifier that can be indexed and queried.
    """
    normalized_url = url.strip()

    return hashlib.sha256(
        normalized_url.encode(
            "utf-8"
        )
    ).hexdigest()


# ============================================================================
# MONGODB
# ============================================================================

def create_mongo_client(
    uri: str,
) -> MongoClient:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        socketTimeoutMS=30_000,
        retryWrites=True,
    )

    # Fail immediately if credentials/network are wrong.
    client.admin.command(
        "ping"
    )

    return client


def prepare_collection(
    client: MongoClient,
    database_name: str,
    collection_name: str,
):
    collection = client[
        database_name
    ][
        collection_name
    ]

    # One document per article + language + keyword family.
    collection.create_index(
        [
            ("eid", ASCENDING),
            ("language", ASCENDING),
            ("keywords", ASCENDING),
        ],
        unique=True,
        name="unique_eid_language_keywords",
    )

    collection.create_index(
        [("publish_date", ASCENDING)],
        name="publish_date_idx",
    )

    collection.create_index(
        [("media_name", ASCENDING)],
        name="media_name_idx",
    )

    collection.create_index(
        [("language", ASCENDING)],
        name="language_idx",
    )

    collection.create_index(
        [("keywords", ASCENDING)],
        name="keywords_idx",
    )

    collection.create_index(
        [("hash", ASCENDING)],
        name="hash_idx",
    )

    return collection


def mongo_identity(
    record: dict[str, Any],
) -> dict[str, Any]:
    return {
        "eid": record["eid"],
        "language": record["language"],
        "keywords": record["keywords"],
    }


def already_exists(
    collection,
    *,
    eid: str,
    language: str,
    keyword: str,
) -> bool:
    return (
        collection.find_one(
            {
                "eid": eid,
                "language": language,
                "keywords": keyword,
            },
            {"_id": 1},
        )
        is not None
    )


def upsert_record(
    collection,
    record: dict[str, Any],
) -> str:
    """
    Returns:
        inserted
        updated
        unchanged
    """
    result = collection.update_one(
        mongo_identity(record),
        {
            "$set": record
        },
        upsert=True,
    )

    if result.upserted_id is not None:
        return "inserted"

    if result.modified_count > 0:
        return "updated"

    return "unchanged"



# ============================================================================
# AUDIT
# ============================================================================

AUDIT_COUNTER_KEYS = [
    "total_rows",
    "attempted",
    "content_extracted",
    "inserted",
    "updated",
    "unchanged",
    "mongo_writes_successful",
    "failed_mongo",
    "skipped_existing",
    "skipped_invalid",
    "malformed_csv",
    "skipped_empty",
    "failed_scrape",
]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def empty_counters() -> dict[str, int]:
    return {
        key: 0
        for key in AUDIT_COUNTER_KEYS
    }


def empty_language_stats() -> dict[str, dict[str, int]]:
    return {
        language: empty_counters()
        for language in sorted(
            set(LANGUAGE_BY_FOLDER.values())
        )
    }


def increment_counter(
    counters: dict[str, int],
    language_stats: dict[str, dict[str, int]],
    language: str,
    key: str,
    amount: int = 1,
) -> None:
    counters[key] += amount

    if language not in language_stats:
        language_stats[language] = empty_counters()

    language_stats[language][key] += amount


def get_git_commit() -> str | None:
    """
    Return the current Git commit when the script is executed inside a repo.
    """
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "--short",
                "HEAD",
            ],
            cwd=Path(__file__).resolve().parent,
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

        commit = result.stdout.strip()
        return commit or None

    except (
        OSError,
        subprocess.SubprocessError,
    ):
        return None


def prepare_audit_collection(
    client: MongoClient,
    database_name: str,
    collection_name: str,
):
    collection = client[
        database_name
    ][
        collection_name
    ]

    collection.create_index(
        [("run_id", ASCENDING)],
        unique=True,
        name="unique_run_id",
    )

    collection.create_index(
        [("started_at", ASCENDING)],
        name="started_at_idx",
    )

    collection.create_index(
        [("status", ASCENDING)],
        name="status_idx",
    )

    return collection


def start_audit_run(
    audit_collection,
    *,
    database_name: str,
    collection_name: str,
    audit_collection_name: str,
    whitelist_root: Path,
    csv_files_count: int,
    options: dict[str, Any],
) -> tuple[str, datetime, float]:
    run_id = str(uuid4())
    started_at = utc_now()
    started_monotonic = time.monotonic()

    document = {
        "run_id": run_id,
        "status": "running",
        "started_at": started_at,
        "finished_at": None,
        "duration_seconds": None,
        "source": {
            "whitelist": str(
                whitelist_root
            ),
            "csv_files": csv_files_count,
            "csv_files_processed": 0,
        },
        "target": {
            "database": database_name,
            "collection": collection_name,
            "audit_collection": (
                audit_collection_name
            ),
        },
        "options": options,
        "records": empty_counters(),
        "languages": empty_language_stats(),
        "git_commit": get_git_commit(),
        "host": socket.gethostname(),
        "error": None,
    }

    audit_collection.insert_one(
        document
    )

    logging.info(
        "Audit started | run_id=%s",
        run_id,
    )

    return (
        run_id,
        started_at,
        started_monotonic,
    )


def update_audit_progress(
    audit_collection,
    run_id: str,
    *,
    counters: dict[str, int],
    language_stats: dict[str, dict[str, int]],
    csv_files_processed: int,
) -> None:
    audit_collection.update_one(
        {
            "run_id": run_id
        },
        {
            "$set": {
                "records": counters,
                "languages": language_stats,
                "source.csv_files_processed": (
                    csv_files_processed
                ),
                "last_progress_at": utc_now(),
            }
        },
    )


def finish_audit_run(
    audit_collection,
    run_id: str,
    *,
    status: str,
    started_monotonic: float,
    counters: dict[str, int],
    language_stats: dict[str, dict[str, int]],
    csv_files_processed: int,
    error: dict[str, str] | None = None,
) -> None:
    finished_at = utc_now()

    duration_seconds = round(
        time.monotonic()
        - started_monotonic,
        3,
    )

    audit_collection.update_one(
        {
            "run_id": run_id
        },
        {
            "$set": {
                "status": status,
                "finished_at": finished_at,
                "duration_seconds": (
                    duration_seconds
                ),
                "records": counters,
                "languages": language_stats,
                "source.csv_files_processed": (
                    csv_files_processed
                ),
                "error": error,
            }
        },
    )

    logging.info(
        "Audit finished | run_id=%s | "
        "status=%s | duration=%.3fs",
        run_id,
        status,
        duration_seconds,
    )

# ============================================================================
# PER-DOMAIN RATE LIMITING
# ============================================================================

class DomainRateLimiter:
    def __init__(
        self,
        delay_seconds: float,
    ) -> None:
        self.delay_seconds = (
            delay_seconds
        )

        self.last_request: dict[
            str,
            float,
        ] = {}

    def wait(
        self,
        url: str,
    ) -> None:
        domain = domain_from_url(
            url
        )

        if not domain:
            return

        now = time.monotonic()

        previous = (
            self.last_request
            .get(domain)
        )

        if previous is not None:
            elapsed = (
                now - previous
            )

            remaining = (
                self.delay_seconds
                - elapsed
            )

            if remaining > 0:
                time.sleep(
                    remaining
                )

        self.last_request[
            domain
        ] = time.monotonic()


# ============================================================================
# ROBOTS.TXT
# ============================================================================

class RobotsCache:
    """
    robots.txt is checked once per origin.

    Important:
    it uses a short timeout and NO retry loop so a broken robots.txt
    endpoint cannot stall the whole pipeline for several minutes.
    """

    def __init__(
        self,
        limiter: DomainRateLimiter,
        timeout: float = 5.0,
    ) -> None:
        self.limiter = limiter
        self.timeout = timeout

        self.cache: dict[
            str,
            RobotFileParser | None,
        ] = {}

        # Dedicated session WITHOUT retry adapter.
        self.session = (
            requests.Session()
        )

        self.session.headers.update(
            REQUEST_HEADERS
        )

    def can_fetch(
        self,
        url: str,
    ) -> bool:
        parsed = urlparse(
            url
        )

        origin = (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
        )

        if origin in self.cache:
            parser = self.cache[
                origin
            ]

            return (
                True
                if parser is None
                else parser.can_fetch(
                    "*",
                    url,
                )
            )

        robots_url = (
            origin
            + "/robots.txt"
        )

        try:
            self.limiter.wait(
                robots_url
            )

            response = (
                self.session.get(
                    robots_url,
                    timeout=(
                        self.timeout,
                        self.timeout,
                    ),
                )
            )

            if (
                response.status_code
                == 200
            ):
                parser = (
                    RobotFileParser()
                )

                parser.set_url(
                    robots_url
                )

                parser.parse(
                    response.text
                    .splitlines()
                )

                self.cache[
                    origin
                ] = parser

                return (
                    parser.can_fetch(
                        "*",
                        url,
                    )
                )

            self.cache[
                origin
            ] = None

            return True

        except requests.RequestException:
            logging.warning(
                "robots.txt unavailable for %s; "
                "continuing with article.",
                origin,
            )

            self.cache[
                origin
            ] = None

            return True

    def close(
        self,
    ) -> None:
        self.session.close()


# ============================================================================
# HTTP SESSION
# ============================================================================

def create_http_session() -> requests.Session:
    session = requests.Session()

    session.headers.update(
        REQUEST_HEADERS
    )

    # One retry for temporary network/server errors.
    retry_strategy = Retry(
        total=1,
        connect=1,
        read=1,
        status=1,
        backoff_factor=1,
        status_forcelist=(
            TRANSIENT_STATUS_CODES
        ),
        allowed_methods=frozenset(
            ["GET"]
        ),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,
        pool_maxsize=20,
    )

    session.mount(
        "http://",
        adapter,
    )

    session.mount(
        "https://",
        adapter,
    )

    return session


# ============================================================================
# CONTENT EXTRACTION
# ============================================================================

def extract_content_from_html(
    soup: BeautifulSoup,
) -> str | None:
    selectors = [
        "[itemprop='articleBody']",
        "article",
        ".article-body",
        ".article-content",
        ".article__body",
        ".entry-content",
        ".post-content",
        ".story-body",
        ".story-content",
        ".nota-contenido",
        ".contenido-nota",
        ".content-body",
        ".article-text",
    ]

    for selector in selectors:
        container = (
            soup.select_one(
                selector
            )
        )

        if not container:
            continue

        paragraphs: list[
            str
        ] = []

        for paragraph in (
            container.find_all(
                "p"
            )
        ):
            text = clean_text(
                paragraph.get_text(
                    " ",
                    strip=True,
                )
            )

            if (
                text
                and len(text) >= 30
            ):
                paragraphs.append(
                    text
                )

        if paragraphs:
            return "\n\n".join(
                paragraphs
            )

    return None


def extract_content(
    html: str,
) -> str | None:
    content = trafilatura.extract(
        html,
        output_format="txt",
        include_comments=False,
        include_tables=False,
        include_links=False,
        include_images=False,
        favor_precision=True,
    )

    if content:
        content = clean_text(
            content
        )

        if (
            content
            and len(content) >= 100
        ):
            return content

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return (
        extract_content_from_html(
            soup
        )
    )


# ============================================================================
# PLAYWRIGHT FALLBACK FOR 403
# ============================================================================

class BrowserFallback:
    def __init__(
        self,
        timeout_seconds: int,
    ) -> None:
        self.timeout_ms = (
            timeout_seconds
            * 1000
        )

        self.playwright = None
        self.browser = None
        self.context = None
        self.available = True

    def _ensure_started(
        self,
    ) -> bool:
        if not self.available:
            return False

        if self.browser is not None:
            return True

        try:
            from playwright.sync_api import (
                sync_playwright,
            )

            self.playwright = (
                sync_playwright()
                .start()
            )

            self.browser = (
                self.playwright
                .chromium
                .launch(
                    headless=True
                )
            )

            self.context = (
                self.browser
                .new_context(
                    user_agent=(
                        REQUEST_HEADERS[
                            "User-Agent"
                        ]
                    ),
                    locale="en-US",
                    extra_http_headers={
                        "Accept-Language":
                            REQUEST_HEADERS[
                                "Accept-Language"
                            ],
                    },
                )
            )

            return True

        except Exception as exc:
            logging.warning(
                "Playwright fallback unavailable: %s",
                exc,
            )

            logging.warning(
                "Install with: "
                "pip install playwright && "
                "playwright install chromium"
            )

            self.available = False
            return False

    def fetch_html(
        self,
        url: str,
    ) -> str | None:
        if not self._ensure_started():
            return None

        page = (
            self.context
            .new_page()
        )

        try:
            logging.info(
                "403 received. Trying browser fallback: %s",
                url,
            )

            response = page.goto(
                url,
                wait_until=(
                    "domcontentloaded"
                ),
                timeout=self.timeout_ms,
            )

            if response is not None:
                status = (
                    response.status
                )

                if status >= 400:
                    logging.warning(
                        "Browser fallback returned HTTP %d: %s",
                        status,
                        url,
                    )
                    return None

            page.wait_for_timeout(
                1500
            )

            html = (
                page.content()
            )

            if looks_like_block_page(
                html
            ):
                logging.warning(
                    "Browser challenge/paywall detected. "
                    "Skipping: %s",
                    url,
                )
                return None

            return html

        except Exception as exc:
            logging.error(
                "Browser fallback failed for %s: %s",
                url,
                exc,
            )

            return None

        finally:
            page.close()

    def close(
        self,
    ) -> None:
        try:
            if self.context is not None:
                self.context.close()

            if self.browser is not None:
                self.browser.close()

            if self.playwright is not None:
                self.playwright.stop()

        except Exception:
            pass


def looks_like_block_page(
    html: str,
) -> bool:
    lowered = html.lower()

    markers = [
        "captcha",
        "verify you are human",
        "checking your browser",
        "access denied",
        "enable javascript and cookies",
        "unusual traffic",
        "are you a robot",
        "robot check",
        "subscribe to continue",
        "sign in to continue",
    ]

    return any(
        marker in lowered
        for marker in markers
    )


# ============================================================================
# ARTICLE DOWNLOAD
# ============================================================================

def download_article(
    session: requests.Session,
    browser: BrowserFallback,
    limiter: DomainRateLimiter,
    robots: RobotsCache,
    url: str,
    timeout: int,
) -> str | None:
    if not robots.can_fetch(
        url
    ):
        logging.warning(
            "robots.txt does not allow fetching: %s",
            url,
        )

        return None

    limiter.wait(
        url
    )

    response = session.get(
        url,
        timeout=(
            10,
            timeout,
        ),
        allow_redirects=True,
    )

    if (
        response.status_code
        == 403
    ):
        html = (
            browser.fetch_html(
                url
            )
        )

        if not html:
            return None

        return extract_content(
            html
        )

    if (
        response.status_code
        == 429
    ):
        logging.warning(
            "Still rate-limited after retry (429): %s",
            url,
        )

        return None

    if (
        400
        <= response.status_code
        < 500
    ):
        logging.warning(
            "HTTP %d. Skipping: %s",
            response.status_code,
            url,
        )

        return None

    response.raise_for_status()

    return extract_content(
        response.text
    )


# ============================================================================
# WHITELIST PATH METADATA
# ============================================================================

def language_from_csv_path(
    csv_path: Path,
    whitelist_root: Path,
) -> str:
    relative = csv_path.relative_to(
        whitelist_root
    )

    if len(relative.parts) < 2:
        raise ValueError(
            "CSV must be inside a "
            f"language folder: {csv_path}"
        )

    language_folder = (
        relative.parts[0]
        .lower()
    )

    if (
        language_folder
        not in LANGUAGE_BY_FOLDER
    ):
        supported = ", ".join(
            LANGUAGE_BY_FOLDER
        )

        raise ValueError(
            f"Unknown language folder "
            f"'{language_folder}' for "
            f"{csv_path}. Supported: "
            f"{supported}"
        )

    return (
        LANGUAGE_BY_FOLDER[
            language_folder
        ]
    )


def keyword_from_csv_path(
    csv_path: Path,
) -> str:
    return csv_path.stem


def find_csv_files(
    whitelist_root: Path,
) -> list[Path]:
    return sorted(
        path
        for path
        in whitelist_root.rglob(
            "*.csv"
        )
        if path.is_file()
    )


# ============================================================================
# CSV READING
# ============================================================================

def detect_dialect(
    csv_path: Path,
) -> csv.Dialect:
    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        sample = file.read(
            8192
        )

    try:
        return csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|",
        )

    except csv.Error:
        return csv.excel


def read_csv_rows(
    csv_path: Path,
) -> tuple[
    list[str],
    list[
        tuple[int, dict[str, str]]
    ],
    int,
]:
    dialect = detect_dialect(
        csv_path
    )

    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        reader = csv.DictReader(
            file,
            dialect=dialect,
        )

        raw_headers = (
            reader.fieldnames
            or []
        )

        normalized_headers = [
            normalize_header(
                header
            )
            for header in raw_headers
        ]

        if not normalized_headers:
            raise ValueError(
                f"CSV has no header: "
                f"{csv_path}"
            )

        rows: list[
            tuple[
                int,
                dict[str, str],
            ]
        ] = []

        malformed_count = 0

        for raw_row in reader:
            # reader.line_num is the physical CSV line reached by the parser.
            line_number = reader.line_num

            if raw_row.get(
                None
            ):
                malformed_count += 1

                logging.error(
                    "%s:%d malformed CSV row "
                    "(extra columns, likely an unquoted comma). "
                    "Skipping row.",
                    csv_path,
                    line_number,
                )

                continue

            normalized_row: dict[
                str,
                str,
            ] = {}

            for (
                raw_key,
                value,
            ) in raw_row.items():
                key = (
                    normalize_header(
                        raw_key
                    )
                )

                if key:
                    normalized_row[
                        key
                    ] = value

            rows.append(
                (
                    line_number,
                    normalized_row,
                )
            )

    return (
        normalized_headers,
        rows,
        malformed_count,
    )


def validate_columns(
    fieldnames: list[str],
    csv_path: Path,
) -> None:
    required = set(
        WHITELIST_FIELDS
    )

    available = set(
        fieldnames
    )

    missing = sorted(
        required
        - available
    )

    if missing:
        raise ValueError(
            f"\nCSV inválido: "
            f"{csv_path}\n"
            f"Columnas detectadas: "
            f"{sorted(available)}\n"
            f"Columnas faltantes: "
            f"{missing}\n"
            f"Se acepta 'id' o "
            f"'eid' para el identificador."
        )


# ============================================================================
# DOCUMENT BUILDING
# ============================================================================

def build_record(
    row: dict[str, str],
    *,
    language: str,
    keyword: str,
    content: str | None,
) -> dict[str, Any]:
    record: dict[
        str,
        Any,
    ] = {}

    for field in (
        WHITELIST_FIELDS
    ):
        value = row.get(
            field
        )

        if isinstance(
            value,
            str,
        ):
            value = (
                value.strip()
                or None
            )

        record[
            field
        ] = value

    record[
        "language"
    ] = language

    record[
        "keywords"
    ] = keyword

    record[
        "hash"
    ] = hash_url(
        record["url"]
    )

    record[
        "contenido"
    ] = content

    return record


def validate_record(
    record: dict[str, Any],
) -> tuple[
    bool,
    str | None,
]:
    if not record.get(
        "eid"
    ):
        return (
            False,
            "empty eid",
        )

    if not record.get(
        "language"
    ):
        return (
            False,
            "empty language",
        )

    if not record.get(
        "keywords"
    ):
        return (
            False,
            "empty keywords",
        )

    if not record.get(
        "url"
    ):
        return (
            False,
            "empty url",
        )

    return (
        True,
        None,
    )


# ============================================================================
# SCRAPE -> MONGO PIPELINE
# ============================================================================

def process_whitelist_to_mongo(
    whitelist_root: Path,
    collection,
    *,
    counters: dict[str, int],
    language_stats: dict[str, dict[str, int]],
    progress_state: dict[str, int],
    audit_collection=None,
    run_id: str | None = None,
    audit_progress_every: int = 100,
    delay: float = 2.5,
    timeout: int = 20,
    robots_timeout: float = 5.0,
    resume: bool = False,
    skip_empty_content: bool = False,
) -> int:
    csv_files = find_csv_files(
        whitelist_root
    )

    if not csv_files:
        raise FileNotFoundError(
            "No CSV files found inside: "
            f"{whitelist_root}"
        )

    logging.info(
        "Found %d whitelist CSV files.",
        len(csv_files),
    )

    session = (
        create_http_session()
    )

    limiter = (
        DomainRateLimiter(
            delay_seconds=delay
        )
    )

    robots = RobotsCache(
        limiter=limiter,
        timeout=robots_timeout,
    )

    browser = BrowserFallback(
        timeout_seconds=timeout
    )

    progress_events = 0

    def checkpoint() -> None:
        nonlocal progress_events

        progress_events += 1

        if (
            audit_collection is None
            or run_id is None
            or audit_progress_every <= 0
        ):
            return

        if (
            progress_events
            % audit_progress_every
            != 0
        ):
            return

        try:
            update_audit_progress(
                audit_collection,
                run_id,
                counters=counters,
                language_stats=(
                    language_stats
                ),
                csv_files_processed=(
                    progress_state[
                        "csv_files_processed"
                    ]
                ),
            )

        except PyMongoError as exc:
            # Audit progress failure should not discard successfully
            # scraped news. The final audit update will be attempted again.
            logging.error(
                "Could not update audit progress: %s",
                exc,
            )

    try:
        for csv_path in csv_files:
            language = (
                language_from_csv_path(
                    csv_path,
                    whitelist_root,
                )
            )

            keyword = (
                keyword_from_csv_path(
                    csv_path
                )
            )

            logging.info(
                "Reading %s | language=%s | keywords=%s",
                csv_path,
                language,
                keyword,
            )

            (
                fieldnames,
                rows,
                malformed_count,
            ) = read_csv_rows(
                csv_path
            )

            validate_columns(
                fieldnames,
                csv_path,
            )

            total_rows_in_file = (
                len(rows)
                + malformed_count
            )

            increment_counter(
                counters,
                language_stats,
                language,
                "total_rows",
                total_rows_in_file,
            )

            if malformed_count:
                increment_counter(
                    counters,
                    language_stats,
                    language,
                    "malformed_csv",
                    malformed_count,
                )

                increment_counter(
                    counters,
                    language_stats,
                    language,
                    "skipped_invalid",
                    malformed_count,
                )

            logging.info(
                "Detected columns: %s",
                ", ".join(
                    fieldnames
                ),
            )

            for (
                row_number,
                row,
            ) in rows:
                url = (
                    row.get(
                        "url"
                    )
                    or ""
                ).strip()

                eid = (
                    row.get(
                        "eid"
                    )
                    or ""
                ).strip()

                if not eid:
                    logging.error(
                        "%s:%d empty eid. Skipping.",
                        csv_path,
                        row_number,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_invalid",
                    )

                    checkpoint()
                    continue

                if not url:
                    logging.error(
                        "%s:%d empty URL. Skipping.",
                        csv_path,
                        row_number,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_invalid",
                    )

                    checkpoint()
                    continue

                if not is_valid_http_url(
                    url
                ):
                    logging.error(
                        "%s:%d invalid URL: %r. Skipping.",
                        csv_path,
                        row_number,
                        url,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_invalid",
                    )

                    checkpoint()
                    continue

                if (
                    resume
                    and already_exists(
                        collection,
                        eid=eid,
                        language=language,
                        keyword=keyword,
                    )
                ):
                    logging.info(
                        "Already in MongoDB, skipping: "
                        "eid=%s | language=%s | keywords=%s",
                        eid,
                        language,
                        keyword,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_existing",
                    )

                    checkpoint()
                    continue

                increment_counter(
                    counters,
                    language_stats,
                    language,
                    "attempted",
                )

                logging.info(
                    "Scraping: %s",
                    url,
                )

                content = None

                try:
                    content = (
                        download_article(
                            session=session,
                            browser=browser,
                            limiter=limiter,
                            robots=robots,
                            url=url,
                            timeout=timeout,
                        )
                    )

                    if content:
                        increment_counter(
                            counters,
                            language_stats,
                            language,
                            "content_extracted",
                        )

                        logging.info(
                            "Content extracted: %d chars",
                            len(content),
                        )

                    else:
                        increment_counter(
                            counters,
                            language_stats,
                            language,
                            "failed_scrape",
                        )

                        logging.warning(
                            "No content extracted: %s",
                            url,
                        )

                except requests.RequestException as exc:
                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "failed_scrape",
                    )

                    logging.error(
                        "HTTP error for %s: %s",
                        url,
                        exc,
                    )

                except Exception as exc:
                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "failed_scrape",
                    )

                    logging.exception(
                        "Unexpected scraping error "
                        "for %s: %s",
                        url,
                        exc,
                    )

                record = build_record(
                    row,
                    language=language,
                    keyword=keyword,
                    content=content,
                )

                valid, error = (
                    validate_record(
                        record
                    )
                )

                if not valid:
                    logging.error(
                        "Invalid document after scraping: %s",
                        error,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_invalid",
                    )

                    checkpoint()
                    continue

                if (
                    skip_empty_content
                    and not content
                ):
                    logging.warning(
                        "Not uploading because contenido is empty: %s",
                        url,
                    )

                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "skipped_empty",
                    )

                    checkpoint()
                    continue

                try:
                    status = (
                        upsert_record(
                            collection,
                            record,
                        )
                    )

                except PyMongoError as exc:
                    increment_counter(
                        counters,
                        language_stats,
                        language,
                        "failed_mongo",
                    )

                    logging.error(
                        "MongoDB write failed for eid=%s: %s",
                        eid,
                        exc,
                    )

                    checkpoint()
                    raise

                increment_counter(
                    counters,
                    language_stats,
                    language,
                    status,
                )

                increment_counter(
                    counters,
                    language_stats,
                    language,
                    "mongo_writes_successful",
                )

                logging.info(
                    "MongoDB %s | eid=%s | language=%s | keywords=%s",
                    status.upper(),
                    eid,
                    language,
                    keyword,
                )

                checkpoint()

            progress_state[
                "csv_files_processed"
            ] += 1

            if (
                audit_collection is not None
                and run_id is not None
            ):
                try:
                    update_audit_progress(
                        audit_collection,
                        run_id,
                        counters=counters,
                        language_stats=(
                            language_stats
                        ),
                        csv_files_processed=(
                            progress_state[
                                "csv_files_processed"
                            ]
                        ),
                    )

                except PyMongoError as exc:
                    logging.error(
                        "Could not update audit progress after CSV: %s",
                        exc,
                    )

    finally:
        browser.close()
        robots.close()
        session.close()

    logging.info(
        "Pipeline finished | "
        "total_rows=%d | "
        "attempted=%d | "
        "content_extracted=%d | "
        "mongo_writes_successful=%d | "
        "inserted=%d | "
        "updated=%d | "
        "unchanged=%d | "
        "skipped_existing=%d | "
        "skipped_invalid=%d | "
        "malformed_csv=%d | "
        "skipped_empty=%d | "
        "failed_scrape=%d | "
        "failed_mongo=%d",
        counters["total_rows"],
        counters["attempted"],
        counters["content_extracted"],
        counters["mongo_writes_successful"],
        counters["inserted"],
        counters["updated"],
        counters["unchanged"],
        counters["skipped_existing"],
        counters["skipped_invalid"],
        counters["malformed_csv"],
        counters["skipped_empty"],
        counters["failed_scrape"],
        counters["failed_mongo"],
    )

    return progress_state[
        "csv_files_processed"
    ]


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description=(
            "Scrape whitelist news, upload each document "
            "directly to MongoDB Atlas, and audit every run."
        )
    )

    parser.add_argument(
        "--whitelist",
        default="white_list",
        help=(
            "Root whitelist directory. "
            "Default: white_list"
        ),
    )

    parser.add_argument(
        "--database",
        default=os.getenv(
            "MONGODB_DATABASE",
            "dragons_app",
        ),
        help=(
            "MongoDB database. "
            "Default: MONGODB_DATABASE"
        ),
    )

    parser.add_argument(
        "--collection",
        default=os.getenv(
            "MONGODB_COLLECTION",
            "news",
        ),
        help=(
            "MongoDB news collection. "
            "Default: MONGODB_COLLECTION"
        ),
    )

    parser.add_argument(
        "--audit-collection",
        default=os.getenv(
            "MONGODB_AUDIT_COLLECTION",
            "audit_runs",
        ),
        help=(
            "MongoDB audit collection. "
            "Default: audit_runs"
        ),
    )

    parser.add_argument(
        "--audit-progress-every",
        type=int,
        default=100,
        help=(
            "Save an audit progress snapshot every N processed "
            "rows. Use 0 to disable periodic snapshots. "
            "Default: 100"
        ),
    )

    parser.add_argument(
        "--delay",
        type=float,
        default=2.5,
        help=(
            "Minimum seconds between requests "
            "to the same domain. Default: 2.5"
        ),
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=20,
        help=(
            "Article/browser timeout in seconds. "
            "Default: 20"
        ),
    )

    parser.add_argument(
        "--robots-timeout",
        type=float,
        default=5.0,
        help=(
            "robots.txt timeout in seconds. "
            "Default: 5"
        ),
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Skip documents that already exist "
            "in MongoDB using eid + language + keywords."
        ),
    )

    parser.add_argument(
        "--skip-empty-content",
        action="store_true",
        help=(
            "Do not upload records where "
            "contenido could not be extracted."
        ),
    )

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format=(
            "%(asctime)s | %(levelname)s | "
            "%(message)s"
        ),
    )

    uri = os.getenv(
        "MONGODB_URI"
    )

    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not configured in .env"
        )

    whitelist_root = Path(
        args.whitelist
    ).resolve()

    csv_files = find_csv_files(
        whitelist_root
    )

    if not csv_files:
        raise FileNotFoundError(
            "No CSV files found inside: "
            f"{whitelist_root}"
        )

    counters = empty_counters()
    language_stats = (
        empty_language_stats()
    )

    client = None
    audit_collection = None
    run_id = None
    started_monotonic = None
    progress_state = {
        "csv_files_processed": 0
    }

    try:
        logging.info(
            "Connecting to MongoDB Atlas..."
        )

        client = create_mongo_client(
            uri
        )

        logging.info(
            "MongoDB connection successful."
        )

        # Prepare audit first so setup/runtime failures after connection
        # can also be recorded.
        audit_collection = (
            prepare_audit_collection(
                client,
                args.database,
                args.audit_collection,
            )
        )

        (
            run_id,
            _started_at,
            started_monotonic,
        ) = start_audit_run(
            audit_collection,
            database_name=args.database,
            collection_name=args.collection,
            audit_collection_name=(
                args.audit_collection
            ),
            whitelist_root=whitelist_root,
            csv_files_count=len(
                csv_files
            ),
            options={
                "resume": args.resume,
                "skip_empty_content": (
                    args.skip_empty_content
                ),
                "delay_seconds": args.delay,
                "timeout_seconds": args.timeout,
                "robots_timeout_seconds": (
                    args.robots_timeout
                ),
                "audit_progress_every": (
                    args.audit_progress_every
                ),
            },
        )

        collection = prepare_collection(
            client,
            args.database,
            args.collection,
        )

        logging.info(
            "Target: %s.%s",
            args.database,
            args.collection,
        )

        logging.info(
            "Audit collection: %s.%s",
            args.database,
            args.audit_collection,
        )

        process_whitelist_to_mongo(
                whitelist_root,
                collection,
                counters=counters,
                language_stats=(
                    language_stats
                ),
                progress_state=(
                    progress_state
                ),
                audit_collection=(
                    audit_collection
                ),
                run_id=run_id,
                audit_progress_every=(
                    args.audit_progress_every
                ),
                delay=args.delay,
                timeout=args.timeout,
                robots_timeout=(
                    args.robots_timeout
                ),
                resume=args.resume,
                skip_empty_content=(
                    args.skip_empty_content
                ),
            )

        finish_audit_run(
            audit_collection,
            run_id,
            status="completed",
            started_monotonic=(
                started_monotonic
            ),
            counters=counters,
            language_stats=(
                language_stats
            ),
            csv_files_processed=(
                progress_state[
                    "csv_files_processed"
                ]
            ),
        )

    except KeyboardInterrupt:
        logging.warning(
            "Execution interrupted by user."
        )

        if (
            audit_collection is not None
            and run_id is not None
            and started_monotonic is not None
        ):
            try:
                finish_audit_run(
                    audit_collection,
                    run_id,
                    status="interrupted",
                    started_monotonic=(
                        started_monotonic
                    ),
                    counters=counters,
                    language_stats=(
                        language_stats
                    ),
                    csv_files_processed=(
                        progress_state[
                            "csv_files_processed"
                        ]
                    ),
                    error={
                        "type": (
                            "KeyboardInterrupt"
                        ),
                        "message": (
                            "Execution interrupted "
                            "by user."
                        ),
                    },
                )

            except PyMongoError as audit_exc:
                logging.error(
                    "Could not finalize interrupted audit: %s",
                    audit_exc,
                )

    except Exception as exc:
        logging.exception(
            "Pipeline failed: %s",
            exc,
        )

        if (
            audit_collection is not None
            and run_id is not None
            and started_monotonic is not None
        ):
            try:
                finish_audit_run(
                    audit_collection,
                    run_id,
                    status="failed",
                    started_monotonic=(
                        started_monotonic
                    ),
                    counters=counters,
                    language_stats=(
                        language_stats
                    ),
                    csv_files_processed=(
                        progress_state[
                            "csv_files_processed"
                        ]
                    ),
                    error={
                        "type": (
                            type(exc).__name__
                        ),
                        "message": str(exc)[
                            :2000
                        ],
                    },
                )

            except PyMongoError as audit_exc:
                logging.error(
                    "Could not finalize failed audit: %s",
                    audit_exc,
                )

        raise

    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

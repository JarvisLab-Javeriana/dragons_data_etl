from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
import trafilatura
from bs4 import BeautifulSoup
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

# Metadata copied ONLY from the whitelist CSV.
# language is derived from the folder.
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
# HELPERS
# ============================================================================

def clean_text(value: Any) -> str | None:
    if value is None:
        return None

    text = re.sub(r"[ \t\r\f\v]+", " ", str(value))
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text or None


def normalize_header(header: str | None) -> str:
    if header is None:
        return ""

    normalized = (
        header.replace("\ufeff", "")
        .strip()
        .lower()
    )

    return HEADER_ALIASES.get(normalized, normalized)


def is_valid_http_url(url: str) -> bool:
    try:
        parsed = urlparse(url)

        return (
            parsed.scheme in {"http", "https"}
            and bool(parsed.netloc)
        )
    except ValueError:
        return False


def domain_from_url(url: str) -> str:
    return urlparse(url).netloc.lower()


# ============================================================================
# PER-DOMAIN RATE LIMITING
# ============================================================================

class DomainRateLimiter:
    """
    Ensures a minimum delay between requests to the same domain.

    Different domains do not share the same timer.
    """

    def __init__(self, delay_seconds: float) -> None:
        self.delay_seconds = delay_seconds
        self.last_request: dict[str, float] = {}

    def wait(self, url: str) -> None:
        domain = domain_from_url(url)

        if not domain:
            return

        now = time.monotonic()
        previous = self.last_request.get(domain)

        if previous is not None:
            elapsed = now - previous
            remaining = self.delay_seconds - elapsed

            if remaining > 0:
                logging.debug(
                    "Rate limit: waiting %.2fs for %s",
                    remaining,
                    domain,
                )
                time.sleep(remaining)

        self.last_request[domain] = time.monotonic()


# ============================================================================
# ROBOTS.TXT
# ============================================================================

class RobotsCache:
    """
    Cache robots.txt by origin so it is not downloaded for every article.
    """

    def __init__(
        self,
        session: requests.Session,
        limiter: DomainRateLimiter,
        timeout: int,
    ) -> None:
        self.session = session
        self.limiter = limiter
        self.timeout = timeout
        self.cache: dict[str, RobotFileParser | None] = {}

    def can_fetch(self, url: str) -> bool:
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"

        if origin in self.cache:
            parser = self.cache[origin]
            return True if parser is None else parser.can_fetch("*", url)

        robots_url = origin + "/robots.txt"

        try:
            self.limiter.wait(robots_url)

            response = self.session.get(
                robots_url,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.parse(response.text.splitlines())
                self.cache[origin] = parser

                return parser.can_fetch("*", url)

            # If robots.txt is not available, continue conservatively
            # without trying to interpret the missing file.
            self.cache[origin] = None
            return True

        except requests.RequestException:
            self.cache[origin] = None
            return True


# ============================================================================
# REQUESTS SESSION WITH RETRIES
# ============================================================================

def create_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(REQUEST_HEADERS)

    retry_strategy = Retry(
        total=3,
        connect=3,
        read=3,
        status=3,
        backoff_factor=2,
        status_forcelist=TRANSIENT_STATUS_CODES,
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(
        max_retries=retry_strategy,
        pool_connections=20,
        pool_maxsize=20,
    )

    session.mount("http://", adapter)
    session.mount("https://", adapter)

    return session


# ============================================================================
# ARTICLE CONTENT EXTRACTION
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
        container = soup.select_one(selector)

        if not container:
            continue

        paragraphs: list[str] = []

        for paragraph in container.find_all("p"):
            text = clean_text(
                paragraph.get_text(" ", strip=True)
            )

            if text and len(text) >= 30:
                paragraphs.append(text)

        if paragraphs:
            return "\n\n".join(paragraphs)

    return None


def extract_content(html: str) -> str | None:
    """
    Main extraction:
    1. Trafilatura
    2. BeautifulSoup article-body fallback
    """

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
        content = clean_text(content)

        if content and len(content) >= 100:
            return content

    soup = BeautifulSoup(
        html,
        "html.parser",
    )

    return extract_content_from_html(soup)


# ============================================================================
# PLAYWRIGHT FALLBACK
# ============================================================================

class BrowserFallback:
    """
    Lazy Playwright browser.

    It is launched only if a site returns HTTP 403 through requests.

    This does NOT try to solve CAPTCHAs, bypass paywalls, log in, or defeat
    explicit anti-bot challenges.
    """

    def __init__(self, timeout_seconds: int) -> None:
        self.timeout_ms = timeout_seconds * 1000
        self.playwright = None
        self.browser = None
        self.context = None
        self.available = True

    def _ensure_started(self) -> bool:
        if not self.available:
            return False

        if self.browser is not None:
            return True

        try:
            from playwright.sync_api import sync_playwright

            self.playwright = sync_playwright().start()

            self.browser = self.playwright.chromium.launch(
                headless=True,
            )

            self.context = self.browser.new_context(
                user_agent=REQUEST_HEADERS["User-Agent"],
                locale="en-US",
                extra_http_headers={
                    "Accept-Language": REQUEST_HEADERS[
                        "Accept-Language"
                    ],
                },
            )

            return True

        except Exception as exc:
            logging.warning(
                "Playwright fallback unavailable: %s",
                exc,
            )

            logging.warning(
                "Install it with: "
                "pip install playwright && "
                "playwright install chromium"
            )

            self.available = False
            return False

    def fetch_html(self, url: str) -> str | None:
        if not self._ensure_started():
            return None

        page = self.context.new_page()

        try:
            logging.info(
                "403 received. Trying browser fallback: %s",
                url,
            )

            response = page.goto(
                url,
                wait_until="domcontentloaded",
                timeout=self.timeout_ms,
            )

            if response is not None:
                status = response.status

                if status >= 400:
                    logging.warning(
                        "Browser fallback returned HTTP %d: %s",
                        status,
                        url,
                    )
                    return None

            # Small wait for normal client-side rendering.
            page.wait_for_timeout(1500)

            html = page.content()

            if looks_like_block_page(html):
                logging.warning(
                    "Browser challenge/paywall detected. "
                    "Skipping instead of bypassing it: %s",
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

    def close(self) -> None:
        try:
            if self.context is not None:
                self.context.close()

            if self.browser is not None:
                self.browser.close()

            if self.playwright is not None:
                self.playwright.stop()

        except Exception:
            pass


def looks_like_block_page(html: str) -> bool:
    """
    Avoid storing obvious CAPTCHA / anti-bot / subscription screens
    as if they were article content.
    """

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
# DOWNLOAD STRATEGY
# ============================================================================

def download_article(
    session: requests.Session,
    browser: BrowserFallback,
    limiter: DomainRateLimiter,
    robots: RobotsCache,
    url: str,
    timeout: int,
) -> str | None:
    """
    Strategy:

        requests
            |
            +-- 200 ------> extract content
            |
            +-- 429/5xx --> automatic retry/backoff
            |
            +-- 403 ------> Playwright fallback
            |
            +-- other 4xx -> skip
    """

    if not robots.can_fetch(url):
        logging.warning(
            "robots.txt does not allow fetching: %s",
            url,
        )
        return None

    limiter.wait(url)

    response = session.get(
        url,
        timeout=timeout,
        allow_redirects=True,
    )

    if response.status_code == 403:
        html = browser.fetch_html(url)

        if not html:
            return None

        return extract_content(html)

    if response.status_code == 429:
        logging.warning(
            "Still rate-limited after retries (429): %s",
            url,
        )
        return None

    if 400 <= response.status_code < 500:
        logging.warning(
            "HTTP %d. Skipping: %s",
            response.status_code,
            url,
        )
        return None

    response.raise_for_status()

    content = extract_content(
        response.text
    )

    return content


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
            f"CSV must be inside a language folder: "
            f"{csv_path}"
        )

    language_folder = relative.parts[0].lower()

    if language_folder not in LANGUAGE_BY_FOLDER:
        supported = ", ".join(
            LANGUAGE_BY_FOLDER
        )

        raise ValueError(
            f"Unknown language folder "
            f"'{language_folder}' for {csv_path}. "
            f"Supported: {supported}"
        )

    return LANGUAGE_BY_FOLDER[
        language_folder
    ]


def keyword_from_csv_path(
    csv_path: Path,
) -> str:
    return csv_path.stem


def find_csv_files(
    whitelist_root: Path,
) -> list[Path]:
    return sorted(
        path
        for path in whitelist_root.rglob(
            "*.csv"
        )
        if path.is_file()
    )


# ============================================================================
# ROBUST CSV READING
# ============================================================================

def detect_dialect(
    csv_path: Path,
) -> csv.Dialect:
    with csv_path.open(
        "r",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        sample = file.read(8192)

    try:
        return csv.Sniffer().sniff(
            sample,
            delimiters=",;\t|",
        )

    except csv.Error:
        return csv.excel


def read_csv_rows(
    csv_path: Path,
) -> tuple[list[str], list[dict[str, str]]]:
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
            reader.fieldnames or []
        )

        normalized_headers = [
            normalize_header(header)
            for header in raw_headers
        ]

        if not normalized_headers:
            raise ValueError(
                f"CSV has no header: {csv_path}"
            )

        rows: list[dict[str, str]] = []

        for line_number, raw_row in enumerate(
            reader,
            start=2,
        ):
            # DictReader stores surplus unquoted CSV columns
            # under the None key.
            if raw_row.get(None):
                logging.error(
                    "%s:%d malformed CSV row "
                    "(extra columns, likely an unquoted comma). "
                    "Skipping row.",
                    csv_path,
                    line_number,
                )
                continue

            normalized_row: dict[str, str] = {}

            for raw_key, value in raw_row.items():
                key = normalize_header(
                    raw_key
                )

                if key:
                    normalized_row[key] = (
                        value
                    )

            rows.append(
                normalized_row
            )

    return (
        normalized_headers,
        rows,
    )


def validate_columns(
    fieldnames: list[str],
    csv_path: Path,
) -> None:
    # language deliberately NOT required.
    required = set(
        WHITELIST_FIELDS
    )

    available = set(
        fieldnames
    )

    missing = sorted(
        required - available
    )

    if missing:
        raise ValueError(
            f"\nCSV inválido: {csv_path}\n"
            f"Columnas detectadas: "
            f"{sorted(available)}\n"
            f"Columnas faltantes: "
            f"{missing}\n"
            f"Se acepta 'id' o 'eid' "
            f"para el identificador."
        )


# ============================================================================
# JSON CONSTRUCTION
# ============================================================================

def build_record(
    row: dict[str, str],
    *,
    language: str,
    keyword: str,
    content: str | None,
) -> dict:
    """
    Final JSON:
    - whitelist metadata
    - language from folder
    - keywords from CSV filename
    - contenido scraped from article
    """

    record: dict[str, Any] = {}

    for field in WHITELIST_FIELDS:
        value = row.get(
            field
        )

        if isinstance(value, str):
            value = (
                value.strip()
                or None
            )

        record[field] = value

    record["language"] = language
    record["keywords"] = keyword
    record["contenido"] = content

    return record


def load_existing_output(
    output_path: Path,
) -> list[dict]:
    if not output_path.exists():
        return []

    with output_path.open(
        "r",
        encoding="utf-8",
    ) as file:
        data = json.load(
            file
        )

    if not isinstance(
        data,
        list,
    ):
        raise ValueError(
            f"Existing output must be a "
            f"JSON array: {output_path}"
        )

    return data


def save_json(
    records: list[dict],
    output_path: Path,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temp_path = output_path.with_suffix(
        output_path.suffix + ".tmp"
    )

    with temp_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            records,
            file,
            ensure_ascii=False,
            indent=2,
        )

    temp_path.replace(
        output_path
    )


# ============================================================================
# MAIN PROCESS
# ============================================================================

def process_whitelist(
    whitelist_root: Path,
    output_path: Path,
    *,
    delay: float = 2.5,
    timeout: int = 25,
    resume: bool = False,
) -> list[dict]:

    csv_files = find_csv_files(
        whitelist_root
    )

    if not csv_files:
        raise FileNotFoundError(
            f"No CSV files found inside: "
            f"{whitelist_root}"
        )

    logging.info(
        "Found %d whitelist CSV files.",
        len(csv_files),
    )

    records = (
        load_existing_output(
            output_path
        )
        if resume
        else []
    )

    completed_keys = {
        (
            record.get("url"),
            record.get("keywords"),
            record.get("language"),
        )
        for record in records
    }

    session = create_session()

    limiter = DomainRateLimiter(
        delay_seconds=delay
    )

    robots = RobotsCache(
        session=session,
        limiter=limiter,
        timeout=timeout,
    )

    browser = BrowserFallback(
        timeout_seconds=timeout,
    )

    total_processed = 0

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
                "Reading %s | language=%s | "
                "keywords=%s",
                csv_path,
                language,
                keyword,
            )

            fieldnames, rows = (
                read_csv_rows(
                    csv_path
                )
            )

            validate_columns(
                fieldnames,
                csv_path,
            )

            logging.info(
                "Detected columns: %s",
                ", ".join(
                    fieldnames
                ),
            )

            for row_number, row in enumerate(
                rows,
                start=2,
            ):
                url = (
                    row.get("url")
                    or ""
                ).strip()

                if not url:
                    logging.warning(
                        "%s:%d has no URL. "
                        "Skipping.",
                        csv_path,
                        row_number,
                    )
                    continue

                if not is_valid_http_url(
                    url
                ):
                    logging.error(
                        "%s:%d invalid URL from CSV: %r. "
                        "Skipping.",
                        csv_path,
                        row_number,
                        url,
                    )
                    continue

                record_key = (
                    url,
                    keyword,
                    language,
                )

                if (
                    resume
                    and record_key
                    in completed_keys
                ):
                    logging.info(
                        "Already processed, skipping: %s",
                        url,
                    )
                    continue

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
                        logging.info(
                            "Content extracted: %d chars",
                            len(content),
                        )
                    else:
                        logging.warning(
                            "No content extracted: %s",
                            url,
                        )

                except requests.RequestException as exc:
                    logging.error(
                        "HTTP error for %s: %s",
                        url,
                        exc,
                    )

                except Exception as exc:
                    logging.exception(
                        "Unexpected error for %s: %s",
                        url,
                        exc,
                    )

                record = build_record(
                    row,
                    language=language,
                    keyword=keyword,
                    content=content,
                )

                records.append(
                    record
                )

                completed_keys.add(
                    record_key
                )

                total_processed += 1

                # Checkpoint after every article.
                save_json(
                    records,
                    output_path,
                )

    finally:
        browser.close()
        session.close()

    logging.info(
        "Finished. %d new records processed. "
        "%d total records written to %s",
        total_processed,
        len(records),
        output_path,
    )

    return records


# ============================================================================
# CLI
# ============================================================================

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Read whitelist CSV files, scrape article "
            "content, and produce normalized JSON."
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
        "--output",
        default="news.json",
        help=(
            "Destination JSON file. "
            "Default: news.json"
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
        default=25,
        help=(
            "HTTP/browser timeout in seconds. "
            "Default: 25"
        ),
    )

    parser.add_argument(
        "--resume",
        action="store_true",
        help=(
            "Continue from an existing JSON and "
            "skip already processed "
            "URL/keyword/language combinations."
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

    process_whitelist(
        Path(
            args.whitelist
        ).resolve(),
        Path(
            args.output
        ).resolve(),
        delay=args.delay,
        timeout=args.timeout,
        resume=args.resume,
    )


if __name__ == "__main__":
    main()

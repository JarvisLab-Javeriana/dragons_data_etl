from __future__ import annotations

import csv
import logging
import re
from datetime import date
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SAMPLE_ROW_LIMIT = 100

DEFAULT_EVENTS_CSV = Path("data/events/DRAGONS_T1.csv")

COUNTRY_LOCATION_TERMS: dict[str, list[str]] = {
    "United Kingdom": [
        "united kingdom",
        "uk",
        "britain",
        "england",
        "scotland",
        "wales",
        "northern ireland",
    ],
    "Hungary": ["hungary", "hungarian", "budapest"],
    "Colombia": ["colombia", "colombian", "bogota", "bogotá"],
}

_MONTHS = {
    "jan": 1,
    "january": 1,
    "feb": 2,
    "february": 2,
    "mar": 3,
    "march": 3,
    "apr": 4,
    "april": 4,
    "may": 5,
    "jun": 6,
    "june": 6,
    "jul": 7,
    "july": 7,
    "aug": 8,
    "august": 8,
    "sep": 9,
    "sept": 9,
    "september": 9,
    "oct": 10,
    "october": 10,
    "nov": 11,
    "november": 11,
    "dec": 12,
    "december": 12,
}

_YEAR_RANGE = re.compile(r"((?:19|20)\d{2})\s*[–\-]\s*((?:19|20)\d{2})")
_MONTH_RANGE = re.compile(
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|jul(?:y)?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"\s*[–\-]\s*"
    r"(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|jul(?:y)?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)",
    re.IGNORECASE,
)
_SINGLE_MONTH = re.compile(
    r"\b(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|june?|jul(?:y)?"
    r"|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)\b",
    re.IGNORECASE,
)
_YEAR = re.compile(r"\b((?:19|20)\d{2})\b")


def split_hooks(raw: str | None) -> list[str]:
    if not raw:
        return []
    return [part.strip() for part in str(raw).split(";") if part.strip()]


def _month_number(token: str) -> int:
    return _MONTHS[token.lower()]


def _first_of_next_month(year: int, month: int) -> date:
    if month == 12:
        return date(year + 1, 1, 1)
    return date(year, month + 1, 1)


def parse_event_period(period: str | None, year: int) -> tuple[date, date]:
    """Return inclusive-start / exclusive-end dates for BigQuery _PARTITIONTIME."""
    text = str(period or "").strip()
    year_range = _YEAR_RANGE.search(text)
    if year_range:
        start_year = int(year_range.group(1))
        end_year = int(year_range.group(2))
        return date(start_year, 1, 1), date(end_year + 1, 1, 1)

    month_range = _MONTH_RANGE.search(text)
    if month_range:
        start_month = _month_number(month_range.group(1))
        end_month = _month_number(month_range.group(2))
        start = date(year, start_month, 1)
        if end_month >= start_month:
            end = _first_of_next_month(year, end_month)
        else:
            end = _first_of_next_month(year + 1, end_month)
        return start, end

    single = _SINGLE_MONTH.search(text)
    if single:
        month = _month_number(single.group(1))
        return date(year, month, 1), _first_of_next_month(year, month)

    years = [int(match.group(1)) for match in _YEAR.finditer(text)]
    if len(years) >= 2:
        return date(min(years), 1, 1), date(max(years) + 1, 1, 1)
    if years:
        only = years[0]
        return date(only, 1, 1), date(only + 1, 1, 1)

    return date(year, 1, 1), date(year + 1, 1, 1)


def location_terms_for_country(country: str) -> list[str]:
    return list(COUNTRY_LOCATION_TERMS.get(country, [country.lower()] if country else []))


def _fallback_name(primary: str, fallback: str) -> str:
    value = (primary or "").strip()
    return value if value else fallback.strip()


def row_to_evento(row: dict[str, str]) -> dict[str, Any] | None:
    event_id = (row.get("ID") or "").strip()
    if not event_id:
        return None
    try:
        year = int(str(row.get("Year") or "").strip())
    except ValueError:
        logger.warning("Skipping event %s: invalid Year %r", event_id, row.get("Year"))
        return None

    name_en = (row.get("Event (EN)") or "").strip()
    if not name_en:
        logger.warning("Skipping event %s: missing Event (EN)", event_id)
        return None

    start, end = parse_event_period(row.get("Period"), year)
    return {
        "id": event_id,
        "pais": (row.get("Country") or "").strip(),
        "evento": {
            "en": name_en,
            "es": _fallback_name(row.get("Event (ES)") or "", name_en),
            "hu": _fallback_name(row.get("Event (HU)") or "", name_en),
        },
        "keywords": {
            "en": split_hooks(row.get("Keyword hooks (EN)")),
            "es": split_hooks(row.get("Keyword hooks (ES)")),
            "hu": split_hooks(row.get("Keyword hooks (HU)")),
        },
        "periodo": {
            "texto": (row.get("Period") or "").strip(),
            "start": start.isoformat(),
            "end": end.isoformat(),
        },
        "year": year,
        "spatial_level": (row.get("Spatial level") or "").strip(),
        "event_type": (row.get("Event type") or "").strip(),
        "source": (row.get("Source / starting point") or "").strip(),
    }


def _open_events_csv(path: Path):
    last_error: UnicodeDecodeError | None = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        handle = path.open("r", encoding=encoding, newline="")
        try:
            handle.read()
            handle.seek(0)
            return handle
        except UnicodeDecodeError as exc:
            last_error = exc
            handle.close()
    if last_error is not None:
        raise last_error
    raise OSError(f"Could not open events CSV: {path}")


def load_events_from_csv(path: str | Path = DEFAULT_EVENTS_CSV) -> list[dict[str, Any]]:
    csv_path = Path(path)
    events: list[dict[str, Any]] = []
    with _open_events_csv(csv_path) as handle:
        reader = csv.reader(handle)
        try:
            next(reader)
        except StopIteration:
            return []
        rows = csv.DictReader(handle)
        for row in rows:
            event = row_to_evento(row)
            if event is not None:
                events.append(event)
    logger.info("Loaded %s events from %s", len(events), csv_path)
    return events


def merged_keywords(event: dict[str, Any]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    keywords = event.get("keywords") or {}
    for language in ("en", "es", "hu"):
        for term in keywords.get(language) or []:
            key = term.casefold()
            if key in seen:
                continue
            seen.add(key)
            merged.append(term)
    return merged

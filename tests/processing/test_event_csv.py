from __future__ import annotations

from datetime import date
from pathlib import Path

from src.gdelt.common.utils import hash_identifier
from src.gdelt.processing.event_csv import (
    load_events_from_csv,
    location_terms_for_country,
    merged_keywords,
    parse_event_period,
    split_hooks,
)

CSV_PATH = Path("data/events/DRAGONS_T1.csv")


def test_parse_single_month():
    start, end = parse_event_period("2016 (Jun)", 2016)
    assert start == date(2016, 6, 1)
    assert end == date(2016, 7, 1)


def test_parse_month_range():
    start, end = parse_event_period("2018 (Oct–Dec)", 2018)
    assert start == date(2018, 10, 1)
    assert end == date(2019, 1, 1)


def test_parse_year_range():
    start, end = parse_event_period("2021–2026", 2021)
    assert start == date(2021, 1, 1)
    assert end == date(2027, 1, 1)


def test_parse_calendar_year():
    start, end = parse_event_period("2017", 2017)
    assert start == date(2017, 1, 1)
    assert end == date(2018, 1, 1)


def test_split_hooks_and_hash():
    hooks = split_hooks("Brexit environment; Habitats Directive; CAP subsidies")
    assert hooks[0] == "Brexit environment"
    assert hash_identifier("UK-01") == hash_identifier("UK-01")
    assert len(hash_identifier("UK-01")) == 64


def test_load_events_csv_has_expected_shape():
    events = load_events_from_csv(CSV_PATH)
    assert len(events) == 68
    first = next(event for event in events if event["id"] == "UK-01")
    assert first["pais"] == "United Kingdom"
    assert first["evento"]["en"]
    assert first["keywords"]["en"]
    assert first["periodo"]["start"] == "2016-06-01"
    assert first["periodo"]["end"] == "2016-07-01"
    colombia = next(event for event in events if event["id"] == "CO-01")
    assert colombia["evento"]["es"]
    assert "colombia" in location_terms_for_country(colombia["pais"])
    keywords = merged_keywords(first)
    assert keywords
    assert len(keywords) == len(set(item.casefold() for item in keywords))

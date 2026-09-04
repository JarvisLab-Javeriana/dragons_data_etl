"""Tests for client.py (no network)."""

from __future__ import annotations

import json
import sys
from argparse import Namespace
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import client  # noqa: E402


def _args(**overrides) -> Namespace:
    base = dict(
        keywords="biodiversity, conservation",
        tags="environment",
        languages="en,es",
        media="bbc,reuters",
        start_date="2026-01-01",
        end_date="2026-01-31",
        limit=10,
        output="results.json",
    )
    base.update(overrides)
    return Namespace(**base)


def test_parse_csv_list_trims_and_drops_empties():
    assert client.parse_csv_list("a, b,,c ") == ["a", "b", "c"]
    assert client.parse_csv_list("") == []
    assert client.parse_csv_list(None) == []


def test_validate_params_accepts_valid_input():
    params = client.validate_params(_args())
    assert params.keywords == ["biodiversity", "conservation"]
    assert params.tags == ["environment"]
    assert params.languages == ["en", "es"]
    assert params.media == ["bbc", "reuters"]
    assert params.start_date == date(2026, 1, 1)
    assert params.end_date == date(2026, 1, 31)
    assert params.limit == 10


def test_validate_params_rejects_bad_date_format():
    with pytest.raises(client.ParameterError, match="--start-date"):
        client.validate_params(_args(start_date="01-01-2026"))


def test_validate_params_rejects_start_after_end():
    with pytest.raises(client.ParameterError, match="no puede ser posterior"):
        client.validate_params(_args(start_date="2026-02-01", end_date="2026-01-01"))


def test_validate_params_rejects_unknown_language():
    with pytest.raises(client.ParameterError, match="fr"):
        client.validate_params(_args(languages="en,fr"))


def test_validate_params_rejects_empty_keywords():
    with pytest.raises(client.ParameterError, match="palabra clave"):
        client.validate_params(_args(keywords=" , "))


def test_apply_limit_truncates():
    records = [{"id": i} for i in range(20)]
    assert len(client.apply_limit(records, 5)) == 5
    assert client.apply_limit(records, 5)[-1] == {"id": 4}


def test_help_describes_filters():
    with pytest.raises(SystemExit) as exc:
        client.parse_args(["--help"])
    assert exc.value.code == 0


def test_run_writes_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        client,
        "fetch_records",
        lambda query: [
            {"url": "https://example.com/a", "title": "Hello", "language": "English"}
        ],
    )
    output = tmp_path / "out.json"
    summary = client.run(_args(output=str(output)))
    assert output.exists()
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert payload["query"]["keywords"] == ["biodiversity", "conservation"]
    assert payload["query"]["limit"] == 10
    assert payload["record_count"] == 1
    assert summary["records_processed"] == 1
    assert summary["sample_urls"] == ["https://example.com/a"]
    assert summary["elapsed_seconds"] >= 0


def test_build_gdelt_query_text_includes_languages_and_media():
    text = client.build_gdelt_query_text(
        {
            "keywords": ["biodiversity", "conservation"],
            "tags": ["environment"],
            "languages": ["en", "es", "hu"],
            "media": ["bbc", "reuters"],
        }
    )
    assert "biodiversity OR conservation" in text
    assert "sourcelang:english" in text
    assert "sourcelang:spanish" in text
    assert "sourcelang:hungarian" in text
    assert "domain:bbc.com" in text
    assert "domain:reuters.com" in text
    assert "environment" in text


def test_filter_by_language_keeps_selected_codes():
    articles = [
        {"url": "1", "language": "English"},
        {"url": "2", "language": "French"},
        {"url": "3", "language": "Spanish"},
        {"url": "4", "language": "Hungarian"},
    ]
    kept = client.filter_by_language(articles, ["en", "hu"])
    assert [row["url"] for row in kept] == ["1", "4"]


def test_parse_args_default_limit_and_languages():
    args = client.parse_args(
        [
            "--keywords",
            "biodiversity",
            "--start-date",
            "2026-01-01",
            "--end-date",
            "2026-01-31",
        ]
    )
    assert args.limit == 100
    assert args.languages == "en,es,hu"

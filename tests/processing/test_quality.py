from __future__ import annotations

from datetime import datetime, timezone

from src.quality.checks import run_quality_checks
from src.quality.validators import validate_document


def _valid_document(**overrides):
    base = {
        "source": "gdelt",
        "source_type": "gkg",
        "gkg_record_id": "id-1",
        "date": datetime.now(timezone.utc),
        "document_identifier": "https://example.com/a",
        "themes": ["ENV_BIODIVERSITY"],
        "persons": [],
        "organizations": [],
        "locations": [],
        "tone": None,
        "raw": {},
        "run_id": "run_1",
        "collected_at": datetime.now(timezone.utc),
    }
    base.update(overrides)
    return base


def test_validate_document_accepts_well_formed_document():
    problems = validate_document(_valid_document())
    assert problems == []


def test_validate_document_flags_missing_url():
    problems = validate_document(_valid_document(document_identifier=None))
    assert any("document_identifier" in p for p in problems)


def test_run_quality_checks_splits_valid_and_invalid():
    documents = [
        _valid_document(gkg_record_id="ok-1"),
        _valid_document(gkg_record_id=None),  # invalid: missing id
    ]
    result = run_quality_checks(documents)

    assert result.valid_count == 1
    assert result.invalid_count == 1

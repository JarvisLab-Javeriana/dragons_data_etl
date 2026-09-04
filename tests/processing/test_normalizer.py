from __future__ import annotations

from datetime import datetime, timezone

from src.gdelt.processing.normalizer import normalize_gkg_row


def test_normalize_gkg_row_basic_fields():
    row = {
        "GKGRECORDID": "20200101000000-1",
        "DATE": "20200101120000",
        "DocumentIdentifier": "https://example.com/article",
        "SourceCollectionIdentifier": 1,
        "V2Themes": "ENV_BIODIVERSITY;TAX_FNCACT_SCIENTIST",
        "V2Persons": "Jane Doe,100",
        "V2Organizations": "United Nations,50",
        "V2Locations": "1#United States#US#...",
        "V2Tone": "-2.5,1.2,3.7,4.9,0.0,0.0,120",
    }
    collected_at = datetime(2026, 8, 24, tzinfo=timezone.utc)

    document = normalize_gkg_row(row, run_id="run_test_1", collected_at=collected_at)

    assert document["source"] == "gdelt"
    assert document["source_type"] == "gkg"
    assert document["gkg_record_id"] == "20200101000000-1"
    assert document["document_identifier"] == "https://example.com/article"
    assert document["date"] == datetime(2020, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    assert "ENV_BIODIVERSITY" in document["themes"]
    assert document["tone"]["tone"] == -2.5
    assert document["run_id"] == "run_test_1"
    assert document["raw"]["GKGRECORDID"] == "20200101000000-1"
    assert "V2Themes" not in document["raw"]


def test_normalize_gkg_row_handles_missing_optional_fields():
    row = {"GKGRECORDID": "id-1", "DATE": None}
    document = normalize_gkg_row(row, run_id="run_x", collected_at=datetime.now(timezone.utc))

    assert document["date"] is None
    assert document["themes"] == []
    assert document["tone"] is None

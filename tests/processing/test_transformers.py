from __future__ import annotations

from datetime import date, datetime

from src.gdelt.processing.transformers import (
    deduplicate_batch,
    make_bson_safe,
    prepare_batch_for_storage,
)


def test_make_bson_safe_converts_date_to_datetime():
    document = {"date": date(2020, 1, 1), "nested": {"another_date": date(2020, 1, 2)}}
    safe = make_bson_safe(document)

    assert isinstance(safe["date"], datetime)
    assert isinstance(safe["nested"]["another_date"], datetime)


def test_deduplicate_batch_removes_duplicates_by_key():
    documents = [
        {"gkg_record_id": "a"},
        {"gkg_record_id": "b"},
        {"gkg_record_id": "a"},
    ]
    result = deduplicate_batch(documents)

    assert result.duplicate_count == 1
    assert len(result.unique_documents) == 2


def test_prepare_batch_for_storage_combines_coercion_and_dedupe():
    documents = [
        {"gkg_record_id": "a", "date": date(2020, 1, 1)},
        {"gkg_record_id": "a", "date": date(2020, 1, 1)},
    ]
    result = prepare_batch_for_storage(documents)

    assert len(result.unique_documents) == 1
    assert isinstance(result.unique_documents[0]["date"], datetime)

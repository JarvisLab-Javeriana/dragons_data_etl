"""Unit tests for Mongo sample export helpers (no live MongoDB)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from bson import ObjectId

from src.gdelt.database.export_sample import flatten_document, write_csv, write_xlsx


def test_flatten_document_nested_and_objectid():
    oid = ObjectId()
    flat = flatten_document(
        {
            "_id": oid,
            "source": {"name": "bbc", "country": "UK"},
            "tags": ["a", "b"],
            "date": datetime(2024, 1, 2, 3, 4, 5),
        }
    )
    assert flat["_id"] == str(oid)
    assert flat["source.name"] == "bbc"
    assert flat["source.country"] == "UK"
    assert "a" in flat["tags"]
    assert flat["date"].startswith("2024-01-02")


def test_write_csv_and_xlsx(tmp_path: Path):
    rows = [{"_id": "1", "title": "hello"}, {"_id": "2", "title": "world", "extra": "x"}]
    csv_path = tmp_path / "gkg_records.csv"
    write_csv(csv_path, rows)
    text = csv_path.read_text(encoding="utf-8-sig")
    assert "title" in text
    assert "hello" in text

    xlsx_path = tmp_path / "mongo_sample.xlsx"
    write_xlsx(xlsx_path, {"gkg_records": rows, "crawled_data": []})
    assert xlsx_path.stat().st_size > 0
    assert xlsx_path.read_bytes()[:2] == b"PK"


from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _split_field(value: str | None, sep: str = ";") -> list[str]:
    """Split a semi-colon-delimited GKG field into a clean list of strings."""
    if not value:
        return []
    return [part.strip() for part in value.split(sep) if part.strip()]


def _parse_gkg_date(raw_date: Any) -> datetime | None:
    """GKG's DATE field is typically YYYYMMDDHHMMSS (15-digit long) or a
    BigQuery-native TIMESTAMP/DATE depending on the table. Handle both.
    """
    if raw_date is None:
        return None
    if isinstance(raw_date, datetime):
        return raw_date if raw_date.tzinfo else raw_date.replace(tzinfo=timezone.utc)
    text = str(raw_date)
    for fmt in ("%Y%m%d%H%M%S", "%Y%m%d"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _parse_tone(v2_tone: str | None) -> dict[str, float] | None:
    """V2Tone is a comma-separated list of floats:
    tone, positive_score, negative_score, polarity, activity_ref_density,
    self_group_ref_density, word_count.
    """
    if not v2_tone:
        return None
    parts = [p.strip() for p in v2_tone.split(",")]
    keys = [
        "tone",
        "positive_score",
        "negative_score",
        "polarity",
        "activity_reference_density",
        "self_group_reference_density",
        "word_count",
    ]
    parsed: dict[str, float] = {}
    for key, part in zip(keys, parts):
        try:
            parsed[key] = float(part)
        except ValueError:
            continue
    return parsed or None


def normalize_gkg_row(row: dict[str, Any], run_id: str, collected_at: datetime) -> dict[str, Any]:
    """Convert one raw GKG row (dict from BigQuery) into a MongoDB document.

    The document schema matches section 9 of the project spec. Fields we
    could not confidently parse remain available under `raw` for later,
    more thorough re-processing.
    """
    gkg_record_id = row.get("GKGRECORDID")
    document_identifier = row.get("DocumentIdentifier")

    themes = _split_field(row.get("V2Themes"))
    persons = _split_field(row.get("V2Persons"))
    organizations = _split_field(row.get("V2Organizations"))
    locations = _split_field(row.get("V2Locations"))
    tone = _parse_tone(row.get("V2Tone"))

    # Keep a compact original payload: the large GKG text fields are already
    # stored in parsed form above. Duplicating them in `raw` overflows the
    # Atlas M0 512 MB quota on a 100k-row ingest.
    parsed_raw_keys = {
        "V2Themes",
        "V2Persons",
        "V2Organizations",
        "V2Locations",
        "V2Tone",
    }
    raw = {key: value for key, value in row.items() if key not in parsed_raw_keys}

    document = {
        "source": "gdelt",
        "source_type": "gkg",
        "gkg_record_id": gkg_record_id,
        "date": _parse_gkg_date(row.get("DATE")),
        "document_identifier": document_identifier,
        "source_common_name": row.get("SourceCommonName") or row.get("SourceCollectionIdentifier"),
        "themes": themes,
        "persons": persons,
        "organizations": organizations,
        "locations": locations,
        "tone": tone,
        "raw": raw,
        "ingestion": {
            "run_id": run_id,
            "collected_at": collected_at,
        },
        "run_id": run_id,
        "collected_at": collected_at,
    }
    return document

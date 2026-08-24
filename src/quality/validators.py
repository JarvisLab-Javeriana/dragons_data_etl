
from __future__ import annotations

from typing import Any
from urllib.parse import urlparse


def validate_url(document: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    url = document.get("document_identifier")
    if not url:
        problems.append("missing document_identifier (URL)")
        return problems
    parsed = urlparse(str(url))
    if not parsed.scheme or not parsed.netloc:
        problems.append(f"document_identifier is not a well-formed URL: {url!r}")
    return problems


def validate_gkg_record_id(document: dict[str, Any]) -> list[str]:
    if not document.get("gkg_record_id"):
        return ["missing gkg_record_id"]
    return []


def validate_date(document: dict[str, Any]) -> list[str]:
    if document.get("date") is None:
        return ["missing or unparsable date"]
    return []


def validate_source(document: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    if document.get("source") != "gdelt":
        problems.append(f"unexpected source: {document.get('source')!r}")
    if document.get("source_type") != "gkg":
        problems.append(f"unexpected source_type: {document.get('source_type')!r}")
    return problems


def validate_not_empty(document: dict[str, Any]) -> list[str]:
    """A GKG record with no themes, persons, organizations AND no locations
    is likely low-value noise (or a parsing failure upstream)."""
    if not (
        document.get("themes")
        or document.get("persons")
        or document.get("organizations")
        or document.get("locations")
    ):
        return ["document has no themes/persons/organizations/locations"]
    return []


def validate_expected_structure(document: dict[str, Any]) -> list[str]:
    required_keys = {
        "source",
        "source_type",
        "gkg_record_id",
        "date",
        "document_identifier",
        "themes",
        "persons",
        "organizations",
        "locations",
        "tone",
        "raw",
        "run_id",
        "collected_at",
    }
    missing = required_keys - document.keys()
    if missing:
        return [f"missing expected keys: {sorted(missing)}"]
    return []


DEFAULT_VALIDATORS = (
    validate_expected_structure,
    validate_gkg_record_id,
    validate_date,
    validate_source,
    validate_url,
    validate_not_empty,
)


def validate_document(
    document: dict[str, Any], validators=DEFAULT_VALIDATORS
) -> list[str]:
    """Run all validators against a document and return the combined list of
    problems (empty == valid)."""
    problems: list[str] = []
    for validator in validators:
        problems.extend(validator(document))
    return problems

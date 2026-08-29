
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.gdelt.quality.validators import DEFAULT_VALIDATORS, validate_document


@dataclass
class QualityCheckResult:
    valid_documents: list[dict[str, Any]] = field(default_factory=list)
    invalid_documents: list[dict[str, Any]] = field(default_factory=list)
    problems_by_gkg_record_id: dict[str, list[str]] = field(default_factory=dict)

    @property
    def valid_count(self) -> int:
        return len(self.valid_documents)

    @property
    def invalid_count(self) -> int:
        return len(self.invalid_documents)

    def to_metrics_dict(self) -> dict[str, Any]:
        return {
            "documents_checked": self.valid_count + self.invalid_count,
            "documents_valid": self.valid_count,
            "documents_invalid": self.invalid_count,
        }


def run_quality_checks(
    documents: list[dict[str, Any]], validators=DEFAULT_VALIDATORS
) -> QualityCheckResult:
    result = QualityCheckResult()

    for document in documents:
        problems = validate_document(document, validators=validators)
        if problems:
            result.invalid_documents.append(document)
            record_id = str(document.get("gkg_record_id") or id(document))
            result.problems_by_gkg_record_id[record_id] = problems
        else:
            result.valid_documents.append(document)

    return result

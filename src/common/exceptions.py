from __future__ import annotations


class DragonsDataETLError(Exception):
    """Base class for all project-specific exceptions."""

    stage: str = "unknown"

    def __init__(self, message: str, *, stage: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if stage is not None:
            self.stage = stage


class ConfigurationError(DragonsDataETLError):
    stage = "config"


class BigQueryError(DragonsDataETLError):
    stage = "bigquery"


class DownloadError(DragonsDataETLError):
    stage = "download"


class ProcessingError(DragonsDataETLError):
    stage = "processing"


class ValidationError(ProcessingError):
    stage = "processing"


class MongoDBError(DragonsDataETLError):
    stage = "mongodb"


class MonitoringError(DragonsDataETLError):
    stage = "monitoring"


class ResourceLimitError(DragonsDataETLError):
    """Raised when a configured safety limit (disk, bytes billed, ...) is hit."""

    stage = "monitoring"

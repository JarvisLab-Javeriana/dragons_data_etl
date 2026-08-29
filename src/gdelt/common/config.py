from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

from src.gdelt.common.exceptions import ConfigurationError

# Load .env once, as early as possible, without overriding variables the
# shell/CI environment may have already exported.
load_dotenv(override=False)

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _resolve_env_placeholders(value: Any) -> Any:
    """Recursively resolve ``${VAR_NAME}`` placeholders in strings.

    Missing environment variables resolve to an empty string rather than
    raising, so that config files stay loadable (e.g. for `test` mode where
    MongoDB is not actually touched). Callers that require a value should
    validate it explicitly.
    """
    if isinstance(value, str):
        def _replace(match: re.Match) -> str:
            return os.environ.get(match.group(1), "")

        return _ENV_VAR_PATTERN.sub(_replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_placeholders(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_placeholders(v) for v in value]
    return value


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load a YAML file relative to the project root (or as an absolute path)."""
    full_path = Path(path)
    if not full_path.is_absolute():
        full_path = PROJECT_ROOT / full_path

    if not full_path.exists():
        raise ConfigurationError(f"Configuration file not found: {full_path}")

    with full_path.open("r", encoding="utf-8") as fh:
        raw = yaml.safe_load(fh) or {}

    return _resolve_env_placeholders(raw)


@dataclass(frozen=True)
class DatasetConfig:
    project: str
    dataset: str
    table: str


@dataclass(frozen=True)
class DateRangeConfig:
    start: date
    end: date

    def __post_init__(self) -> None:
        if self.start >= self.end:
            raise ConfigurationError(
                f"date_range.start ({self.start}) must be before date_range.end ({self.end})"
            )


@dataclass(frozen=True)
class GdeltSourceConfig:
    """Typed view over config/sources/gdelt.yaml."""

    dataset: DatasetConfig
    keywords: list[str]
    date_range: DateRangeConfig
    max_rows: int
    batch_size: int
    mode: str  # "test" | "ingestion"
    save_to_mongodb: bool
    save_metrics: bool
    max_bytes_billed: int | None = None

    @property
    def is_ingestion(self) -> bool:
        return self.mode == "ingestion" and self.save_to_mongodb

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "GdeltSourceConfig":
        try:
            dataset = DatasetConfig(**raw["dataset"])
            date_range_raw = raw["date_range"]
            date_range = DateRangeConfig(
                start=_parse_date(date_range_raw["start"]),
                end=_parse_date(date_range_raw["end"]),
            )
            mode = raw.get("mode", "test")
            if mode not in ("test", "ingestion"):
                raise ConfigurationError(
                    f"Invalid mode '{mode}': expected 'test' or 'ingestion'"
                )
            return cls(
                dataset=dataset,
                keywords=list(raw.get("keywords", [])),
                date_range=date_range,
                max_rows=int(raw.get("max_rows", 1000)),
                batch_size=int(raw.get("batch_size", 500)),
                mode=mode,
                save_to_mongodb=bool(raw.get("save_to_mongodb", False)),
                save_metrics=bool(raw.get("save_metrics", True)),
                max_bytes_billed=raw.get("max_bytes_billed"),
            )
        except KeyError as exc:
            raise ConfigurationError(f"Missing required GDELT config key: {exc}") from exc


def _parse_date(value: Any) -> date:
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def load_gdelt_config(path: str | Path = "config/sources/gdelt.yaml") -> GdeltSourceConfig:
    return GdeltSourceConfig.from_dict(load_yaml(path))


@dataclass(frozen=True)
class MongoDBConfig:
    uri: str
    database: str
    gkg_records_collection: str
    execution_metrics_collection: str
    connect_timeout_ms: int
    server_selection_timeout_ms: int
    ordered_inserts: bool
    ensure_indexes_on_startup: bool

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "MongoDBConfig":
        uri = raw.get("uri", "")
        database = raw.get("database", "")
        if not uri:
            raise ConfigurationError(
                "MongoDB URI is empty. Set MONGODB_URI in your .env file."
            )
        if not database:
            raise ConfigurationError(
                "MongoDB database name is empty. Set MONGODB_DATABASE in your .env file."
            )
        collections = raw.get("collections", {})
        return cls(
            uri=uri,
            database=database,
            gkg_records_collection=collections.get("gkg_records", "gkg_records"),
            execution_metrics_collection=collections.get(
                "execution_metrics", "execution_metrics"
            ),
            connect_timeout_ms=int(raw.get("connect_timeout_ms", 5000)),
            server_selection_timeout_ms=int(
                raw.get("server_selection_timeout_ms", 5000)
            ),
            ordered_inserts=bool(raw.get("ordered_inserts", False)),
            ensure_indexes_on_startup=bool(raw.get("ensure_indexes_on_startup", True)),
        )


def load_mongodb_config(path: str | Path = "config/settings/mongodb.yaml") -> MongoDBConfig:
    return MongoDBConfig.from_dict(load_yaml(path))


@dataclass(frozen=True)
class PipelineConfig:
    run_id_prefix: str
    experiments_output_dir: str
    system_monitor_interval_seconds: float
    min_free_disk_bytes: int | None

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "PipelineConfig":
        return cls(
            run_id_prefix=raw.get("run_id_prefix", "run"),
            experiments_output_dir=raw.get(
                "experiments_output_dir", "docs/experiments"
            ),
            system_monitor_interval_seconds=float(
                raw.get("system_monitor_interval_seconds", 1.0)
            ),
            min_free_disk_bytes=raw.get("min_free_disk_bytes"),
        )


def load_pipeline_config(path: str | Path = "config/settings/pipeline.yaml") -> PipelineConfig:
    return PipelineConfig.from_dict(load_yaml(path))


@dataclass(frozen=True)
class LoggingConfig:
    level: str
    format: str
    date_format: str
    log_to_file: bool
    log_dir: str
    log_file: str
    max_bytes: int
    backup_count: int

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "LoggingConfig":
        return cls(
            level=raw.get("level", "INFO"),
            format=raw.get(
                "format", "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
            ),
            date_format=raw.get("date_format", "%Y-%m-%d %H:%M:%S"),
            log_to_file=bool(raw.get("log_to_file", True)),
            log_dir=raw.get("log_dir", "logs"),
            log_file=raw.get("log_file", "dragons_data_etl.log"),
            max_bytes=int(raw.get("max_bytes", 5 * 1024 * 1024)),
            backup_count=int(raw.get("backup_count", 3)),
        )


def load_logging_config(path: str | Path = "config/settings/logging.yaml") -> LoggingConfig:
    return LoggingConfig.from_dict(load_yaml(path))

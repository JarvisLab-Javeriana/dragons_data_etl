
from __future__ import annotations

import uuid
from collections.abc import Iterable, Iterator
from datetime import datetime, timezone
from typing import TypeVar

T = TypeVar("T")


def new_run_id(prefix: str = "run") -> str:
    """Generate a sortable, unique run identifier.

    Format: ``{prefix}_{UTC timestamp}_{short uuid}``, e.g.
    ``run_20260824T131500Z_a1b2c3d4``.
    """
    timestamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    short_uuid = uuid.uuid4().hex[:8]
    return f"{prefix}_{timestamp}_{short_uuid}"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def chunked(iterable: Iterable[T], size: int) -> Iterator[list[T]]:
    """Yield successive chunks of at most ``size`` items from ``iterable``.

    Works on any iterable (including generators) without loading everything
    into memory at once -- important for batching BigQuery results before
    they are written to MongoDB (see section 16 of the project spec).
    """
    if size <= 0:
        raise ValueError("chunk size must be positive")

    batch: list[T] = []
    for item in iterable:
        batch.append(item)
        if len(batch) >= size:
            yield batch
            batch = []
    if batch:
        yield batch


def bytes_to_human(num_bytes: float) -> str:
    """Format a byte count as a human-readable string, e.g. '12.34 MB'."""
    value = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(value) < 1024.0:
            return f"{value:.2f} {unit}"
        value /= 1024.0
    return f"{value:.2f} PB"

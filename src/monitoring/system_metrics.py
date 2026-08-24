
from __future__ import annotations

import logging
import os
import threading
import time
from dataclasses import dataclass

import psutil

from src.monitoring.metrics import SystemMetrics

logger = logging.getLogger(__name__)


def _process_rss_bytes() -> int:
    return psutil.Process(os.getpid()).memory_info().rss


def _disk_free_bytes(path: str = "/") -> int:
    return psutil.disk_usage(path).free


@dataclass
class _Snapshot:
    ram_bytes: int
    disk_free_bytes: int
    cpu_percent: float


class SystemMonitor:
    """Background sampler for RAM/disk/CPU.

    Usage:
        monitor = SystemMonitor(interval_seconds=1.0)
        monitor.start()
        ... do work ...
        metrics = monitor.stop()
    """

    def __init__(self, interval_seconds: float = 1.0, disk_path: str = "/") -> None:
        self._interval = interval_seconds
        self._disk_path = disk_path
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._samples: list[_Snapshot] = []
        self._ram_before: int | None = None
        self._disk_before: int | None = None

    def start(self) -> None:
        self._ram_before = _process_rss_bytes()
        self._disk_before = _disk_free_bytes(self._disk_path)
        psutil.cpu_percent(interval=None)  # prime the internal CPU counter

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        logger.debug("SystemMonitor started (interval=%.2fs)", self._interval)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            try:
                self._samples.append(
                    _Snapshot(
                        ram_bytes=_process_rss_bytes(),
                        disk_free_bytes=_disk_free_bytes(self._disk_path),
                        cpu_percent=psutil.cpu_percent(interval=None),
                    )
                )
            except Exception:  # pragma: no cover - monitoring must never crash the pipeline
                logger.exception("SystemMonitor sampling error")
            self._stop_event.wait(self._interval)

    def stop(self) -> SystemMetrics:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval + 1)

        ram_after = _process_rss_bytes()
        disk_after = _disk_free_bytes(self._disk_path)

        ram_values = [s.ram_bytes for s in self._samples] + [
            v for v in (self._ram_before, ram_after) if v is not None
        ]
        disk_values = [s.disk_free_bytes for s in self._samples] + [
            v for v in (self._disk_before, disk_after) if v is not None
        ]
        cpu_values = [s.cpu_percent for s in self._samples]

        metrics = SystemMetrics(
            ram_before_bytes=self._ram_before,
            ram_after_bytes=ram_after,
            ram_peak_bytes=max(ram_values) if ram_values else None,
            disk_free_before_bytes=self._disk_before,
            disk_free_after_bytes=disk_after,
            disk_free_minimum_bytes=min(disk_values) if disk_values else None,
            cpu_percent_avg=(sum(cpu_values) / len(cpu_values)) if cpu_values else None,
            cpu_count=psutil.cpu_count(logical=True),
        )
        logger.debug("SystemMonitor stopped: %s", metrics.to_dict())
        return metrics

    def check_disk_guard(self, min_free_bytes: int | None) -> bool:
        """Returns True if disk space is still above the configured guard
        (or no guard configured)."""
        if min_free_bytes is None:
            return True
        return _disk_free_bytes(self._disk_path) >= min_free_bytes

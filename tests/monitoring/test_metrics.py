from __future__ import annotations

from src.monitoring.metrics import ErrorInfo, ExecutionMetrics
from src.monitoring.system_metrics import SystemMonitor


def test_execution_metrics_mark_success_sets_status_and_timestamp():
    metrics = ExecutionMetrics(run_id="run_1")
    metrics.mark_success()

    assert metrics.status == "success"
    assert metrics.finished_at is not None


def test_execution_metrics_mark_failed_records_error():
    metrics = ExecutionMetrics(run_id="run_1")
    metrics.mark_failed(ErrorInfo(type="BigQueryError", message="boom", stage="bigquery"))

    assert metrics.status == "failed"
    assert metrics.error.stage == "bigquery"
    as_dict = metrics.to_dict()
    assert as_dict["error"]["type"] == "BigQueryError"


def test_system_monitor_start_stop_produces_metrics():
    monitor = SystemMonitor(interval_seconds=0.05)
    monitor.start()
    metrics = monitor.stop()

    assert metrics.ram_before_bytes is not None
    assert metrics.ram_after_bytes is not None
    assert metrics.ram_peak_bytes is not None
    assert metrics.cpu_count is not None

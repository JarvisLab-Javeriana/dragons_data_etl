#!/usr/bin/env python3
"""
Characterizes GDELT/BigQuery behaviour across historical periods WITHOUT
writing anything to MongoDB (project spec section 21).

For each year (or custom period) in the requested range, runs a cheap
keyword-count query (see queries/gdelt/analysis/keyword_count.sql) and
records: period, rows, bytes_processed, bytes_billed, duration.

Results are printed as a table and written to
`docs/experiments/history_<timestamp>.csv` for later comparison.

Usage:
    python GDELT/scripts/test_gdelt_history.py
    python GDELT/scripts/test_gdelt_history.py --start-year 2015 --end-year 2026
    python GDELT/scripts/test_gdelt_history.py --start-year 2020 --end-year 2021 --keywords biodiversity climate
"""

from __future__ import annotations

import argparse
import csv
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.collectors.gdelt.collector import GdeltCollector  # noqa: E402
from src.gedelt.collectors.common.config import PROJECT_ROOT, load_gdelt_config, load_pipeline_config  # noqa: E402
from src.gedelt.collectors.common.exceptions import DragonsDataETLError  # noqa: E402
from src.gedelt.collectors.common.logging import configure_logging  # noqa: E402
from src.gedelt.collectors.common.utils import utcnow  # noqa: E402

import logging  # noqa: E402

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Characterize GDELT/BigQuery across historical yearly periods."
    )
    parser.add_argument("--config", default="config/sources/gdelt.yaml")
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=date.today().year)
    parser.add_argument(
        "--keywords",
        nargs="*",
        default=None,
        help="Override keywords from config for this experiment.",
    )
    return parser.parse_args()


def year_periods(start_year: int, end_year: int) -> list[tuple[date, date]]:
    periods = []
    for year in range(start_year, end_year + 1):
        start = date(year, 1, 1)
        end = date(year + 1, 1, 1)
        periods.append((start, end))
    return periods


def main() -> int:
    configure_logging()
    args = parse_args()

    gdelt_config = load_gdelt_config(args.config)
    pipeline_config = load_pipeline_config()
    keywords = args.keywords or gdelt_config.keywords

    collector = GdeltCollector(gdelt_config)

    print(f"Characterizing GDELT history for keywords={keywords}, "
          f"years {args.start_year}-{args.end_year}\n")
    print(f"{'period':<12}{'rows':>12}{'bytes_processed':>18}{'bytes_billed':>16}{'duration_s':>12}")
    print("-" * 70)

    results: list[dict] = []

    for start, end in year_periods(args.start_year, args.end_year):
        period_label = str(start.year)
        try:
            count, metrics = collector.count_for_range(start, end, keywords)
            row = {
                "period": period_label,
                "start_date": str(start),
                "end_date": str(end),
                "rows": count,
                "bytes_processed": metrics.bytes_processed,
                "bytes_billed": metrics.bytes_billed,
                "duration_seconds": round(metrics.duration_seconds or 0.0, 3),
                "error": "",
            }
            print(
                f"{period_label:<12}{count:>12}{metrics.bytes_processed or 0:>18}"
                f"{metrics.bytes_billed or 0:>16}{row['duration_seconds']:>12}"
            )
        except DragonsDataETLError as exc:
            row = {
                "period": period_label,
                "start_date": str(start),
                "end_date": str(end),
                "rows": None,
                "bytes_processed": None,
                "bytes_billed": None,
                "duration_seconds": None,
                "error": str(exc),
            }
            print(f"{period_label:<12}{'ERROR':>12}  {exc}")

        results.append(row)

    collector.close()

    output_dir = PROJECT_ROOT / pipeline_config.experiments_output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = utcnow().strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"history_{timestamp}.csv"

    with output_path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(results[0].keys()) if results else [])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nResults written to {output_path.relative_to(PROJECT_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

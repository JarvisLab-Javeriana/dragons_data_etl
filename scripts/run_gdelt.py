#!/usr/bin/env python3
"""Run the event-driven GDELT pipeline (sample: 100 rows per event).

Usage:
    python scripts/run_gdelt.py --seed-only
    python scripts/run_gdelt.py --max-events 1 --skip-scrape
    python scripts/run_gdelt.py --event-id UK-01 --event-id CO-01
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.common.config import load_gdelt_config  # noqa: E402
from src.gdelt.common.exceptions import DragonsDataETLError  # noqa: E402
from src.gdelt.common.logging import configure_logging  # noqa: E402
from src.gdelt.pipelines.gdelt_pipeline import GdeltPipeline  # noqa: E402
from src.gdelt.processing.event_csv import DEFAULT_EVENTS_CSV, SAMPLE_ROW_LIMIT  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the event-driven GDELT ETL pipeline.")
    parser.add_argument(
        "--config",
        default="config/sources/gdelt.yaml",
        help="Path to the GDELT source configuration YAML file.",
    )
    parser.add_argument(
        "--csv",
        default=str(DEFAULT_EVENTS_CSV),
        help="Events CSV used to seed the eventos collection.",
    )
    parser.add_argument(
        "--event-id",
        action="append",
        dest="event_ids",
        default=None,
        help="Run only these event IDs (repeatable).",
    )
    parser.add_argument(
        "--max-events",
        type=int,
        default=None,
        help="Cap how many events to query (Atlas sample). Omit to run all seeded events.",
    )
    parser.add_argument(
        "--row-limit",
        type=int,
        default=SAMPLE_ROW_LIMIT,
        help="Max GDELT rows per query (default: 100).",
    )
    parser.add_argument(
        "--skip-scrape",
        action="store_true",
        help="Persist whitelist and metrics without scraping article HTML.",
    )
    parser.add_argument(
        "--seed-only",
        action="store_true",
        help="Upsert eventos from the CSV and exit (no BigQuery).",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    gdelt_config = load_gdelt_config(args.config)
    pipeline = GdeltPipeline(gdelt_config=gdelt_config)
    try:
        result = pipeline.run(
            csv_path=args.csv,
            event_ids=args.event_ids,
            max_events=args.max_events,
            row_limit=args.row_limit,
            skip_scrape=args.skip_scrape,
            seed_only=args.seed_only,
        )
    except DragonsDataETLError as exc:
        print(f"\nGDELT run failed at stage='{exc.stage}': {exc}", file=sys.stderr)
        return 1

    print("\n=== GDELT run summary ===")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

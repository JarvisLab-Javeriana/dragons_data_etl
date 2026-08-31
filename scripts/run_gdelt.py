#!/usr/bin/env python3
"""
Entry point for a single GDELT pipeline run.

Usage:
    python scripts/run_gdelt.py
    python scripts/run_gdelt.py --config config/sources/gdelt.yaml

This script deliberately contains NO pipeline logic -- it only parses
arguments, configures logging, and delegates to
`src.pipelines.gdelt_pipeline.GdeltPipeline`.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Allow running as `python scripts/run_gdelt.py` from the repo root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.common.config import load_gdelt_config  # noqa: E402
from src.gdelt.common.exceptions import DragonsDataETLError  # noqa: E402
from src.gdelt.common.logging import configure_logging  # noqa: E402
from src.gdelt.pipelines.gdelt_pipeline import GdeltPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the GDELT ETL pipeline.")
    parser.add_argument(
        "--config",
        default="config/sources/gdelt.yaml",
        help="Path to the GDELT source configuration YAML file.",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()

    gdelt_config = load_gdelt_config(args.config)
    pipeline = GdeltPipeline(gdelt_config=gdelt_config)

    try:
        result = pipeline.run()
    except DragonsDataETLError as exc:
        print(f"\nGDELT run failed at stage='{exc.stage}': {exc}", file=sys.stderr)
        return 1

    print("\n=== GDELT run summary ===")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

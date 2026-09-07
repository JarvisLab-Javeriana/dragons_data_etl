#!/usr/bin/env python3
"""Seed the eventos collection from DRAGONS_T1.csv without querying GDELT."""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.common.config import load_gdelt_config  # noqa: E402
from src.gdelt.common.logging import configure_logging  # noqa: E402
from src.gdelt.pipelines.gdelt_pipeline import GdeltPipeline  # noqa: E402
from src.gdelt.processing.event_csv import DEFAULT_EVENTS_CSV  # noqa: E402


def main() -> int:
    configure_logging()
    pipeline = GdeltPipeline(gdelt_config=load_gdelt_config())
    result = pipeline.run(csv_path=DEFAULT_EVENTS_CSV, seed_only=True)
    print(json.dumps(result, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

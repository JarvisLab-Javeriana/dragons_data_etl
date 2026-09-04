#!/usr/bin/env python3
"""
Crawl a sample of GDELT document_identifier URLs stored in MongoDB,
write HTML locally, and insert extracted text/metadata into crawled_data.

Usage:
    python scripts/run_crawler.py
    python scripts/run_crawler.py --limit 50
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.common.config import load_crawler_config  # noqa: E402
from src.gdelt.common.exceptions import DragonsDataETLError  # noqa: E402
from src.gdelt.common.logging import configure_logging  # noqa: E402
from src.gdelt.pipelines.crawl_pipeline import CrawlPipeline  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Crawl GDELT article URLs from MongoDB to local files."
    )
    parser.add_argument(
        "--config",
        default="config/sources/crawler.yaml",
        help="Path to the crawler YAML configuration.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Override the number of URLs to crawl (default: config limit).",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    crawler_config = load_crawler_config(args.config)
    pipeline = CrawlPipeline(crawler_config=crawler_config)

    try:
        result = pipeline.run(limit=args.limit)
    except DragonsDataETLError as exc:
        print(f"\nCrawl run failed at stage='{exc.stage}': {exc}", file=sys.stderr)
        return 1

    print("\n=== Crawl run summary ===")
    print(json.dumps(result, indent=2, default=str))
    return 0 if result.get("status") == "success" else 1


if __name__ == "__main__":
    raise SystemExit(main())

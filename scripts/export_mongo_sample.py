#!/usr/bin/env python3
"""Export the first N documents of every MongoDB collection to CSV and/or Excel.

Usage (from repo root, PowerShell in one line):

    python scripts/export_mongo_sample.py
    python scripts/export_mongo_sample.py --limit 100 --format both
    python scripts/export_mongo_sample.py --format csv --output-dir data/mongo_exports
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.gdelt.common.config import load_mongodb_config  # noqa: E402
from src.gdelt.common.exceptions import DragonsDataETLError  # noqa: E402
from src.gdelt.common.logging import configure_logging  # noqa: E402
from src.gdelt.database.export_sample import export_collection_samples  # noqa: E402
from src.gdelt.database.mongodb import MongoDBConnection  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Exporta los primeros registros de cada colección MongoDB a CSV y/o Excel. "
            "Por defecto toma 100 documentos por colección."
        )
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Máximo de documentos por colección (por defecto: 100).",
    )
    parser.add_argument(
        "--format",
        choices=("csv", "xlsx", "both"),
        default="both",
        help="Formato de salida: csv, xlsx (Excel) o both (por defecto).",
    )
    parser.add_argument(
        "--output-dir",
        default="data/mongo_exports",
        help="Directorio de salida (por defecto: data/mongo_exports).",
    )
    parser.add_argument(
        "--config",
        default="config/settings/mongodb.yaml",
        help="YAML de conexión MongoDB.",
    )
    return parser.parse_args()


def main() -> int:
    configure_logging()
    args = parse_args()
    if args.limit < 1:
        print("--limit debe ser un entero positivo.", file=sys.stderr)
        return 2

    formats = ("csv", "xlsx") if args.format == "both" else (args.format,)
    mongo_config = load_mongodb_config(args.config)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with MongoDBConnection(mongo_config) as connection:
            summary = export_collection_samples(
                connection.database,
                output_dir=output_dir,
                limit=args.limit,
                formats=formats,
            )
    except DragonsDataETLError as exc:
        print(f"Export failed at stage='{exc.stage}': {exc}", file=sys.stderr)
        return 1

    print("\n=== Mongo export summary ===")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

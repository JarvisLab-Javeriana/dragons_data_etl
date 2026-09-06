from __future__ import annotations

import argparse
import json
import logging
import os
from pathlib import Path
from typing import Any

import certifi
from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, UpdateOne
from pymongo.errors import BulkWriteError, PyMongoError


REQUIRED_FIELDS = {
    "eid",
    "indexed_date",
    "media_name",
    "media_url",
    "publish_date",
    "title",
    "url",
    "language",
    "keywords",
    "contenido",
}


def load_json_file(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        raise FileNotFoundError(f"JSON file not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError("The JSON root must be an array/list.")

    return data


def validate_record(record: dict[str, Any], index: int) -> tuple[bool, str | None]:
    if not isinstance(record, dict):
        return False, f"Record #{index} is not an object."

    missing = REQUIRED_FIELDS - set(record.keys())
    if missing:
        return False, f"Record #{index} missing fields: {', '.join(sorted(missing))}"

    if not record.get("eid"):
        return False, f"Record #{index} has empty eid."

    if not record.get("language"):
        return False, f"Record #{index} has empty language."

    if not record.get("keywords"):
        return False, f"Record #{index} has empty keywords."

    return True, None


def create_client(uri: str) -> MongoClient:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10000,
        connectTimeoutMS=10000,
        socketTimeoutMS=30000,
        retryWrites=True,
    )
    client.admin.command("ping")
    return client


def prepare_collection(client: MongoClient, database_name: str, collection_name: str):
    collection = client[database_name][collection_name]

    collection.create_index(
        [
            ("eid", ASCENDING),
            ("language", ASCENDING),
            ("keywords", ASCENDING),
        ],
        unique=True,
        name="unique_eid_language_keywords",
    )

    collection.create_index([("publish_date", ASCENDING)], name="publish_date_idx")
    collection.create_index([("media_name", ASCENDING)], name="media_name_idx")
    collection.create_index([("language", ASCENDING)], name="language_idx")
    collection.create_index([("keywords", ASCENDING)], name="keywords_idx")

    return collection


def build_upsert(record: dict[str, Any]) -> UpdateOne:
    identity = {
        "eid": record["eid"],
        "language": record["language"],
        "keywords": record["keywords"],
    }

    return UpdateOne(
        identity,
        {"$set": record},
        upsert=True,
    )


def upload_news(
    collection,
    records: list[dict[str, Any]],
    *,
    batch_size: int = 500,
    skip_empty_content: bool = False,
) -> None:
    operations: list[UpdateOne] = []

    valid = 0
    invalid = 0
    skipped_empty = 0
    inserted_total = 0
    updated_total = 0
    matched_total = 0

    logging.info("Loaded %d records from JSON.", len(records))

    for index, record in enumerate(records, start=1):
        ok, error = validate_record(record, index)

        if not ok:
            invalid += 1
            logging.error("Skipping invalid record: %s", error)
            continue

        if skip_empty_content and not record.get("contenido"):
            skipped_empty += 1
            logging.warning(
                "Skipping empty contenido | eid=%s | language=%s | keywords=%s",
                record.get("eid"),
                record.get("language"),
                record.get("keywords"),
            )
            continue

        operations.append(build_upsert(record))
        valid += 1

        if len(operations) >= batch_size:
            result = collection.bulk_write(operations, ordered=False)

            inserted_total += result.upserted_count
            updated_total += result.modified_count
            matched_total += result.matched_count

            logging.info(
                "Batch uploaded | inserted=%d | updated=%d | matched=%d",
                result.upserted_count,
                result.modified_count,
                result.matched_count,
            )

            operations.clear()

    if operations:
        result = collection.bulk_write(operations, ordered=False)

        inserted_total += result.upserted_count
        updated_total += result.modified_count
        matched_total += result.matched_count

        logging.info(
            "Final batch uploaded | inserted=%d | updated=%d | matched=%d",
            result.upserted_count,
            result.modified_count,
            result.matched_count,
        )

    logging.info(
        "Finished | valid=%d | invalid=%d | skipped_empty=%d | inserted=%d | updated=%d | matched=%d",
        valid,
        invalid,
        skipped_empty,
        inserted_total,
        updated_total,
        matched_total,
    )


def main() -> None:
    load_dotenv()

    parser = argparse.ArgumentParser(
        description="Upload scraped news JSON to MongoDB Atlas."
    )

    parser.add_argument("--input", default="news.json")
    parser.add_argument(
        "--database",
        default=os.getenv("MONGODB_DATABASE", "dragons"),
    )
    parser.add_argument(
        "--collection",
        default=os.getenv("MONGODB_COLLECTION", "news"),
    )
    parser.add_argument("--batch-size", type=int, default=500)
    parser.add_argument("--skip-empty-content", action="store_true")

    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
    )

    uri = os.getenv("MONGODB_URI")
    if not uri:
        raise RuntimeError(
            "MONGODB_URI is not configured. Create a .env file with your Atlas URI."
        )

    records = load_json_file(Path(args.input).resolve())

    client = None

    try:
        logging.info("Connecting to MongoDB Atlas...")
        client = create_client(uri)
        logging.info("MongoDB connection successful.")

        collection = prepare_collection(
            client,
            args.database,
            args.collection,
        )

        logging.info("Target: %s.%s", args.database, args.collection)

        upload_news(
            collection,
            records,
            batch_size=args.batch_size,
            skip_empty_content=args.skip_empty_content,
        )

    except BulkWriteError as exc:
        logging.error("MongoDB bulk write error: %s", exc.details)
        raise

    except PyMongoError as exc:
        logging.error("MongoDB error: %s", exc)
        raise

    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

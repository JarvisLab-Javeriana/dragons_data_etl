from __future__ import annotations

import csv
import json
import logging
import re
import zipfile
from datetime import date, datetime
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape

from bson import ObjectId
from pymongo.database import Database

logger = logging.getLogger(__name__)

_INVALID_SHEET_CHARS = re.compile(r"[\\/*?:\[\]]")


def serialize_value(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (list, dict, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def flatten_document(document: dict[str, Any], prefix: str = "") -> dict[str, str]:
    flat: dict[str, str] = {}
    for key, value in document.items():
        column = f"{prefix}.{key}" if prefix else str(key)
        if isinstance(value, dict):
            flat.update(flatten_document(value, column))
        else:
            flat[column] = serialize_value(value)
    return flat


def list_user_collections(database: Database) -> list[str]:
    names = database.list_collection_names()
    return sorted(name for name in names if not name.startswith("system."))


def sample_documents(
    database: Database, collection_name: str, limit: int
) -> list[dict[str, Any]]:
    cursor = database[collection_name].find({}).limit(limit)
    return [dict(doc) for doc in cursor]


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames: list[str] = []
    seen: set[str] = set()
    for row in rows:
        for key in row:
            if key not in seen:
                seen.add(key)
                fieldnames.append(key)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _sheet_name(collection_name: str, used: set[str]) -> str:
    name = _INVALID_SHEET_CHARS.sub("_", collection_name)[:31] or "sheet"
    candidate = name
    index = 1
    while candidate.lower() in used:
        suffix = f"_{index}"
        candidate = f"{name[: 31 - len(suffix)]}{suffix}"
        index += 1
    used.add(candidate.lower())
    return candidate


def _cell_xml(col_index: int, row_index: int, value: str) -> str:
    n = col_index
    col = ""
    while n:
        n, rem = divmod(n - 1, 26)
        col = chr(65 + rem) + col
    ref = f"{col}{row_index}"
    text = escape(value[:32767], {"'": "&apos;", '"': "&quot;"})
    return f'<c r="{ref}" t="inlineStr"><is><t xml:space="preserve">{text}</t></is></c>'


def write_xlsx(path: Path, sheets: dict[str, list[dict[str, str]]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    used_names: set[str] = set()
    sheet_files: list[tuple[str, str, str, str]] = []
    for collection_name, rows in sheets.items():
        sheet = _sheet_name(collection_name, used_names)
        fieldnames: list[str] = []
        seen: set[str] = set()
        for row in rows:
            for key in row:
                if key not in seen:
                    seen.add(key)
                    fieldnames.append(key)
        xml_rows: list[str] = []
        header_cells = "".join(
            _cell_xml(i + 1, 1, name) for i, name in enumerate(fieldnames)
        )
        xml_rows.append(f'<row r="1">{header_cells}</row>')
        for row_i, row in enumerate(rows, start=2):
            cells = "".join(
                _cell_xml(col_i + 1, row_i, row.get(name, ""))
                for col_i, name in enumerate(fieldnames)
            )
            xml_rows.append(f'<row r="{row_i}">{cells}</row>')
        sheet_xml = (
            '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
            '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
            f'<sheetData>{"".join(xml_rows)}</sheetData></worksheet>'
        )
        rel_id = f"rId{len(sheet_files) + 1}"
        filename = f"sheet{len(sheet_files) + 1}.xml"
        sheet_files.append((sheet, rel_id, filename, sheet_xml))

    workbook_sheets = "".join(
        f'<sheet name="{escape(name)}" sheetId="{i}" r:id="{rel_id}"/>'
        for i, (name, rel_id, _, _) in enumerate(sheet_files, start=1)
    )
    workbook_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{workbook_sheets}</sheets></workbook>"
    )
    rels_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        + "".join(
            f'<Relationship Id="{rel_id}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/{filename}"/>'
            for _, rel_id, filename, _ in sheet_files
        )
        + "</Relationships>"
    )
    content_types = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
        + "".join(
            f'<Override PartName="/xl/worksheets/{filename}" '
            'ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
            for _, _, filename, _ in sheet_files
        )
        + "</Types>"
    )
    root_rels = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", root_rels)
        zf.writestr("xl/workbook.xml", workbook_xml)
        zf.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        for _, _, filename, sheet_xml in sheet_files:
            zf.writestr(f"xl/worksheets/{filename}", sheet_xml)
    path.write_bytes(buffer.getvalue())


def export_collection_samples(
    database: Database,
    output_dir: Path,
    limit: int = 100,
    formats: tuple[str, ...] = ("csv", "xlsx"),
) -> dict[str, Any]:
    collections = list_user_collections(database)
    summary: dict[str, Any] = {"collections": [], "files": []}
    sheets: dict[str, list[dict[str, str]]] = {}

    for name in collections:
        docs = sample_documents(database, name, limit)
        rows = [flatten_document(doc) for doc in docs]
        sheets[name] = rows
        entry = {
            "name": name,
            "exported": len(rows),
            "total": database[name].estimated_document_count(),
        }
        summary["collections"].append(entry)
        logger.info(
            "Colección '%s': exportados %s de ~%s",
            name,
            len(rows),
            entry["total"],
        )
        if "csv" in formats:
            csv_path = output_dir / f"{name}.csv"
            write_csv(csv_path, rows)
            summary["files"].append(str(csv_path))

    if "xlsx" in formats:
        xlsx_path = output_dir / "mongo_sample.xlsx"
        if not sheets:
            sheets = {"_empty": []}
        write_xlsx(xlsx_path, sheets)
        summary["files"].append(str(xlsx_path))

    return summary

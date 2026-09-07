#!/usr/bin/env python3
"""Cliente CLI para consultar GDELT en BigQuery (cuenta de servicio Google).

No usa la API pública de GDELT (evita HTTP 429). Requiere el JSON de una
cuenta de servicio con acceso a BigQuery, o GOOGLE_APPLICATION_CREDENTIALS.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict, dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SUPPORTED_LANGUAGES = ("en", "es", "hu")
MEDIA_DOMAINS = {
    "bbc": ("bbc.com", "bbc.co.uk"),
    "reuters": ("reuters.com",),
    "guardian": ("theguardian.com", "guardian.com"),
    "eltiempo": ("eltiempo.com",),
    "elespectador": ("elespectador.com",),
    "index": ("index.hu",),
    "telex": ("telex.hu",),
}
TAG_ALIASES = {
    "environment": ("environment", "env"),
    "science": ("science", "sci"),
}
DEFAULT_LIMIT = 100
DEFAULT_OUTPUT = "results.json"
GDELT_PROJECT = "gdelt-bq"
GDELT_DATASET = "gdeltv2"
GDELT_TABLE = "gkg_partitioned"

logger = logging.getLogger("client")


@dataclass(frozen=True)
class QueryParams:
    keywords: list[str]
    tags: list[str]
    languages: list[str]
    media: list[str]
    start_date: date
    end_date: date
    limit: int


class ParameterError(ValueError):
    """Argumento de línea de comandos inválido."""


def parse_csv_list(raw: str | None) -> list[str]:
    if raw is None:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


def parse_iso_date(value: str, flag: str) -> date:
    try:
        return date.fromisoformat(value.strip())
    except (ValueError, AttributeError) as exc:
        raise ParameterError(
            f"{flag} debe tener formato YYYY-MM-DD. Valor recibido: {value!r}."
        ) from exc


def positive_int(value: str) -> int:
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"--limit debe ser un entero positivo. Valor recibido: {value!r}."
        ) from exc
    if number < 1:
        raise argparse.ArgumentTypeError(
            f"--limit debe ser un entero positivo. Valor recibido: {value!r}."
        )
    return number


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="client.py",
        description=(
            "Consulta GDELT en BigQuery y descarga artículos. "
            "Pase el JSON de la cuenta de servicio con --credentials "
            "(o defina GOOGLE_APPLICATION_CREDENTIALS). "
            "No usa la API pública de GDELT."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Idiomas: en, es, hu (filtro GKG TranslationInfo).\n"
            "En PowerShell escriba el comando en una sola línea.\n\n"
            "Ejemplos:\n"
            "  python client.py --credentials C:\\ruta\\cuenta.json "
            "--keywords biodiversity --start-date 2024-01-01 "
            "--end-date 2024-01-31 --limit 10\n"
            "  python client.py --keywords \"biodiversity,conservation\" "
            "--tags environment --languages \"en,es\" --media \"bbc,reuters\" "
            "--start-date 2024-01-01 --end-date 2024-01-31 --limit 100"
        ),
    )
    parser.add_argument(
        "--keywords",
        required=True,
        help='Palabras clave separadas por comas. Ejemplo: "biodiversity,conservation".',
    )
    parser.add_argument(
        "--tags",
        default="",
        help='Etiquetas opcionales, separadas por comas. Ejemplo: "environment,science".',
    )
    parser.add_argument(
        "--languages",
        default=",".join(SUPPORTED_LANGUAGES),
        help=(
            "Idiomas (en, es, hu). Uno, varios o los tres. "
            f"Por defecto: {','.join(SUPPORTED_LANGUAGES)}."
        ),
    )
    parser.add_argument(
        "--media",
        default="",
        help='Medios o dominios, separados por comas. Ejemplo: "bbc,reuters,guardian".',
    )
    parser.add_argument(
        "--start-date",
        dest="start_date",
        required=True,
        help="Fecha inicial (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--end-date",
        dest="end_date",
        required=True,
        help="Fecha final (YYYY-MM-DD).",
    )
    parser.add_argument(
        "--limit",
        type=positive_int,
        default=DEFAULT_LIMIT,
        help=f"Máximo de registros a obtener. Por defecto: {DEFAULT_LIMIT}.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Archivo JSON de salida. Por defecto: {DEFAULT_OUTPUT}.",
    )
    parser.add_argument(
        "--credentials",
        default=None,
        help=(
            "Ruta al JSON de cuenta de servicio de Google Cloud. "
            "Si se omite, se usa GOOGLE_APPLICATION_CREDENTIALS."
        ),
    )
    return parser.parse_args(argv)


def validate_params(args: argparse.Namespace) -> QueryParams:
    keywords = parse_csv_list(args.keywords)
    if not keywords:
        raise ParameterError(
            'Debe indicar al menos una palabra clave. Ejemplo: --keywords "biodiversity".'
        )

    languages = [code.lower() for code in parse_csv_list(args.languages)]
    if not languages:
        raise ParameterError(
            f"Debe indicar al menos un idioma. Valores permitidos: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    unknown = [code for code in languages if code not in SUPPORTED_LANGUAGES]
    if unknown:
        raise ParameterError(
            f"Idioma(s) no permitido(s): {', '.join(unknown)}. "
            f"Use uno o más de: {', '.join(SUPPORTED_LANGUAGES)}."
        )
    languages = list(dict.fromkeys(languages))

    start_date = parse_iso_date(args.start_date, "--start-date")
    end_date = parse_iso_date(args.end_date, "--end-date")
    if start_date > end_date:
        raise ParameterError(
            f"La fecha inicial ({start_date.isoformat()}) no puede ser posterior "
            f"a la fecha final ({end_date.isoformat()})."
        )

    return QueryParams(
        keywords=keywords,
        tags=parse_csv_list(args.tags),
        languages=languages,
        media=parse_csv_list(args.media),
        start_date=start_date,
        end_date=end_date,
        limit=args.limit,
    )


def build_query(params: QueryParams) -> dict[str, Any]:
    return {
        "keywords": params.keywords,
        "tags": params.tags,
        "languages": params.languages,
        "media": params.media,
        "start_date": params.start_date.isoformat(),
        "end_date": params.end_date.isoformat(),
        "limit": params.limit,
    }


def media_domains(media: list[str]) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for item in media:
        key = item.strip().lower().replace(" ", "")
        if not key:
            continue
        mapped = MEDIA_DOMAINS.get(key)
        candidates = [key]
        if mapped:
            candidates.extend(mapped)
        elif "." not in key:
            candidates.append(f"{key}.com")
        for domain in candidates:
            if domain not in seen:
                seen.add(domain)
                domains.append(domain)
    return domains


def expand_tags(tags: list[str]) -> list[str]:
    expanded: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        key = tag.strip().lower()
        if not key:
            continue
        pieces = TAG_ALIASES.get(key, (key,))
        for piece in pieces:
            if piece not in seen:
                seen.add(piece)
                expanded.append(piece)
    return expanded


def languages_for_query(languages: list[str]) -> list[str]:
    """Skip GKG language filter when all supported languages are requested.

    That matches the Mongo pipeline (keywords + dates only). TranslationInfo
    is empty for English and rarely filled, so filtering en+es+hu as AND/OR
    on that field often returns zero rows.
    """
    selected = {code.lower() for code in languages}
    if not selected or selected >= set(SUPPORTED_LANGUAGES):
        return []
    return [code for code in languages if code in SUPPORTED_LANGUAGES]


def apply_credentials(credentials_path: str | None) -> None:
    try:
        from dotenv import load_dotenv

        load_dotenv(REPO_ROOT / ".env", override=False)
    except ImportError:
        pass

    path = credentials_path or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
    path = str(path).strip().strip('"')
    if not path:
        raise RuntimeError(
            "Falta la cuenta de servicio de Google. Pase --credentials "
            "con la ruta del JSON, o defina GOOGLE_APPLICATION_CREDENTIALS. "
            "No suba ese archivo al repositorio; envíelo a su compañero por un canal privado."
        )
    creds = Path(path).expanduser()
    if not creds.is_file():
        raise RuntimeError(f"No se encontró el JSON de credenciales: {creds}")
    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = str(creds.resolve())
    logger.info("Usando credenciales BigQuery: %s", creds.resolve())


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def fetch_records(query: dict[str, Any], credentials_path: str | None = None) -> list[dict[str, Any]]:
    """Consulta GDELT GKG en BigQuery. No llama a api.gdeltproject.org."""
    apply_credentials(credentials_path)

    from src.gdelt.collectors.gdelt.bigquery_client import BigQueryGdeltClient
    from src.gdelt.collectors.gdelt.query_builder import build_client_articles_query
    from src.gdelt.common.config import DatasetConfig
    from src.gdelt.common.exceptions import BigQueryError

    start_date = date.fromisoformat(query["start_date"])
    end_exclusive = date.fromisoformat(query["end_date"]) + timedelta(days=1)
    dataset = DatasetConfig(project=GDELT_PROJECT, dataset=GDELT_DATASET, table=GDELT_TABLE)
    prepared = build_client_articles_query(
        dataset,
        start_date=start_date,
        end_date=end_exclusive,
        keywords=query["keywords"],
        row_limit=int(query["limit"]),
        tags=expand_tags(query.get("tags") or []),
        media=media_domains(query.get("media") or []),
        languages=languages_for_query(query.get("languages") or []),
    )
    lang_sql = languages_for_query(query.get("languages") or [])
    logger.info(
        "Consultando BigQuery GDELT (filtro_idioma=%s, tags=%s, media=%s, limit=%s)",
        lang_sql or "ninguno (igual que el pipeline Mongo)",
        query.get("tags") or [],
        query.get("media") or [],
        query["limit"],
    )

    client = BigQueryGdeltClient()
    try:
        result = client.run_query(prepared, page_size=min(int(query["limit"]), 1000))
        rows = [dict(row) for row in result.rows]
    except (BigQueryError, OSError, RuntimeError) as exc:
        raise RuntimeError(
            "No se pudo consultar GDELT en BigQuery. Verifique el JSON de la cuenta "
            "de servicio y que BigQuery esté habilitado en ese proyecto. "
            f"Detalle: {exc}"
        ) from exc
    finally:
        client.close()

    logger.info("Registros devueltos por BigQuery: %s", len(rows))
    return rows


def apply_limit(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return records[:limit]


def export_results(path: Path, query: dict[str, Any], records: list[dict[str, Any]]) -> None:
    payload = {
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "source": "bigquery",
        "query": query,
        "record_count": len(records),
        "records": records,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_jsonable) + "\n",
        encoding="utf-8",
    )


def run(args: argparse.Namespace) -> dict[str, Any]:
    started = datetime.now().timestamp()
    params = validate_params(args)
    query = build_query(params)

    logger.info("Parámetros utilizados: %s", json.dumps(asdict(params), ensure_ascii=False, default=str))
    logger.info("Consulta construida: %s", json.dumps(query, ensure_ascii=False))

    obtained = fetch_records(query, credentials_path=getattr(args, "credentials", None))
    processed = apply_limit(obtained, params.limit)

    output_path = Path(args.output)
    export_results(output_path, query, processed)

    elapsed = datetime.now().timestamp() - started
    sample_urls = [
        row.get("DocumentIdentifier") or row.get("url")
        for row in processed[:5]
        if row.get("DocumentIdentifier") or row.get("url")
    ]
    summary = {
        "records_obtained": len(obtained),
        "records_processed": len(processed),
        "output": str(output_path.resolve()),
        "elapsed_seconds": round(elapsed, 3),
        "sample_urls": sample_urls,
        "source": "bigquery",
    }
    logger.info("Registros obtenidos: %s", summary["records_obtained"])
    logger.info("Registros procesados/descargados: %s", summary["records_processed"])
    logger.info("Tiempo de ejecución: %s s", summary["elapsed_seconds"])
    logger.info("Resultados en: %s", summary["output"])
    return summary


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    try:
        args = parse_args(argv)
        summary = run(args)
    except ParameterError as exc:
        logger.error("%s", exc)
        return 2
    except Exception as exc:
        logger.error("Error durante la ejecución: %s", exc)
        return 1

    print("\n=== Resumen ===")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

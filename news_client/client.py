#!/usr/bin/env python3
"""Cliente CLI para consultar noticias en GDELT (API pública DOC 2.0).

Tras clonar el repositorio basta con Python 3.10+ e internet: no hay YAML,
claves ni paquetes extra. Los socios cambian la búsqueda con argumentos.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import asdict, dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Any

SUPPORTED_LANGUAGES = ("en", "es", "hu")
LANGUAGE_TO_GDELT = {
    "en": "english",
    "es": "spanish",
    "hu": "hungarian",
}
MEDIA_DOMAINS = {
    "bbc": ("bbc.com", "bbc.co.uk"),
    "reuters": ("reuters.com",),
    "guardian": ("theguardian.com", "guardian.com"),
    "eltiempo": ("eltiempo.com",),
    "elespectador": ("elespectador.com",),
    "index": ("index.hu",),
    "telex": ("telex.hu",),
}
DEFAULT_LIMIT = 100
DEFAULT_OUTPUT = "results.json"
GDELT_DOC_API = "https://api.gdeltproject.org/api/v2/doc/doc"
GDELT_MAX_RECORDS = 250

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
            "Consulta la API pública de GDELT y descarga artículos. "
            "Cambie keywords, tags, idiomas, medios, fechas y --limit en el "
            "comando; no edite el código ni configure credenciales."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Idiomas permitidos: en, es, hu (se envían a GDELT como "
            "sourcelang:english/spanish/hungarian).\n"
            f"--limit por defecto: {DEFAULT_LIMIT} (máximo de la API: {GDELT_MAX_RECORDS}).\n"
            "En PowerShell escriba el comando en una sola línea.\n\n"
            "Ejemplos:\n"
            "  python client.py --keywords biodiversity --start-date 2026-01-01 "
            "--end-date 2026-01-31 --limit 10\n"
            "  python client.py --keywords \"biodiversity,conservation\" "
            "--tags environment --languages \"en,es\" --media \"bbc,reuters\" "
            "--start-date 2026-01-01 --end-date 2026-01-31 --limit 100"
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
            "Se aplican en la consulta GDELT. "
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
        help=f"Máximo de registros a obtener (hasta {GDELT_MAX_RECORDS}). Por defecto: {DEFAULT_LIMIT}.",
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help=f"Archivo JSON de salida. Por defecto: {DEFAULT_OUTPUT}.",
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


def _quote_term(term: str) -> str:
    cleaned = term.strip()
    if " " in cleaned:
        return f'"{cleaned}"'
    return cleaned


def _or_group(terms: list[str]) -> str:
    if len(terms) == 1:
        return terms[0]
    return "(" + " OR ".join(terms) + ")"


def media_domains(media: list[str]) -> list[str]:
    domains: list[str] = []
    seen: set[str] = set()
    for item in media:
        key = item.strip().lower().replace(" ", "")
        if not key:
            continue
        mapped = MEDIA_DOMAINS.get(key)
        candidates = list(mapped) if mapped else ([key] if "." in key else [key, f"{key}.com"])
        for domain in candidates:
            if domain not in seen:
                seen.add(domain)
                domains.append(domain)
    return domains


def build_gdelt_query_text(query: dict[str, Any]) -> str:
    """Arma el parámetro query de GDELT DOC, incluyendo sourcelang."""
    parts: list[str] = [_or_group([_quote_term(k) for k in query["keywords"]])]
    tags = query.get("tags") or []
    if tags:
        parts.append(_or_group([_quote_term(tag) for tag in tags]))

    lang_ops = [
        f"sourcelang:{LANGUAGE_TO_GDELT[code]}"
        for code in query.get("languages") or []
        if code in LANGUAGE_TO_GDELT
    ]
    if lang_ops:
        parts.append(_or_group(lang_ops))

    domain_ops = [f"domain:{domain}" for domain in media_domains(query.get("media") or [])]
    if domain_ops:
        parts.append(_or_group(domain_ops))

    return " ".join(parts)


def filter_by_language(
    articles: list[dict[str, Any]], languages: list[str]
) -> list[dict[str, Any]]:
    allowed = {LANGUAGE_TO_GDELT[code] for code in languages if code in LANGUAGE_TO_GDELT}
    if not allowed:
        return articles
    kept: list[dict[str, Any]] = []
    for article in articles:
        raw = str(article.get("language") or "").strip().lower()
        if raw in allowed:
            kept.append(article)
    return kept


def _jsonable(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return str(value)


def fetch_records(query: dict[str, Any]) -> list[dict[str, Any]]:
    """Consulta la API pública DOC 2.0 de GDELT (sin API key)."""
    gdelt_query = build_gdelt_query_text(query)
    maxrecords = min(int(query["limit"]), GDELT_MAX_RECORDS)
    if int(query["limit"]) > GDELT_MAX_RECORDS:
        logger.info(
            "GDELT DOC permite como máximo %s registros por llamada; se usará --limit %s.",
            GDELT_MAX_RECORDS,
            GDELT_MAX_RECORDS,
        )

    start = date.fromisoformat(query["start_date"]).strftime("%Y%m%d000000")
    end = date.fromisoformat(query["end_date"]).strftime("%Y%m%d235959")
    params = {
        "query": gdelt_query,
        "mode": "ArtList",
        "format": "json",
        "maxrecords": str(maxrecords),
        "sort": "DateDesc",
        "startdatetime": start,
        "enddatetime": end,
    }
    url = f"{GDELT_DOC_API}?{urllib.parse.urlencode(params)}"
    logger.info("Ejecutando consulta GDELT: %s", gdelt_query)
    logger.info("Idiomas aplicados: %s", ", ".join(query.get("languages") or []))

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "dragons-data-etl-client/1.0"},
    )
    last_error: Exception | None = None
    raw = ""
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                raw = response.read().decode("utf-8", errors="replace")
            last_error = None
            break
        except urllib.error.HTTPError as exc:
            last_error = exc
            if exc.code == 429 and attempt < 3:
                wait = 8 * attempt
                logger.info(
                    "GDELT pidió esperar (HTTP 429). Reintento %s/3 en %s s.",
                    attempt + 1,
                    wait,
                )
                time.sleep(wait)
                continue
            break
        except urllib.error.URLError as exc:
            last_error = exc
            break

    if last_error is not None:
        hint = ""
        if isinstance(last_error, urllib.error.HTTPError) and last_error.code == 429:
            hint = " La API pública limita peticiones seguidas; espere un minuto y vuelva a intentar."
        raise RuntimeError(
            "No se pudo contactar la API pública de GDELT. Compruebe la conexión a internet."
            f"{hint} Detalle: {last_error}"
        ) from last_error

    try:
        payload = json.loads(raw) if raw.strip() else {}
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GDELT no devolvió JSON válido. Intente de nuevo en unos segundos o estreche fechas/filtros."
        ) from exc

    articles = payload.get("articles") if isinstance(payload, dict) else None
    if not isinstance(articles, list):
        articles = []

    filtered = filter_by_language(articles, query.get("languages") or [])
    logger.info(
        "Artículos de GDELT: %s; tras filtro de idioma: %s",
        len(articles),
        len(filtered),
    )
    return filtered


def apply_limit(records: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    return records[: min(limit, GDELT_MAX_RECORDS)]


def export_results(path: Path, query: dict[str, Any], records: list[dict[str, Any]]) -> None:
    payload = {
        "exported_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "query": query,
        "gdelt_query": build_gdelt_query_text(query),
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

    obtained = fetch_records(query)
    processed = apply_limit(obtained, params.limit)

    output_path = Path(args.output)
    export_results(output_path, query, processed)

    elapsed = datetime.now().timestamp() - started
    sample_urls = [row.get("url") for row in processed[:5] if row.get("url")]
    summary = {
        "records_obtained": len(obtained),
        "records_processed": len(processed),
        "output": str(output_path.resolve()),
        "elapsed_seconds": round(elapsed, 3),
        "sample_urls": sample_urls,
        "gdelt_query": build_gdelt_query_text(query),
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

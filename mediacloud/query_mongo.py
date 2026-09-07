from __future__ import annotations

import csv
import json
import os
import re
from pathlib import Path
from typing import Any

import certifi
from bson import ObjectId
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import PyMongoError


DEFAULT_FIELDS = [
    "url",
    "title",
    "language",
    "keywords",
    "publish_date",
    "media_name",
    "contenido",
    "eid",
    "hash",
    "indexed_date",
    "media_url",
]

FIELD_MENU_ORDER = [
    "url",
    "title",
    "language",
    "keywords",
    "publish_date",
    "media_name",
    "contenido",
    "eid",
    "hash",
    "indexed_date",
    "media_url",
    "_id",
]

LANGUAGE_NAMES = {
    "es": "Español",
    "en": "Inglés",
    "hu": "Húngaro",
}



# ============================================================================
# INTERNAL KEYWORD CODE NORMALIZATION
# ============================================================================
#
# Some Spanish whitelist families were split into multiple CSV files only
# for operational/query-size reasons. For the client they still represent
# one conceptual keyword family.
#
# Examples:
#   B2 - 1.csv + B2 - 2.csv -> B2
#   C1.csv + C2.csv         -> C
#   D1.csv + D2.csv         -> D
#
# We support both old documents already stored in MongoDB and future
# canonical documents.

KEYWORD_CODE_ALIASES = {
    "es": {
        "B2": ["B2", "B2 - 1", "B2 - 2"],
        "C": ["C", "C1", "C2"],
        "D": ["D", "D1", "D2"],
    },
    "en": {},
    "hu": {},
}


def canonical_keyword_code(
    language: str,
    stored_code: str,
) -> str:
    """
    Convert a code stored in MongoDB to the conceptual code used by the
    keyword TXT.

    Example:
        es + "B2 - 1" -> "B2"
        es + "C2"     -> "C"
        en + "B2"     -> "B2"
    """
    language_aliases = KEYWORD_CODE_ALIASES.get(language, {})

    for canonical_code, aliases in language_aliases.items():
        if stored_code in aliases:
            return canonical_code

    return stored_code


def stored_codes_for_canonical(
    language: str,
    canonical_code: str,
) -> list[str]:
    """
    Return every MongoDB code that can represent a conceptual keyword family.

    Example:
        es + B2 -> ["B2", "B2 - 1", "B2 - 2"]
        es + C  -> ["C", "C1", "C2"]
        en + C  -> ["C"]
    """
    return KEYWORD_CODE_ALIASES.get(
        language,
        {},
    ).get(
        canonical_code,
        [canonical_code],
    )


def expand_stored_keyword_codes(
    language: str,
    canonical_codes: list[str],
) -> list[str]:
    expanded: list[str] = []

    for canonical_code in canonical_codes:
        for stored_code in stored_codes_for_canonical(
            language,
            canonical_code,
        ):
            if stored_code not in expanded:
                expanded.append(stored_code)

    return expanded


# ============================================================================
# MONGODB
# ============================================================================

def create_client(uri: str) -> MongoClient:
    client = MongoClient(
        uri,
        tlsCAFile=certifi.where(),
        serverSelectionTimeoutMS=10_000,
        connectTimeoutMS=10_000,
        socketTimeoutMS=30_000,
        retryWrites=True,
    )
    client.admin.command("ping")
    return client


# ============================================================================
# KEYWORD MAPS
# ============================================================================

def detect_keyword_file_language(text: str) -> str | None:
    lowered = text.lower()

    if "biodiverzitás and" in lowered:
        return "hu"

    if "biodiversidad and" in lowered:
        return "es"

    if "biodiversity and" in lowered:
        return "en"

    return None


def clean_category_title(raw_title: str) -> str:
    title = re.sub(
        r"\s*\([^)]*términos[^)]*\)\s*",
        " ",
        raw_title,
        flags=re.IGNORECASE,
    )

    title = re.sub(
        r"\s*\(Fue partida en 2\)\s*",
        " ",
        title,
        flags=re.IGNORECASE,
    )

    title = title.replace("===", " ")

    return re.sub(
        r"\s+",
        " ",
        title,
    ).strip()


def extract_terms(expression: str) -> list[str]:
    terms: list[str] = []

    for clause in re.findall(
        r"\(([^()]*)\)",
        expression,
    ):
        if " AND " not in clause:
            continue

        _, value = clause.split(
            " AND ",
            1,
        )

        value = (
            value.strip()
            .strip('"')
            .strip()
        )

        if value and value not in terms:
            terms.append(value)

    return terms


def parse_keyword_txt(
    path: Path,
) -> tuple[str, dict[str, dict[str, Any]]]:
    text = path.read_text(
        encoding="utf-8-sig"
    )

    language = detect_keyword_file_language(
        text
    )

    if not language:
        raise ValueError(
            f"No pude detectar el idioma de {path}"
        )

    lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip()
    ]

    mapping: dict[str, dict[str, Any]] = {}

    index = 0

    while index < len(lines):
        line = lines[index]

        match = re.match(
            r"^===\s*([A-Z](?:\d+)?)\.\s*(.+?)\s*===\s*$",
            line,
        )

        if not match:
            index += 1
            continue

        code = match.group(1)

        category = clean_category_title(
            match.group(2)
        )

        expression = (
            lines[index + 1]
            if index + 1 < len(lines)
            else ""
        )

        mapping[code] = {
            "category": category,
            "terms": extract_terms(
                expression
            ),
        }

        index += 2

    return language, mapping


def load_keyword_maps(
    keyword_directory: Path,
) -> dict[str, dict[str, dict[str, Any]]]:
    if not keyword_directory.exists():
        raise FileNotFoundError(
            f"No existe: {keyword_directory}"
        )

    maps: dict[
        str,
        dict[str, dict[str, Any]],
    ] = {}

    txt_files = sorted(
        keyword_directory.glob("*.txt")
    )

    if not txt_files:
        raise FileNotFoundError(
            f"No hay .txt en {keyword_directory}"
        )

    for path in txt_files:
        try:
            language, mapping = parse_keyword_txt(
                path
            )
        except ValueError as exc:
            print(
                f"WARNING | {exc}"
            )
            continue

        maps[language] = mapping

        print(
            f"Keyword map loaded: "
            f"{path.name} -> "
            f"language={language} -> "
            f"categories={len(mapping)}"
        )

    return maps


# ============================================================================
# CLIENT-FACING KEYWORD CONVERSION
# ============================================================================

def enrich_keywords(
    document: dict[str, Any],
    keyword_maps: dict[
        str,
        dict[str, dict[str, Any]],
    ],
) -> dict[str, Any]:
    result = dict(document)

    language = result.get(
        "language"
    )

    code = result.get(
        "keywords"
    )

    if not language or not code:
        return result

    # Mongo may contain split Spanish codes such as B2 - 1, C1 or D2.
    # The TXT uses the conceptual codes B2, C and D.
    canonical_code = canonical_keyword_code(
        str(language),
        str(code),
    )

    info = (
        keyword_maps
        .get(str(language), {})
        .get(canonical_code)
    )

    if not info:
        result["keyword_category"] = None
        result["keywords"] = []
        return result

    result["keyword_category"] = info[
        "category"
    ]

    result["keywords"] = info[
        "terms"
    ]

    return result


def project_for_client(
    document: dict[str, Any],
    selected_fields: list[str] | None,
) -> dict[str, Any]:
    if selected_fields is None:
        return document

    output: dict[str, Any] = {}

    for field in selected_fields:
        if field in document:
            output[field] = document[
                field
            ]

        if (
            field == "keywords"
            and "keyword_category" in document
        ):
            output["keyword_category"] = document[
                "keyword_category"
            ]

    return output


# ============================================================================
# DISPLAY
# ============================================================================

def json_default(value: Any):
    if isinstance(value, ObjectId):
        return str(value)

    return str(value)


def print_documents(
    documents: list[dict[str, Any]],
) -> None:
    if not documents:
        print(
            "\nNo se encontraron documentos.\n"
        )
        return

    print(
        f"\nResultados mostrados: "
        f"{len(documents)}\n"
    )

    for index, document in enumerate(
        documents,
        start=1,
    ):
        print(
            "=" * 90
        )
        print(
            f"DOCUMENTO {index}"
        )
        print(
            "=" * 90
        )

        print(
            json.dumps(
                document,
                ensure_ascii=False,
                indent=2,
                default=json_default,
            )
        )

        print()


# ============================================================================
# FIELD DISCOVERY
# ============================================================================

def discover_fields(
    collection,
    sample_size: int = 200,
) -> list[str]:
    fields: set[str] = set()

    for document in collection.find(
        {},
        limit=sample_size,
    ):
        fields.update(
            document.keys()
        )

    ordered: list[str] = []

    for field in FIELD_MENU_ORDER:
        if field in fields:
            ordered.append(
                field
            )
            fields.remove(
                field
            )

    ordered.extend(
        sorted(fields)
    )

    return ordered


def show_fields(
    fields: list[str],
) -> None:
    print(
        "\nCampos disponibles:"
    )

    for index, field in enumerate(
        fields,
        start=1,
    ):
        print(
            f"  {index}. {field}"
        )

    print()


def choose_field_by_number(
    fields: list[str],
    *,
    prompt: str = "Número del campo: ",
    allow_blank: bool = False,
    show_menu: bool = True,
) -> str | None:
    if show_menu:
        show_fields(
            fields
        )

    while True:
        raw = input(
            prompt
        ).strip()

        if (
            not raw
            and allow_blank
        ):
            return None

        try:
            index = int(
                raw
            )

        except ValueError:
            print(
                "Escribe el número del campo."
            )
            continue

        if (
            1
            <= index
            <= len(fields)
        ):
            return fields[
                index - 1
            ]

        print(
            "Número fuera de rango."
        )


def choose_fields_by_numbers(
    fields: list[str],
) -> list[str] | None:
    show_fields(
        fields
    )

    raw = input(
        "Números separados por coma "
        "(ej: 1,2,4): "
    ).strip()

    if not raw:
        return None

    selected: list[str] = []

    for part in raw.split(","):
        part = part.strip()

        if not part:
            continue

        try:
            index = int(
                part
            )

        except ValueError:
            print(
                f"Ignorando '{part}': "
                "no es un número."
            )
            continue

        if not (
            1
            <= index
            <= len(fields)
        ):
            print(
                f"Ignorando '{part}': "
                "fuera de rango."
            )
            continue

        field = fields[
            index - 1
        ]

        if field not in selected:
            selected.append(
                field
            )

    return (
        selected
        if selected
        else None
    )


# ============================================================================
# FIELD SELECTION / PROJECTION
# ============================================================================

def ask_selected_fields(
    fields: list[str],
) -> list[str] | None:
    print(
        "\n¿Qué campos quieres mostrar?"
    )
    print(
        "1. Todos los campos"
    )
    print(
        "2. Elegir campos específicos"
    )

    option = input(
        "Opción: "
    ).strip()

    if option != "2":
        return None

    return choose_fields_by_numbers(
        fields
    )


def build_mongo_projection(
    selected_fields: list[str] | None,
) -> dict[str, int] | None:
    if selected_fields is None:
        return None

    projection = {
        field: 1
        for field in selected_fields
    }

    # Needed internally to translate keyword code into client-facing terms.
    if "keywords" in selected_fields:
        projection["language"] = 1
        projection["keywords"] = 1

    if "_id" not in selected_fields:
        projection["_id"] = 0

    return projection


# ============================================================================
# FILTERS
# ============================================================================

def parse_scalar(
    value: str,
) -> Any:
    lowered = value.lower()

    if lowered == "true":
        return True

    if lowered == "false":
        return False

    if lowered in {
        "null",
        "none",
    }:
        return None

    try:
        if "." in value:
            return float(value)

        return int(value)

    except ValueError:
        return value


def build_single_filter(
    field: str,
) -> dict[str, Any]:
    print(
        "\nOperadores:"
    )
    print(
        "1. Igual a"
    )
    print(
        "2. Contiene texto"
    )
    print(
        "3. Empieza por"
    )
    print(
        "4. Termina en"
    )
    print(
        "5. Está en una lista"
    )
    print(
        "6. Diferente de"
    )
    print(
        "7. Existe"
    )
    print(
        "8. No existe"
    )

    operator = input(
        "Opción: "
    ).strip()

    if operator == "1":
        return {
            field: parse_scalar(
                input(
                    "Valor: "
                ).strip()
            )
        }

    if operator == "2":
        value = input(
            "Texto: "
        ).strip()

        return {
            field: {
                "$regex": re.escape(value),
                "$options": "i",
            }
        }

    if operator == "3":
        value = input(
            "Texto inicial: "
        ).strip()

        return {
            field: {
                "$regex": "^" + re.escape(value),
                "$options": "i",
            }
        }

    if operator == "4":
        value = input(
            "Texto final: "
        ).strip()

        return {
            field: {
                "$regex": re.escape(value) + "$",
                "$options": "i",
            }
        }

    if operator == "5":
        raw = input(
            "Valores separados por coma: "
        ).strip()

        values = [
            parse_scalar(
                value.strip()
            )
            for value in raw.split(",")
            if value.strip()
        ]

        return {
            field: {
                "$in": values
            }
        }

    if operator == "6":
        return {
            field: {
                "$ne": parse_scalar(
                    input(
                        "Valor: "
                    ).strip()
                )
            }
        }

    if operator == "7":
        return {
            field: {
                "$exists": True
            }
        }

    if operator == "8":
        return {
            field: {
                "$exists": False
            }
        }

    return {
        field: parse_scalar(
            input(
                "Valor: "
            ).strip()
        )
    }


# ============================================================================
# LANGUAGE / KEYWORDS
# ============================================================================

def choose_language() -> str:
    print(
        "\nIdioma:"
    )
    print(
        "1. Español (es)"
    )
    print(
        "2. Inglés (en)"
    )
    print(
        "3. Húngaro (hu)"
    )

    while True:
        option = input(
            "Opción: "
        ).strip()

        language = {
            "1": "es",
            "2": "en",
            "3": "hu",
        }.get(
            option
        )

        if language:
            return language

        print(
            "Opción no válida."
        )


def keyword_options(
    keyword_maps,
    language: str,
) -> list[
    tuple[
        str,
        dict[str, Any],
    ]
]:
    return list(
        keyword_maps
        .get(language, {})
        .items()
    )


def show_keyword_options(
    keyword_maps,
    language: str,
    *,
    preview_terms: int = 4,
) -> list[
    tuple[
        str,
        dict[str, Any],
    ]
]:
    options = keyword_options(
        keyword_maps,
        language,
    )

    language_name = (
        LANGUAGE_NAMES.get(
            language,
            language,
        )
    )

    print(
        f"\nCategorías de keywords — "
        f"{language_name} ({language}):"
    )

    if not options:
        print(
            "No hay categorías cargadas "
            "para este idioma.\n"
        )
        return []

    for index, (
        code,
        info,
    ) in enumerate(
        options,
        start=1,
    ):
        category = str(
            info.get(
                "category",
                "",
            )
        )

        terms = [
            str(term)
            for term in info.get(
                "terms",
                [],
            )
        ]

        preview = ", ".join(
            terms[
                :preview_terms
            ]
        )

        if (
            len(terms)
            > preview_terms
        ):
            preview += ", ..."

        print(
            f"  {index}. "
            f"{code} — {category}"
        )

        if preview:
            print(
                f"     Ej.: {preview}"
            )

    print()

    return options


def choose_keyword_codes(
    keyword_maps,
    language: str,
    *,
    allow_multiple: bool = True,
) -> list[str]:
    options = show_keyword_options(
        keyword_maps,
        language,
    )

    if not options:
        return []

    if allow_multiple:
        prompt = (
            "Número(s) de categoría "
            "separados por coma "
            "(ej: 1,3): "
        )
    else:
        prompt = (
            "Número de categoría: "
        )

    raw = input(
        prompt
    ).strip()

    if not raw:
        return []

    selected_codes: list[str] = []

    parts = (
        raw.split(",")
        if allow_multiple
        else [raw]
    )

    for part in parts:
        part = part.strip()

        try:
            index = int(
                part
            )

        except ValueError:
            print(
                f"Ignorando '{part}': "
                "no es un número."
            )
            continue

        if not (
            1
            <= index
            <= len(options)
        ):
            print(
                f"Ignorando '{part}': "
                "fuera de rango."
            )
            continue

        code = options[
            index - 1
        ][0]

        if code not in selected_codes:
            selected_codes.append(
                code
            )

    if selected_codes:
        print(
            "\nSeleccionado: "
            + ", ".join(
                selected_codes
            )
        )

        for code in selected_codes:
            info = (
                keyword_maps[
                    language
                ][
                    code
                ]
            )

            print(
                f"\n{code} — "
                f"{info.get('category', '')}"
            )

            print(
                "Keywords: "
                + " | ".join(
                    str(term)
                    for term
                    in info.get(
                        "terms",
                        [],
                    )
                )
            )

        print()

    return selected_codes


def find_keyword_codes(
    keyword_maps,
    language: str,
    search_text: str,
) -> list[str]:
    needle = (
        search_text
        .casefold()
    )

    matches: list[str] = []

    for code, info in (
        keyword_maps
        .get(language, {})
        .items()
    ):
        category = str(
            info.get(
                "category",
                "",
            )
        )

        if needle in category.casefold():
            matches.append(
                code
            )
            continue

        for term in info.get(
            "terms",
            [],
        ):
            if needle in str(
                term
            ).casefold():
                matches.append(
                    code
                )
                break

    return matches


def print_keyword_matches(
    keyword_maps,
    language: str,
    codes: list[str],
) -> None:
    if not codes:
        return

    print(
        "\nCategorías encontradas:"
    )

    for code in codes:
        info = (
            keyword_maps
            .get(language, {})
            .get(code, {})
        )

        terms = [
            str(term)
            for term in info.get(
                "terms",
                [],
            )
        ]

        preview = ", ".join(
            terms[:5]
        )

        if len(terms) > 5:
            preview += ", ..."

        print(
            f"- {code} — "
            f"{info.get('category', '')}"
        )

        if preview:
            print(
                f"  Ej.: {preview}"
            )

    print()


def build_keyword_query(
    language: str,
    codes: list[str],
) -> dict[str, Any]:
    mongo_keyword_codes = (
        expand_stored_keyword_codes(
            language,
            codes,
        )
    )

    return {
        "language": language,
        "keywords": {
            "$in": mongo_keyword_codes
        },
    }


def search_by_real_keyword(
    collection,
    keyword_maps,
    fields,
):
    language = choose_language()

    print(
        "\n¿Cómo quieres elegir la keyword?"
    )
    print(
        "1. Ver categorías y elegir por número"
    )
    print(
        "2. Buscar escribiendo una palabra"
    )

    mode = input(
        "Opción: "
    ).strip()

    if mode == "2":
        text = input(
            "Escribe una keyword "
            "o parte de ella: "
        ).strip()

        codes = find_keyword_codes(
            keyword_maps,
            language,
            text,
        )

        if not codes:
            print(
                f"\nNo encontré keywords para "
                f"'{text}' en '{language}'.\n"
            )
            return []

        print_keyword_matches(
            keyword_maps,
            language,
            codes,
        )

    else:
        codes = choose_keyword_codes(
            keyword_maps,
            language,
            allow_multiple=True,
        )

        if not codes:
            print(
                "\nNo seleccionaste "
                "ninguna categoría.\n"
            )
            return []

    query = build_keyword_query(
        language,
        codes,
    )

    print(
        "\nConsulta por categorías: "
        + ", ".join(codes)
    )

    selected_fields = ask_selected_fields(
        fields
    )

    sort_spec = ask_sort(
        fields
    )

    limit = ask_limit()

    total = collection.count_documents(
        query
    )

    print(
        f"\nCoincidencias en MongoDB: "
        f"{total}"
    )

    return execute_query(
        collection,
        query,
        selected_fields,
        limit,
        sort_spec,
        keyword_maps,
    )


def ask_filters(
    fields: list[str],
    keyword_maps,
) -> dict[str, Any]:
    filters: list[
        dict[str, Any]
    ] = []

    while True:
        field = choose_field_by_number(
            fields,
            prompt=(
                "Número del campo a filtrar "
                "(Enter para terminar): "
            ),
            allow_blank=True,
            show_menu=True,
        )

        if field is None:
            break

        # Language gets a simple numbered language menu.
        if field == "language":
            language = choose_language()

            filters.append(
                {
                    "language": language
                }
            )

        # Keywords get a language + conceptual category menu.
        elif field == "keywords":
            language = choose_language()

            codes = choose_keyword_codes(
                keyword_maps,
                language,
                allow_multiple=True,
            )

            if not codes:
                print(
                    "No se agregó "
                    "el filtro de keywords."
                )
                continue

            filters.append(
                build_keyword_query(
                    language,
                    codes,
                )
            )

        else:
            filters.append(
                build_single_filter(
                    field
                )
            )

        more = input(
            "¿Agregar otro filtro? [s/N]: "
        ).strip().lower()

        if more not in {
            "s",
            "si",
            "sí",
            "y",
            "yes",
        }:
            break

    if not filters:
        return {}

    if len(filters) == 1:
        return filters[0]

    return {
        "$and": filters
    }


# ============================================================================
# QUERY OPTIONS
# ============================================================================

def ask_limit() -> int:
    raw = input(
        "\nCantidad a mostrar "
        "(Enter=20, 0=todos): "
    ).strip()

    if not raw:
        return 20

    try:
        return max(
            int(raw),
            0,
        )

    except ValueError:
        return 20


def ask_sort(
    fields: list[str],
):
    option = input(
        "\n¿Ordenar resultados? [s/N]: "
    ).strip().lower()

    if option not in {
        "s",
        "si",
        "sí",
        "y",
        "yes",
    }:
        return None

    field = choose_field_by_number(
        fields,
        prompt="Número del campo: ",
        show_menu=True,
    )

    if field is None:
        return None

    print(
        "\nDirección:"
    )
    print(
        "1. Ascendente"
    )
    print(
        "2. Descendente"
    )

    direction = input(
        "Opción: "
    ).strip()

    return (
        field,
        -1 if direction == "2" else 1,
    )


# ============================================================================
# QUERY EXECUTION
# ============================================================================

def ask_limit() -> int:
    raw = input(
        "\nCantidad a mostrar "
        "(Enter=20, 0=todos): "
    ).strip()

    if not raw:
        return 20

    try:
        return max(
            int(raw),
            0,
        )

    except ValueError:
        return 20


def ask_sort(
    fields: list[str],
):
    option = input(
        "\n¿Ordenar resultados? [s/N]: "
    ).strip().lower()

    if option not in {
        "s",
        "si",
        "sí",
        "y",
        "yes",
    }:
        return None

    show_fields(
        fields
    )

    field = input(
        "Campo: "
    ).strip()

    if field not in fields:
        print(
            "Campo no válido. Sin orden."
        )
        return None

    direction = input(
        "1=ascendente, -1=descendente: "
    ).strip()

    return (
        field,
        -1 if direction == "-1" else 1,
    )


def execute_query(
    collection,
    query,
    selected_fields,
    limit,
    sort_spec,
    keyword_maps,
):
    projection = build_mongo_projection(
        selected_fields
    )

    cursor = collection.find(
        query,
        projection,
    )

    if sort_spec:
        cursor = cursor.sort(
            sort_spec[0],
            sort_spec[1],
        )

    if limit > 0:
        cursor = cursor.limit(
            limit
        )

    results = []

    for document in cursor:
        enriched = enrich_keywords(
            document,
            keyword_maps,
        )

        results.append(
            project_for_client(
                enriched,
                selected_fields,
            )
        )

    return results


# ============================================================================
# OTHER QUERY HELPERS
# ============================================================================

def query_by_language(
    collection,
    fields,
    keyword_maps,
):
    language = choose_language()

    query = {
        "language": language
    }

    selected_fields = ask_selected_fields(
        fields
    )

    sort_spec = ask_sort(
        fields
    )

    limit = ask_limit()

    total = collection.count_documents(
        query
    )

    print(
        f"\nCoincidencias para "
        f"language='{language}': "
        f"{total}"
    )

    return execute_query(
        collection,
        query,
        selected_fields,
        limit,
        sort_spec,
        keyword_maps,
    )


def show_distinct_values(
    collection,
    fields,
    keyword_maps,
):
    field = choose_field_by_number(
        fields,
        prompt="Número del campo: ",
        show_menu=True,
    )

    if field is None:
        return

    if field == "keywords":
        language = choose_language()

        show_keyword_options(
            keyword_maps,
            language,
            preview_terms=6,
        )

        return

    values = sorted(
        collection.distinct(
            field
        ),
        key=lambda value: str(value),
    )

    print(
        f"\nValores distintos de "
        f"'{field}' ({len(values)}):"
    )

    for index, value in enumerate(
        values,
        start=1,
    ):
        print(
            f"{index}. {value}"
        )

    print()



def csv_cell_value(value: Any) -> str:
    """
    Convert Mongo/client values into Excel-friendly CSV cells.

    Lists such as keywords become:
        cambio climático | calentamiento global | ...

    Dicts are serialized as JSON.
    """
    if value is None:
        return ""

    if isinstance(value, list):
        return " | ".join(
            str(item)
            for item in value
        )

    if isinstance(value, dict):
        return json.dumps(
            value,
            ensure_ascii=False,
            default=json_default,
        )

    if isinstance(value, ObjectId):
        return str(value)

    return str(value)


def csv_field_order(
    results: list[dict[str, Any]],
) -> list[str]:
    """
    Build a stable, readable column order for Excel.
    """
    preferred = [
        "_id",
        "eid",
        "indexed_date",
        "media_name",
        "media_url",
        "publish_date",
        "title",
        "url",
        "language",
        "keyword_category",
        "keywords",
        "contenido",
    ]

    detected: set[str] = set()

    for result in results:
        detected.update(
            result.keys()
        )

    ordered = [
        field
        for field in preferred
        if field in detected
    ]

    ordered.extend(
        sorted(
            detected - set(ordered)
        )
    )

    return ordered


def export_json(
    results: list[dict[str, Any]],
    base_name: str,
) -> Path:
    path = Path(
        base_name + ".json"
    ).resolve()

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            results,
            file,
            ensure_ascii=False,
            indent=2,
            default=json_default,
        )

    return path


def export_csv(
    results: list[dict[str, Any]],
    base_name: str,
) -> Path:
    """
    Export UTF-8 CSV that can be opened directly with Excel.

    utf-8-sig writes a BOM so Excel recognizes accents and Hungarian
    characters correctly.
    """
    path = Path(
        base_name + ".csv"
    ).resolve()

    fieldnames = csv_field_order(
        results
    )

    with path.open(
        "w",
        encoding="utf-8-sig",
        newline="",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames,
            delimiter=",",
            quoting=csv.QUOTE_MINIMAL,
        )

        writer.writeheader()

        for result in results:
            row = {
                field: csv_cell_value(
                    result.get(field)
                )
                for field in fieldnames
            }

            writer.writerow(
                row
            )

    return path


def export_results(
    results: list[dict[str, Any]],
) -> None:
    if not results:
        print(
            "\nNo hay resultados para exportar.\n"
        )
        return

    print(
        "\nFormato de exportación:"
    )
    print(
        "1. JSON"
    )
    print(
        "2. CSV compatible con Excel"
    )
    print(
        "3. JSON + CSV"
    )

    option = input(
        "Opción: "
    ).strip()

    raw_name = input(
        "Nombre base del archivo "
        "(Enter=query_results): "
    ).strip()

    if not raw_name:
        raw_name = "query_results"

    # Avoid accidentally producing query_results.json.csv.
    base_path = Path(
        raw_name
    )

    if base_path.suffix.lower() in {
        ".json",
        ".csv",
    }:
        base_path = base_path.with_suffix("")

    base_name = str(
        base_path
    )

    exported: list[Path] = []

    if option == "1":
        exported.append(
            export_json(
                results,
                base_name,
            )
        )

    elif option == "2":
        exported.append(
            export_csv(
                results,
                base_name,
            )
        )

    elif option == "3":
        exported.append(
            export_json(
                results,
                base_name,
            )
        )

        exported.append(
            export_csv(
                results,
                base_name,
            )
        )

    else:
        print(
            "\nOpción no válida. "
            "No se exportó ningún archivo.\n"
        )
        return

    print(
        "\nExportación completada:"
    )

    for path in exported:
        print(
            f"- {path}"
        )

    print()


# ============================================================================
# MENU
# ============================================================================

def print_menu():
    print(
        "\n"
        + "=" * 65
        + "\nMONGODB NEWS QUERY MENU\n"
        + "=" * 65
        + "\n1. Ver documentos"
        + "\n2. Filtrar por idioma"
        + "\n3. Filtrar por keyword / categoría"
        + "\n4. Consulta personalizada"
        + "\n5. Ver valores distintos de un campo"
        + "\n6. Contar documentos"
        + "\n7. Mostrar campos disponibles"
        + "\n8. Exportar última consulta (JSON / CSV)"
        + "\n0. Salir\n"
        + "=" * 65
    )


def main():
    load_dotenv()

    uri = os.getenv(
        "MONGODB_URI"
    )

    db_name = os.getenv(
        "MONGODB_DATABASE",
        "dragons_app",
    )

    collection_name = os.getenv(
        "MONGODB_COLLECTION",
        "news",
    )

    keyword_directory = Path(
        os.getenv(
            "KEYWORD_MAPS_DIR",
            "keyword_maps",
        )
    ).resolve()

    if not uri:
        raise RuntimeError(
            "MONGODB_URI no está configurado en .env"
        )

    print(
        "\nCargando mapas de keywords..."
    )

    keyword_maps = load_keyword_maps(
        keyword_directory
    )

    client = None
    last_results = []

    try:
        print(
            "\nConectando a MongoDB Atlas..."
        )

        client = create_client(
            uri
        )

        collection = (
            client[
                db_name
            ][
                collection_name
            ]
        )

        print(
            f"Conectado a "
            f"{db_name}.{collection_name}"
        )

        fields = discover_fields(
            collection
        )

        while True:
            print_menu()

            option = input(
                "Selecciona una opción: "
            ).strip()

            if option == "1":
                selected_fields = ask_selected_fields(
                    fields
                )

                sort_spec = ask_sort(
                    fields
                )

                limit = ask_limit()

                print(
                    f"\nTotal en colección: "
                    f"{collection.count_documents({})}"
                )

                last_results = execute_query(
                    collection,
                    {},
                    selected_fields,
                    limit,
                    sort_spec,
                    keyword_maps,
                )

                print_documents(
                    last_results
                )

            elif option == "2":
                last_results = query_by_language(
                    collection,
                    fields,
                    keyword_maps,
                )

                print_documents(
                    last_results
                )

            elif option == "3":
                last_results = search_by_real_keyword(
                    collection,
                    keyword_maps,
                    fields,
                )

                print_documents(
                    last_results
                )

            elif option == "4":
                query = ask_filters(
                    fields,
                    keyword_maps,
                )

                selected_fields = ask_selected_fields(
                    fields
                )

                sort_spec = ask_sort(
                    fields
                )

                limit = ask_limit()

                total = collection.count_documents(
                    query
                )

                print(
                    f"\nCoincidencias: "
                    f"{total}"
                )

                print(
                    "\nConsulta Mongo generada:"
                )

                print(
                    json.dumps(
                        query,
                        ensure_ascii=False,
                        indent=2,
                        default=json_default,
                    )
                )

                last_results = execute_query(
                    collection,
                    query,
                    selected_fields,
                    limit,
                    sort_spec,
                    keyword_maps,
                )

                print_documents(
                    last_results
                )

            elif option == "5":
                show_distinct_values(
                    collection,
                    fields,
                    keyword_maps,
                )

            elif option == "6":
                print(
                    f"\nTotal documentos: "
                    f"{collection.count_documents({})}\n"
                )

            elif option == "7":
                fields = discover_fields(
                    collection
                )

                show_fields(
                    fields
                )

            elif option == "8":
                export_results(
                    last_results
                )

            elif option == "0":
                print(
                    "\nSaliendo...\n"
                )
                break

            else:
                print(
                    "\nOpción no válida.\n"
                )

    except PyMongoError as exc:
        print(
            f"\nMongoDB error: "
            f"{exc}\n"
        )
        raise

    except KeyboardInterrupt:
        print(
            "\nPrograma detenido.\n"
        )

    finally:
        if client is not None:
            client.close()


if __name__ == "__main__":
    main()

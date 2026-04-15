import re
from contextlib import suppress

from django.db import connection
from django.utils.text import slugify

SCHEMA_ALLOWED_PATTERN = re.compile(r"^[a-z_][a-z0-9_]{0,62}$")


def normalize_schema_name(raw_value: str) -> str:
    """Normalize an arbitrary tenant label into a valid PostgreSQL schema name."""
    candidate = slugify(raw_value or "", allow_unicode=False).replace("-", "_")
    candidate = re.sub(r"[^a-z0-9_]", "", candidate)

    if not candidate:
        candidate = "tenant"

    if candidate[0].isdigit():
        candidate = f"t_{candidate}"

    return candidate[:63]


def is_valid_schema_name(schema_name: str) -> bool:
    return bool(SCHEMA_ALLOWED_PATTERN.match(schema_name or ""))


def ensure_schema_exists(schema_name: str) -> None:
    if not is_valid_schema_name(schema_name):
        raise ValueError(f"Invalid schema name: {schema_name!r}")

    with connection.cursor() as cursor:
        cursor.execute(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"')


def set_connection_schema(schema_name: str) -> None:
    if not is_valid_schema_name(schema_name):
        raise ValueError(f"Invalid schema name: {schema_name!r}")

    with connection.cursor() as cursor:
        cursor.execute(f'SET search_path TO "{schema_name}", public')


def reset_connection_schema() -> None:
    with suppress(Exception):
        with connection.cursor() as cursor:
            cursor.execute('SET search_path TO public')

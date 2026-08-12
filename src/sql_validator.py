"""Compatibilité avec l'ancienne API du validateur.

Le code principal se trouve désormais dans src.sql.validator.
"""

from src.config import get_settings
from src.sql.validator import (
    FORBIDDEN_KEYWORDS,
    apply_safe_limit,
    has_limit,
    is_single_row_aggregation,
    validate_sql_query,
)


DEFAULT_LIMIT = get_settings().sql_row_limit


def normalize_sql(sql_query: str) -> str:
    return sql_query.strip()


def validate_sql(sql_query: str) -> tuple[bool, str]:
    result = validate_sql_query(sql_query)
    return result.is_valid, result.message


__all__ = [
    "DEFAULT_LIMIT",
    "FORBIDDEN_KEYWORDS",
    "apply_safe_limit",
    "has_limit",
    "is_single_row_aggregation",
    "normalize_sql",
    "validate_sql",
]

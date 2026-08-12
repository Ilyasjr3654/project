"""Compatibilité avec l'ancienne API d'accès SQLite."""

from src.sql.executor import DB_PATH, database_exists, execute_read_only, get_read_only_connection
from src.sql.schema import schema_as_text


def get_connection():
    return get_read_only_connection()


def execute_select_query(sql_query: str):
    return execute_read_only(sql_query).dataframe


def get_schema_text() -> str:
    return schema_as_text()


__all__ = [
    "DB_PATH",
    "database_exists",
    "execute_select_query",
    "get_connection",
    "get_schema_text",
]

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from time import monotonic, perf_counter

import pandas as pd

from src.config import BASE_DIR, get_settings


DB_PATH = BASE_DIR / "data" / "reporting_demo.db"


class SQLExecutionTimeout(TimeoutError):
    pass


@dataclass(frozen=True)
class QueryExecutionResult:
    dataframe: pd.DataFrame
    duration_ms: float


def database_exists(db_path: Path = DB_PATH) -> bool:
    return db_path.exists()


def get_read_only_connection(db_path: Path = DB_PATH) -> sqlite3.Connection:
    if not db_path.exists():
        raise FileNotFoundError(f"Base SQLite introuvable : {db_path}")
    database_uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(database_uri, uri=True, check_same_thread=False)
    connection.execute("PRAGMA query_only = ON")
    return connection


def execute_read_only(
    sql: str,
    timeout_seconds: float | None = None,
    db_path: Path = DB_PATH,
) -> QueryExecutionResult:
    timeout = timeout_seconds or get_settings().sql_timeout_seconds
    deadline = monotonic() + timeout
    started_at = perf_counter()

    with get_read_only_connection(db_path) as connection:
        connection.set_progress_handler(lambda: int(monotonic() > deadline), 1_000)
        try:
            dataframe = pd.read_sql_query(sql, connection)
        except Exception as exc:
            if "interrupted" in str(exc).lower():
                raise SQLExecutionTimeout(
                    f"La requête a dépassé le timeout de {timeout:.1f} seconde(s)."
                ) from exc
            raise
        finally:
            connection.set_progress_handler(None, 0)

    return QueryExecutionResult(
        dataframe=dataframe,
        duration_ms=(perf_counter() - started_at) * 1000,
    )

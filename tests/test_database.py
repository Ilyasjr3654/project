from database.create_database import main
from src.db import DB_PATH, database_exists, execute_select_query, get_connection
import pytest
import sqlite3


def test_database_creation_creates_sqlite_file():
    main()

    assert database_exists() is True
    assert DB_PATH.exists()


def test_execute_simple_select_query():
    main()

    df = execute_select_query("SELECT COUNT(*) AS total_clients FROM clients;")

    assert df.iloc[0]["total_clients"] == 10


def test_connection_is_read_only():
    main()

    with get_connection() as connection:
        with pytest.raises(sqlite3.OperationalError):
            connection.execute(
                "INSERT INTO clients (client_id, nom_client, ville, region) "
                "VALUES (999, 'Test', 'Test', 'Test')"
            )

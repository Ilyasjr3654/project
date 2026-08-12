import pytest

from src.sql.validator import apply_safe_limit, validate_sql_query
from src.sql_validator import validate_sql


def test_accepts_single_select_query():
    result = validate_sql_query("SELECT * FROM clients LIMIT 10;")

    assert result.is_valid is True
    assert result.tables == ["clients"]


@pytest.mark.parametrize(
    "keyword",
    ["DELETE", "UPDATE", "INSERT", "DROP", "ALTER", "CREATE", "TRUNCATE"],
)
def test_blocks_dangerous_statements(keyword):
    result = validate_sql_query(f"{keyword} TABLE clients;")

    assert result.is_valid is False
    assert keyword in result.message


def test_blocks_multiple_statements():
    result = validate_sql_query("SELECT * FROM clients; SELECT * FROM produits;")

    assert result.is_valid is False
    assert "Une seule" in result.message


def test_blocks_unknown_table():
    result = validate_sql_query("SELECT * FROM secrets;")

    assert result.is_valid is False
    assert "Table non autorisée" in result.message


def test_blocks_unknown_column():
    result = validate_sql_query("SELECT mot_de_passe FROM clients;")

    assert result.is_valid is False
    assert "Colonne inconnue" in result.message


def test_blocks_system_schema():
    result = validate_sql_query("SELECT * FROM sqlite_master;")

    assert result.is_valid is False
    assert "système" in result.message


def test_accepts_cte_followed_by_select():
    result = validate_sql_query(
        """
        WITH ventes AS (
            SELECT commande_id, SUM(quantite * prix_unitaire) AS ca
            FROM lignes_commandes
            GROUP BY commande_id
        )
        SELECT c.commande_id, v.ca
        FROM commandes AS c
        JOIN ventes AS v ON c.commande_id = v.commande_id;
        """
    )

    assert result.is_valid is True
    assert "WITH ventes" in result.sql


def test_accepts_columns_exposed_by_cte_select_star():
    result = validate_sql_query(
        "WITH liste AS (SELECT * FROM clients) SELECT liste.nom_client FROM liste;"
    )

    assert result.is_valid is True


def test_detail_query_after_aggregated_cte_receives_a_limit():
    result = validate_sql_query(
        """
        WITH ventes AS (
            SELECT commande_id, SUM(quantite) AS quantite
            FROM lignes_commandes GROUP BY commande_id
        )
        SELECT c.commande_id, v.quantite
        FROM commandes c JOIN ventes v ON c.commande_id = v.commande_id;
        """
    )

    assert result.is_valid is True
    assert result.sql.endswith("LIMIT 100;")


def test_adds_safe_limit_for_detail_query():
    sql = apply_safe_limit("SELECT client_id, nom_client FROM clients;")

    assert sql.endswith("LIMIT 100;")


def test_does_not_add_limit_for_aggregation():
    sql = apply_safe_limit(
        "SELECT region, COUNT(*) AS total FROM clients GROUP BY region;"
    )

    assert "LIMIT" not in sql


def test_legacy_validator_api_is_preserved():
    is_valid, message = validate_sql("SELECT COUNT(*) AS total FROM clients;")

    assert is_valid is True
    assert "validée" in message

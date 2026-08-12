from src.sql_validator import validate_sql
from src.text_to_sql_simple import question_to_sql_simple


def test_simple_mode_generates_total_revenue_sql():
    sql, explanation = question_to_sql_simple("Quel est le chiffre d'affaires total ?")

    assert sql is not None
    assert "SUM" in sql
    assert "validée" in sql
    assert "chiffre" in explanation.lower()

    is_valid, _ = validate_sql(sql)
    assert is_valid is True


def test_simple_mode_handles_accentless_question():
    sql, _ = question_to_sql_simple("Quel est le CA par region ?")

    assert sql is not None
    assert "cl.region" in sql


def test_simple_mode_returns_none_for_unknown_question():
    sql, explanation = question_to_sql_simple("Bonjour")

    assert sql is None
    assert "non reconnue" in explanation


def test_simple_mode_generates_monthly_revenue_by_region():
    sql, _ = question_to_sql_simple(
        "Montre-moi le chiffre d'affaires par mois et par région."
    )

    assert sql is not None
    assert "strftime('%Y-%m'" in sql
    assert "cl.region" in sql
    assert "GROUP BY mois, cl.region" in sql
    assert "statut = 'validée'" in sql


def test_simple_mode_generates_best_revenue_month():
    sql, _ = question_to_sql_simple(
        "Quels sont les mois avec le plus grand chiffre d'affaires ?"
    )

    assert sql is not None
    assert "GROUP BY mois" in sql
    assert "ORDER BY chiffre_affaires DESC" in sql
    assert "LIMIT 1" in sql


def test_simple_mode_generates_total_quantity_sold():
    sql, _ = question_to_sql_simple("Quelle est la quantité totale vendue ?")

    assert sql is not None
    assert "SUM(l.quantite)" in sql
    assert "statut = 'validée'" in sql

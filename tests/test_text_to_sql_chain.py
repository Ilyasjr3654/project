import pytest
from langchain_core.runnables import RunnableLambda

from src.chains.text_to_sql_chain import generate_sql
from src.rag.retriever import RAGResult
from src.sql.validator import validate_sql_query


CA_EXPRESSION = "SUM(l.quantite * l.prix_unitaire)"


TEXT_TO_SQL_CASES = [
    (
        "Quel est le chiffre d'affaires total ?",
        f"SELECT {CA_EXPRESSION} AS chiffre_affaires FROM commandes c JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée'",
        ["commandes", "lignes_commandes"],
    ),
    (
        "Quel est le chiffre d'affaires par région ?",
        f"SELECT cl.region, {CA_EXPRESSION} AS chiffre_affaires FROM clients cl JOIN commandes c ON cl.client_id = c.client_id JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée' GROUP BY cl.region",
        ["clients", "commandes", "lignes_commandes"],
    ),
    (
        "Quels sont les 5 meilleurs clients ?",
        f"SELECT cl.nom_client, {CA_EXPRESSION} AS chiffre_affaires FROM clients cl JOIN commandes c ON cl.client_id = c.client_id JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée' GROUP BY cl.client_id, cl.nom_client ORDER BY chiffre_affaires DESC LIMIT 5",
        ["clients", "commandes", "lignes_commandes"],
    ),
    (
        "Quels sont les produits les plus vendus ?",
        "SELECT p.nom_produit, SUM(l.quantite) AS quantite_totale FROM produits p JOIN lignes_commandes l ON p.produit_id = l.produit_id JOIN commandes c ON l.commande_id = c.commande_id WHERE c.statut = 'validée' GROUP BY p.produit_id, p.nom_produit ORDER BY quantite_totale DESC LIMIT 10",
        ["produits", "lignes_commandes", "commandes"],
    ),
    (
        "Quel est le CA par catégorie ?",
        f"SELECT p.categorie, {CA_EXPRESSION} AS chiffre_affaires FROM produits p JOIN lignes_commandes l ON p.produit_id = l.produit_id JOIN commandes c ON l.commande_id = c.commande_id WHERE c.statut = 'validée' GROUP BY p.categorie",
        ["produits", "lignes_commandes", "commandes"],
    ),
    (
        "Montre les ventes mensuelles.",
        f"SELECT strftime('%Y-%m', c.date_commande) AS mois, {CA_EXPRESSION} AS chiffre_affaires FROM commandes c JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée' GROUP BY mois ORDER BY mois",
        ["commandes", "lignes_commandes"],
    ),
    (
        "Compare les ventes 2025 et 2026.",
        f"SELECT strftime('%Y', c.date_commande) AS annee, {CA_EXPRESSION} AS chiffre_affaires FROM commandes c JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée' AND strftime('%Y', c.date_commande) IN ('2025', '2026') GROUP BY annee ORDER BY annee",
        ["commandes", "lignes_commandes"],
    ),
    (
        "Combien de commandes ont été annulées ?",
        "SELECT COUNT(*) AS nombre_commandes_annulees FROM commandes WHERE statut = 'annulée'",
        ["commandes"],
    ),
    (
        "Quel est le panier moyen ?",
        f"SELECT {CA_EXPRESSION} / COUNT(DISTINCT c.commande_id) AS panier_moyen FROM commandes c JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée'",
        ["commandes", "lignes_commandes"],
    ),
    (
        "Quel est le CA de Casablanca ?",
        f"SELECT cl.ville, {CA_EXPRESSION} AS chiffre_affaires FROM clients cl JOIN commandes c ON cl.client_id = c.client_id JOIN lignes_commandes l ON c.commande_id = l.commande_id WHERE c.statut = 'validée' AND cl.ville = 'Casablanca' GROUP BY cl.ville",
        ["clients", "commandes", "lignes_commandes"],
    ),
]


@pytest.mark.parametrize(("question", "sql", "tables"), TEXT_TO_SQL_CASES)
def test_text_to_sql_chain_uses_structured_output(question, sql, tables):
    prompts = []

    def fake_structured_llm(prompt_value):
        prompts.append(prompt_value.to_string())
        return {
            "status": "ready",
            "sql": sql,
            "title": "Rapport commercial",
            "interpretation": "Interprétation simulée",
            "clarification_question": None,
            "used_tables": tables,
            "applied_business_rules": ["validated_orders_default"],
            "confidence": 0.9,
        }

    rag = RAGResult(
        core_context="TABLE commandes; RÈGLE statut validée",
        retrieved_context="KPI et exemple SQL pertinent",
        final_context="Contexte final",
    )
    result = generate_sql(
        question,
        rag,
        structured_llm=RunnableLambda(fake_structured_llm),
    )

    assert result.sql == sql
    assert result.used_tables == tables
    assert validate_sql_query(result.sql).is_valid is True
    assert question in prompts[0]
    assert "RÈGLE statut validée" in prompts[0]


def test_chain_can_return_a_clarification_without_sql():
    fake_llm = RunnableLambda(
        lambda _: {
            "status": "clarification",
            "sql": None,
            "title": "Période à préciser",
            "interpretation": "La période manque.",
            "clarification_question": "Pour quelle période souhaites-tu le rapport ?",
            "used_tables": [],
            "applied_business_rules": [],
            "confidence": 0.4,
        }
    )
    result = generate_sql(
        "Montre-moi les résultats.",
        RAGResult("core", "retrieved", "final"),
        structured_llm=fake_llm,
    )

    assert result.status == "clarification"
    assert result.sql is None

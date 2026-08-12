import pandas as pd

from src.models import ResultPresentation, SQLGenerationResult
from src.rag.retriever import RAGResult
from src.services.reporting_service import run_reporting
from src.sql.executor import QueryExecutionResult


def test_reporting_service_runs_both_structured_llm_steps():
    calls = []

    def retriever(question, settings=None):
        calls.append("rag")
        return RAGResult("core", "retrieved", "final", duration_ms=1)

    def generator(question, rag_result, **kwargs):
        calls.append("sql_llm")
        return SQLGenerationResult(
            status="ready",
            sql="SELECT region, COUNT(*) AS total FROM clients GROUP BY region",
            title="Clients par région",
            interpretation="Compte les clients",
            clarification_question=None,
            used_tables=["clients"],
            applied_business_rules=[],
            confidence=0.9,
        )

    def executor(sql, timeout_seconds=None):
        calls.append("sql")
        return QueryExecutionResult(
            pd.DataFrame({"region": ["Nord", "Sud"], "total": [2, 3]}),
            2,
        )

    def interpreter(*args, **kwargs):
        calls.append("result_llm")
        return ResultPresentation(
            answer="Deux régions sont représentées.",
            presentation="bar",
            title="Clients par région",
            x_column="region",
            y_columns=["total"],
            series_column=None,
            x_label="Région",
            y_label="Clients",
            number_format="integer",
            explanation="Comparaison catégorielle",
        )

    result = run_reporting(
        "Combien de clients par région ?",
        retriever=retriever,
        sql_generator=generator,
        executor=executor,
        result_interpreter=interpreter,
    )

    assert calls == ["rag", "sql_llm", "sql", "result_llm"]
    assert result.status == "ready"
    assert result.presentation.presentation == "bar"
    assert result.row_count == 2


def test_reporting_service_stops_before_execution_when_sql_is_unsafe():
    executed = False

    def executor(sql, timeout_seconds=None):
        nonlocal executed
        executed = True
        raise AssertionError("L'exécuteur ne doit pas être appelé")

    result = run_reporting(
        "Supprime les clients",
        retriever=lambda question, settings=None: RAGResult("core", "retrieved", "final"),
        sql_generator=lambda *args, **kwargs: SQLGenerationResult(
            status="ready",
            sql="DELETE FROM clients",
            title="Requête dangereuse",
            interpretation="Test",
            clarification_question=None,
            used_tables=["clients"],
            applied_business_rules=[],
            confidence=0.1,
        ),
        executor=executor,
    )

    assert result.status == "error"
    assert executed is False
    assert result.validation.is_valid is False


def test_reporting_service_continues_with_core_context_when_rag_fails():
    calls = []

    def broken_retriever(question, settings=None):
        calls.append("rag")
        raise RuntimeError("temporary rag failure")

    def generator(question, rag_result, **kwargs):
        calls.append("sql_llm")
        assert "CONTEXTE STRUCTUREL OBLIGATOIRE" in rag_result.final_context
        assert rag_result.documents == []
        return SQLGenerationResult(
            status="ready",
            sql="SELECT categorie, COUNT(*) AS total FROM produits GROUP BY categorie",
            title="Produits par categorie",
            interpretation="Compte les produits par categorie",
            clarification_question=None,
            used_tables=["produits"],
            applied_business_rules=[],
            confidence=0.8,
        )

    def executor(sql, timeout_seconds=None):
        calls.append("sql")
        return QueryExecutionResult(
            pd.DataFrame({"categorie": ["Accessoires"], "total": [3]}),
            1,
        )

    def interpreter(*args, **kwargs):
        calls.append("result_llm")
        return ResultPresentation(
            answer="Accessoires contient le plus de produits.",
            presentation="bar",
            title="Produits par categorie",
            x_column="categorie",
            y_columns=["total"],
            series_column=None,
            x_label="Categorie",
            y_label="Produits",
            number_format="integer",
            explanation="Comparaison par categorie",
        )

    result = run_reporting(
        "Quelle est la categorie qui contient le plus de produits ?",
        retriever=broken_retriever,
        sql_generator=generator,
        executor=executor,
        result_interpreter=interpreter,
    )

    assert calls == ["rag", "sql_llm", "sql", "result_llm"]
    assert result.status == "ready"
    assert result.rag is not None
    assert result.rag.documents == []
    assert "temporary rag failure" in result.errors


def test_reporting_service_uses_simple_fallback_when_structured_llm_fails():
    def broken_generator(*args, **kwargs):
        raise RuntimeError("invalid structured output")

    def executor(sql, timeout_seconds=None):
        assert "GROUP BY cl.ville" in sql
        return QueryExecutionResult(
            pd.DataFrame({"ville": ["Casablanca"], "chiffre_affaires": [603587.85]}),
            1,
        )

    def interpreter(*args, **kwargs):
        return ResultPresentation(
            answer="Casablanca genere le plus de ventes.",
            presentation="bar",
            title="Ventes par ville",
            x_column="ville",
            y_columns=["chiffre_affaires"],
            series_column=None,
            x_label="Ville",
            y_label="Chiffre d'affaires",
            number_format="currency",
            explanation="Fallback metier",
        )

    result = run_reporting(
        "Quelle ville genere le plus de ventes ?",
        retriever=lambda question, settings=None: RAGResult("core", "retrieved", "final"),
        sql_generator=broken_generator,
        executor=executor,
        result_interpreter=interpreter,
    )

    assert result.status == "ready"
    assert result.sql_generation.title == "Analyse automatique"
    assert "invalid structured output" in result.errors


def test_reporting_service_fallback_covers_dashboard_questions():
    questions = [
        "Montre-moi le chiffre d'affaires par mois et par région.",
        "Quels sont les mois avec le plus grand chiffre d'affaires ?",
        "Quelle est la quantité totale vendue ?",
    ]

    def broken_generator(*args, **kwargs):
        raise RuntimeError("invalid structured output")

    def executor(sql, timeout_seconds=None):
        assert "statut = 'validée'" in sql
        return QueryExecutionResult(pd.DataFrame({"valeur": [1]}), 1)

    def interpreter(*args, **kwargs):
        return ResultPresentation(
            answer="Résultat disponible.",
            presentation="table",
            title="Analyse automatique",
            x_column=None,
            y_columns=[],
            series_column=None,
            x_label=None,
            y_label=None,
            number_format="none",
            explanation="Fallback métier",
        )

    for question in questions:
        result = run_reporting(
            question,
            retriever=lambda question, settings=None: RAGResult(
                "core", "retrieved", "final"
            ),
            sql_generator=broken_generator,
            executor=executor,
            result_interpreter=interpreter,
        )

        assert result.status == "ready"
        assert result.sql_generation.title == "Analyse automatique"

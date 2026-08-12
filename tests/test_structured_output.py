import pytest
from pydantic import ValidationError

from src.models import ResultPresentation, SQLGenerationResult


def test_ready_status_requires_sql():
    with pytest.raises(ValidationError):
        SQLGenerationResult(
            status="ready",
            sql=None,
            title="Test",
            interpretation="Test",
            clarification_question=None,
            used_tables=[],
            applied_business_rules=[],
            confidence=0.5,
        )


def test_clarification_requires_a_question():
    with pytest.raises(ValidationError):
        SQLGenerationResult(
            status="clarification",
            sql=None,
            title="Clarification",
            interpretation="Question ambiguë",
            clarification_question=None,
            used_tables=[],
            applied_business_rules=[],
            confidence=0.5,
        )


def test_result_presentation_accepts_expected_registry_values():
    presentation = ResultPresentation(
        answer="Le résultat est disponible.",
        presentation="line",
        title="Évolution",
        x_column="mois",
        y_columns=["chiffre_affaires"],
        series_column=None,
        x_label="Mois",
        y_label="Chiffre d'affaires",
        number_format="currency",
        explanation="Série temporelle",
    )

    assert presentation.presentation == "line"

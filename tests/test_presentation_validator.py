import pandas as pd

from src.models import ResultPresentation
from src.presentation.validator import validate_presentation


def _presentation(kind, x_column=None, y_columns=None):
    return ResultPresentation(
        answer="Résultat synthétique.",
        presentation=kind,
        title="Rapport",
        x_column=x_column,
        y_columns=y_columns or [],
        series_column=None,
        x_label=None,
        y_label=None,
        number_format="decimal",
        explanation="Choix simulé",
    )


def test_single_value_can_be_rendered_as_kpi():
    dataframe = pd.DataFrame({"chiffre_affaires": [1250.5]})

    result = validate_presentation(
        _presentation("kpi", y_columns=["chiffre_affaires"]),
        dataframe,
    )

    assert result.is_valid is True
    assert result.presentation.presentation == "kpi"


def test_temporal_data_can_be_rendered_as_line():
    dataframe = pd.DataFrame(
        {"mois": ["2025-01", "2025-02"], "chiffre_affaires": [100.0, 150.0]}
    )

    result = validate_presentation(
        _presentation("line", "mois", ["chiffre_affaires"]),
        dataframe,
    )

    assert result.is_valid is True


def test_categories_can_be_rendered_as_bar():
    dataframe = pd.DataFrame({"region": ["Nord", "Sud"], "total": [3, 5]})

    result = validate_presentation(
        _presentation("bar", "region", ["total"]),
        dataframe,
    )

    assert result.is_valid is True


def test_detailed_result_remains_a_table():
    dataframe = pd.DataFrame({"client_id": [1, 2], "nom_client": ["A", "B"]})

    result = validate_presentation(_presentation("table"), dataframe)

    assert result.is_valid is True
    assert result.presentation.presentation == "table"


def test_missing_graph_column_falls_back_to_table():
    dataframe = pd.DataFrame({"region": ["Nord"], "total": [3]})

    result = validate_presentation(
        _presentation("bar", "ville_absente", ["total"]),
        dataframe,
    )

    assert result.is_valid is False
    assert result.presentation.presentation == "table"
    assert result.warnings

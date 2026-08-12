from dataclasses import dataclass, field
from typing import Callable

import pandas as pd

from src.models.result_presentation import ResultPresentation


@dataclass(frozen=True)
class PresentationValidationResult:
    presentation: ResultPresentation
    is_valid: bool
    warnings: list[str] = field(default_factory=list)


def _success(specification: ResultPresentation, _: pd.DataFrame):
    return PresentationValidationResult(specification, True)


def _fallback(
    specification: ResultPresentation,
    warnings: list[str],
) -> PresentationValidationResult:
    safe_specification = specification.model_copy(
        update={
            "presentation": "table",
            "x_column": None,
            "y_columns": [],
            "series_column": None,
            "explanation": (
                f"{specification.explanation} Affichage tableau appliqué après validation technique."
            ).strip(),
        }
    )
    return PresentationValidationResult(safe_specification, False, warnings)


def _validate_chart(
    specification: ResultPresentation,
    dataframe: pd.DataFrame,
) -> PresentationValidationResult:
    columns = set(map(str, dataframe.columns))
    warnings: list[str] = []

    if not specification.x_column or specification.x_column not in columns:
        warnings.append("La colonne X demandée est absente du résultat.")
    missing_y = [column for column in specification.y_columns if column not in columns]
    if not specification.y_columns or missing_y:
        warnings.append(
            "Une ou plusieurs colonnes Y demandées sont absentes du résultat."
        )
    invalid_numeric = [
        column
        for column in specification.y_columns
        if column in columns and not pd.api.types.is_numeric_dtype(dataframe[column])
    ]
    if invalid_numeric:
        warnings.append(
            "Les colonnes Y suivantes ne sont pas numériques : "
            + ", ".join(invalid_numeric)
            + "."
        )
    if specification.series_column and specification.series_column not in columns:
        warnings.append("La colonne de série demandée est absente du résultat.")

    return _fallback(specification, warnings) if warnings else _success(specification, dataframe)


def _validate_pie(
    specification: ResultPresentation,
    dataframe: pd.DataFrame,
) -> PresentationValidationResult:
    chart_result = _validate_chart(specification, dataframe)
    warnings = list(chart_result.warnings)
    if len(specification.y_columns) != 1:
        warnings.append("Un graphique circulaire doit utiliser une seule colonne numérique.")
    return _fallback(specification, warnings) if warnings else chart_result


def _validate_kpi(
    specification: ResultPresentation,
    dataframe: pd.DataFrame,
) -> PresentationValidationResult:
    warnings: list[str] = []
    if len(dataframe) != 1:
        warnings.append("Un KPI doit correspondre à une seule ligne de résultat.")
    if len(specification.y_columns) != 1:
        warnings.append("Un KPI doit désigner exactement une colonne de valeur.")
    elif specification.y_columns[0] not in dataframe.columns:
        warnings.append("La colonne du KPI est absente du résultat.")
    elif not pd.api.types.is_numeric_dtype(dataframe[specification.y_columns[0]]):
        warnings.append("La valeur du KPI n'est pas numérique.")
    return _fallback(specification, warnings) if warnings else _success(specification, dataframe)


PRESENTATION_VALIDATORS: dict[
    str,
    Callable[[ResultPresentation, pd.DataFrame], PresentationValidationResult],
] = {
    "text": _success,
    "kpi": _validate_kpi,
    "table": _success,
    "bar": _validate_chart,
    "line": _validate_chart,
    "pie": _validate_pie,
}


def validate_presentation(
    specification: ResultPresentation,
    dataframe: pd.DataFrame,
) -> PresentationValidationResult:
    validator = PRESENTATION_VALIDATORS.get(specification.presentation, _success)
    return validator(specification, dataframe)

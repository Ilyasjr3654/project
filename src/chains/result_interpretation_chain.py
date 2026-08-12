import json
from typing import Any

import pandas as pd

from src.config import Settings, get_settings
from src.llm_provider import create_structured_chat_model
from src.models.result_presentation import ResultPresentation
from src.prompts.result_interpretation import RESULT_INTERPRETATION_PROMPT


def create_structured_presentation_llm(settings: Settings | None = None):
    current_settings = settings or get_settings()
    return create_structured_chat_model(ResultPresentation, current_settings)


def _columns_and_types(dataframe: pd.DataFrame) -> str:
    return "\n".join(
        f"- {column}: {dataframe[column].dtype}" for column in dataframe.columns
    )


def _sample_as_json(dataframe: pd.DataFrame, row_limit: int = 10) -> str:
    return dataframe.head(row_limit).to_json(
        orient="records",
        force_ascii=False,
        date_format="iso",
    )


def _numeric_statistics(dataframe: pd.DataFrame) -> str:
    statistics: dict[str, dict[str, Any]] = {}
    for column in dataframe.select_dtypes(include="number").columns:
        series = dataframe[column].dropna()
        if series.empty:
            continue
        statistics[str(column)] = {
            "count": int(series.count()),
            "min": float(series.min()),
            "max": float(series.max()),
            "mean": float(series.mean()),
            "sum": float(series.sum()),
        }
    return json.dumps(statistics, ensure_ascii=False)


def interpret_results(
    question: str,
    title: str,
    initial_interpretation: str,
    dataframe: pd.DataFrame,
    settings: Settings | None = None,
    structured_llm=None,
) -> ResultPresentation:
    current_settings = settings or get_settings()
    runnable = structured_llm or create_structured_presentation_llm(current_settings)
    chain = RESULT_INTERPRETATION_PROMPT | runnable
    result = chain.invoke(
        {
            "question": question,
            "title": title,
            "initial_interpretation": initial_interpretation,
            "columns_and_types": _columns_and_types(dataframe),
            "row_count": len(dataframe),
            "sample": _sample_as_json(dataframe),
            "statistics": _numeric_statistics(dataframe),
        }
    )
    return (
        result
        if isinstance(result, ResultPresentation)
        else ResultPresentation.model_validate(result)
    )

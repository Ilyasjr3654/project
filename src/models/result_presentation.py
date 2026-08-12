from typing import Literal

from pydantic import BaseModel


class ResultPresentation(BaseModel):
    """Restitution structurée choisie par le second appel LLM."""

    answer: str
    presentation: Literal["text", "kpi", "table", "bar", "line", "pie"]
    title: str
    x_column: str | None
    y_columns: list[str]
    series_column: str | None
    x_label: str | None
    y_label: str | None
    number_format: Literal[
        "integer",
        "decimal",
        "currency",
        "percentage",
        "none",
    ]
    explanation: str

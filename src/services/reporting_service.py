from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any, Literal

import pandas as pd

from src.chains.result_interpretation_chain import interpret_results
from src.chains.text_to_sql_chain import build_conversation_context, generate_sql
from src.config import Settings, get_settings
from src.models.result_presentation import ResultPresentation
from src.models.sql_generation import SQLGenerationResult
from src.presentation.validator import PresentationValidationResult, validate_presentation
from src.rag.retriever import (
    RAGResult,
    build_core_only_result,
    retrieve_knowledge,
)
from src.sql.executor import QueryExecutionResult, execute_read_only
from src.sql.validator import SQLValidationResult, validate_sql_query
from src.text_to_sql_simple import question_to_sql_simple


@dataclass
class ReportingResult:
    question: str
    status: Literal["ready", "clarification", "out_of_scope", "error"]
    title: str
    answer: str
    sql_generation: SQLGenerationResult | None = None
    validation: SQLValidationResult | None = None
    presentation: ResultPresentation | None = None
    presentation_validation: PresentationValidationResult | None = None
    dataframe: pd.DataFrame | None = None
    rag: RAGResult | None = None
    generation_ms: float = 0.0
    sql_ms: float = 0.0
    interpretation_ms: float = 0.0
    errors: list[str] = field(default_factory=list)

    @property
    def row_count(self) -> int:
        return 0 if self.dataframe is None else len(self.dataframe)

    @property
    def sql(self) -> str | None:
        if self.validation and self.validation.sql:
            return self.validation.sql
        return self.sql_generation.sql if self.sql_generation else None


def _safe_error(exc: Exception, settings: Settings) -> str:
    message = str(exc) or exc.__class__.__name__
    api_key = settings.api_key_value()
    return message.replace(api_key, "***") if api_key else message


def _fallback_presentation(
    title: str,
    dataframe: pd.DataFrame,
    reason: str,
) -> ResultPresentation:
    return ResultPresentation(
        answer=f"La requête a retourné {len(dataframe)} ligne(s).",
        presentation="table",
        title=title,
        x_column=None,
        y_columns=[],
        series_column=None,
        x_label=None,
        y_label=None,
        number_format="none",
        explanation=f"Tableau de secours : {reason}",
    )


def run_reporting(
    question: str,
    history: Sequence[Mapping[str, Any]] | None = None,
    settings: Settings | None = None,
    retriever: Callable[..., RAGResult] = retrieve_knowledge,
    sql_generator: Callable[..., SQLGenerationResult] = generate_sql,
    executor: Callable[..., QueryExecutionResult] = execute_read_only,
    result_interpreter: Callable[..., ResultPresentation] = interpret_results,
) -> ReportingResult:
    current_settings = settings or get_settings()
    rag_result: RAGResult | None = None

    try:
        rag_result = retriever(question, settings=current_settings)
    except Exception as exc:
        message = _safe_error(exc, current_settings)
        rag_result = build_core_only_result(
            reason=(
                "Contexte enrichi indisponible. Analyse poursuivie avec le "
                "referentiel metier local."
            )
        )
        rag_warning = message
    else:
        rag_warning = ""

    conversation_context = build_conversation_context(history)
    generation_started = perf_counter()
    generation_errors: list[str] = []
    try:
        sql_generation = sql_generator(
            question,
            rag_result,
            conversation_context=conversation_context,
            settings=current_settings,
        )
    except Exception as exc:
        message = _safe_error(exc, current_settings)
        fallback_sql, fallback_explanation = question_to_sql_simple(question)
        if fallback_sql is None:
            return ReportingResult(
                question,
                "error",
                "Génération SQL impossible",
                "Le modèle n'a pas pu produire une décision structurée.",
                rag=rag_result,
                generation_ms=(perf_counter() - generation_started) * 1000,
                errors=[message],
            )
        generation_errors.append(message)
        applied_rules = []
        if "statut = 'valid" in fallback_sql:
            applied_rules.append("validated_orders_default")
        sql_generation = SQLGenerationResult(
            status="ready",
            sql=fallback_sql,
            title="Analyse automatique",
            interpretation=fallback_explanation,
            clarification_question=None,
            used_tables=[],
            applied_business_rules=applied_rules,
            confidence=0.65,
        )
    generation_ms = (perf_counter() - generation_started) * 1000

    if sql_generation.status == "clarification":
        return ReportingResult(
            question,
            "clarification",
            sql_generation.title,
            sql_generation.clarification_question or sql_generation.interpretation,
            sql_generation=sql_generation,
            rag=rag_result,
            generation_ms=generation_ms,
        )
    if sql_generation.status == "out_of_scope":
        return ReportingResult(
            question,
            "out_of_scope",
            sql_generation.title,
            sql_generation.interpretation,
            sql_generation=sql_generation,
            rag=rag_result,
            generation_ms=generation_ms,
        )

    validation = validate_sql_query(
        sql_generation.sql or "",
        dialect=current_settings.sql_dialect,
        row_limit=current_settings.sql_row_limit,
    )
    if not validation.is_valid or not validation.sql:
        return ReportingResult(
            question,
            "error",
            sql_generation.title,
            "La requête générée a été bloquée par le validateur SQL.",
            sql_generation=sql_generation,
            validation=validation,
            rag=rag_result,
            generation_ms=generation_ms,
            errors=generation_errors + validation.errors,
        )

    try:
        execution = executor(
            validation.sql,
            timeout_seconds=current_settings.sql_timeout_seconds,
        )
    except Exception as exc:
        message = _safe_error(exc, current_settings)
        return ReportingResult(
            question,
            "error",
            sql_generation.title,
            "La requête validée n'a pas pu être exécutée.",
            sql_generation=sql_generation,
            validation=validation,
            rag=rag_result,
            generation_ms=generation_ms,
            errors=generation_errors + [message],
        )

    interpretation_started = perf_counter()
    interpretation_errors: list[str] = []
    try:
        presentation = result_interpreter(
            question,
            sql_generation.title,
            sql_generation.interpretation,
            execution.dataframe,
            settings=current_settings,
        )
    except Exception as exc:
        interpretation_errors.append(_safe_error(exc, current_settings))
        presentation = _fallback_presentation(
            sql_generation.title,
            execution.dataframe,
            "l'interprétation LLM a échoué",
        )
    interpretation_ms = (perf_counter() - interpretation_started) * 1000

    presentation_validation = validate_presentation(presentation, execution.dataframe)
    errors = (
        ([rag_warning] if rag_warning else [])
        + generation_errors
        + interpretation_errors
        + presentation_validation.warnings
    )
    return ReportingResult(
        question,
        "ready",
        presentation_validation.presentation.title,
        presentation_validation.presentation.answer,
        sql_generation=sql_generation,
        validation=validation,
        presentation=presentation_validation.presentation,
        presentation_validation=presentation_validation,
        dataframe=execution.dataframe,
        rag=rag_result,
        generation_ms=generation_ms,
        sql_ms=execution.duration_ms,
        interpretation_ms=interpretation_ms,
        errors=errors,
    )


def run_simple_reporting(
    question: str,
    settings: Settings | None = None,
) -> ReportingResult:
    """Conserve le mode historique sans API comme solution de secours explicite."""

    current_settings = settings or get_settings()
    sql, explanation = question_to_sql_simple(question)
    if sql is None:
        return ReportingResult(question, "error", "Question non reconnue", explanation)

    validation = validate_sql_query(
        sql,
        dialect=current_settings.sql_dialect,
        row_limit=current_settings.sql_row_limit,
    )
    if not validation.is_valid or not validation.sql:
        return ReportingResult(
            question,
            "error",
            "Requête simple bloquée",
            validation.message,
            validation=validation,
            errors=validation.errors,
        )

    execution = execute_read_only(
        validation.sql,
        timeout_seconds=current_settings.sql_timeout_seconds,
    )
    sql_generation = SQLGenerationResult(
        status="ready",
        sql=sql,
        title=explanation,
        interpretation=explanation,
        clarification_question=None,
        used_tables=validation.tables,
        applied_business_rules=["Règles fixes du mode simple"],
        confidence=1.0,
    )
    presentation = _fallback_presentation(explanation, execution.dataframe, "mode simple")
    return ReportingResult(
        question,
        "ready",
        explanation,
        explanation,
        sql_generation=sql_generation,
        validation=validation,
        presentation=presentation,
        presentation_validation=validate_presentation(presentation, execution.dataframe),
        dataframe=execution.dataframe,
        sql_ms=execution.duration_ms,
    )

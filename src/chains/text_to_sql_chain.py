from collections.abc import Mapping, Sequence
from typing import Any

from src.config import Settings, get_settings
from src.llm_provider import create_structured_chat_model
from src.models.sql_generation import SQLGenerationResult
from src.prompts.text_to_sql import TEXT_TO_SQL_PROMPT
from src.rag.retriever import RAGResult


def create_structured_text_to_sql_llm(settings: Settings | None = None):
    current_settings = settings or get_settings()
    return create_structured_chat_model(SQLGenerationResult, current_settings)


def build_conversation_context(
    history: Sequence[Mapping[str, Any]] | None,
    max_turns: int = 3,
) -> str:
    """Conserve quelques decisions precedentes utiles aux references courtes."""

    if not history:
        return "Aucun echange precedent utile."

    selected_turns = list(history)[-max_turns:]
    summaries: list[str] = []
    for index, turn in enumerate(selected_turns, start=1):
        tables = turn.get("used_tables") or []
        summaries.append(
            "\n".join(
                [
                    f"Echange {index}",
                    f"Question: {turn.get('question', '')}",
                    f"Titre retenu: {turn.get('title', '')}",
                    f"Tables utilisees: {', '.join(tables)}",
                    f"Reponse synthetique: {turn.get('answer', '')}",
                ]
            )
        )
    return "\n\n".join(summaries)


def generate_sql(
    question: str,
    rag_result: RAGResult,
    conversation_context: str = "Aucun echange precedent utile.",
    settings: Settings | None = None,
    structured_llm=None,
) -> SQLGenerationResult:
    current_settings = settings or get_settings()
    runnable = structured_llm or create_structured_text_to_sql_llm(current_settings)
    chain = TEXT_TO_SQL_PROMPT | runnable
    result = chain.invoke(
        {
            "question": question,
            "sql_dialect": current_settings.sql_dialect,
            "core_context": rag_result.core_context,
            "retrieved_context": rag_result.retrieved_context,
            "conversation_context": conversation_context,
        }
    )
    return (
        result
        if isinstance(result, SQLGenerationResult)
        else SQLGenerationResult.model_validate(result)
    )

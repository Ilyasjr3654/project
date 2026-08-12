"""API de compatibilite pour la generation Text-to-SQL LangChain."""

from collections.abc import Mapping, Sequence
from typing import Any

from src.chains.text_to_sql_chain import build_conversation_context, generate_sql
from src.config import get_settings
from src.rag.retriever import retrieve_knowledge


def clean_sql_output(raw_output: str) -> str:
    """La sortie structuree rend inutile l'extraction SQL par regex."""

    return raw_output.strip()


def question_to_sql_langchain(
    question: str,
    history: Sequence[Mapping[str, Any]] | None = None,
) -> tuple[str | None, str, str]:
    settings = get_settings()
    if settings.llm_provider == "openai" and not settings.has_openai_key:
        return (
            None,
            "Cle OPENAI_API_KEY absente. Ajoute-la dans .env ou utilise LLM_PROVIDER=ollama.",
            "",
        )

    try:
        rag_result = retrieve_knowledge(question, settings=settings)
        result = generate_sql(
            question,
            rag_result,
            conversation_context=build_conversation_context(history),
            settings=settings,
        )
    except Exception as exc:
        return None, f"Erreur pendant la generation LangChain : {exc}", ""

    explanation = result.interpretation
    if result.status == "clarification":
        explanation = result.clarification_question or result.interpretation
    return result.sql, explanation, rag_result.final_context

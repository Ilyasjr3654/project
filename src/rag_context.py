"""API de compatibilité vers le retriever Chroma structuré."""

from src.rag.retriever import retrieve_knowledge


def retrieve_context(question: str, top_k: int | None = None) -> str:
    # RAG_TOP_K reste centralisé dans Settings; l'argument est conservé pour compatibilité.
    return retrieve_knowledge(question).final_context


__all__ = ["retrieve_context"]

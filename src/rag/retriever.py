from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.rag.document_builder import build_core_context, format_document
from src.rag.vector_store import collection_count, get_vector_store


class KnowledgeBaseNotIndexedError(RuntimeError):
    pass


@dataclass(frozen=True)
class RetrievedDocument:
    content: str
    metadata: dict[str, Any]
    score: float | None = None


@dataclass(frozen=True)
class RAGResult:
    core_context: str
    retrieved_context: str
    final_context: str
    documents: list[RetrievedDocument] = field(default_factory=list)
    duration_ms: float = 0.0


def _safe_score(score: float | None) -> float | None:
    if score is None:
        return None
    return max(0.0, min(1.0, float(score)))


def _search(vector_store, question: str, k: int, metadata_filter=None):
    kwargs = {"k": k}
    if metadata_filter:
        kwargs["filter"] = metadata_filter
    return vector_store.similarity_search_with_relevance_scores(question, **kwargs)


def _deduplicate(
    groups: list[list[tuple[Document, float]]],
) -> list[tuple[Document, float]]:
    selected: list[tuple[Document, float]] = []
    seen: set[str] = set()
    for group in groups:
        for document, score in group:
            document_id = str(document.metadata.get("document_id", document.page_content))
            if document_id not in seen:
                selected.append((document, score))
                seen.add(document_id)
    return selected


def build_core_only_result(
    started_at: float | None = None,
    reason: str = "Aucun document similaire n'a pu etre recupere.",
) -> RAGResult:
    core_context = build_core_context()
    duration_ms = 0.0 if started_at is None else (perf_counter() - started_at) * 1000
    return RAGResult(
        core_context=core_context,
        retrieved_context=reason,
        final_context=(
            f"CONTEXTE STRUCTUREL OBLIGATOIRE\n{core_context}\n\n"
            "CONTEXTE RAG PAR SIMILARITE\n"
            f"{reason}"
        ),
        documents=[],
        duration_ms=duration_ms,
    )


def retrieve_knowledge(
    question: str,
    settings: Settings | None = None,
    vector_store=None,
) -> RAGResult:
    """Combine le contexte structurel, la similarite generale et les exemples SQL."""

    started_at = perf_counter()
    current_settings = settings or get_settings()
    try:
        store = vector_store or get_vector_store(current_settings)
        if collection_count(store) == 0:
            return build_core_only_result(
                started_at,
                "Index Chroma vide. Analyse poursuivie avec le contexte structurel.",
            )
        general_results = _search(store, question, current_settings.rag_top_k)
        example_results = _search(
            store,
            question,
            current_settings.rag_example_k,
            metadata_filter={"type": "sql_example"},
        )
    except Exception:
        return build_core_only_result(started_at)

    selected = _deduplicate([general_results, example_results])

    prompt_parts: list[str] = []
    retrieved_documents: list[RetrievedDocument] = []
    for document, raw_score in selected:
        score = _safe_score(raw_score)
        prompt_parts.append(format_document(document, score))
        retrieved_documents.append(
            RetrievedDocument(
                content=document.page_content,
                metadata=dict(document.metadata),
                score=score,
            )
        )

    core_context = build_core_context()
    retrieved_context = "\n\n---\n\n".join(prompt_parts)
    final_context = (
        f"CONTEXTE STRUCTUREL OBLIGATOIRE\n{core_context}\n\n"
        f"CONTEXTE RECUPERE PAR SIMILARITE\n{retrieved_context}"
    )
    return RAGResult(
        core_context=core_context,
        retrieved_context=retrieved_context,
        final_context=final_context,
        documents=retrieved_documents,
        duration_ms=(perf_counter() - started_at) * 1000,
    )

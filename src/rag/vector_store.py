from collections.abc import Iterable
from hashlib import sha1
import re

from langchain_core.documents import Document

from src.config import Settings, get_settings
from src.llm_provider import MissingModelProviderConfigError, create_embeddings


COLLECTION_PREFIX = "reporting_knowledge"


class MissingOpenAIKeyError(RuntimeError):
    """Nom conserve pour compatibilite avec l'ancien code et les tests."""


MissingEmbeddingProviderConfigError = MissingModelProviderConfigError


def _safe_collection_name(settings: Settings) -> str:
    provider_model = f"{settings.llm_provider}_{settings.active_embedding_model}"
    normalized = re.sub(r"[^a-zA-Z0-9_-]+", "_", provider_model).strip("_")
    digest = sha1(provider_model.encode("utf-8")).hexdigest()[:8]
    return f"{COLLECTION_PREFIX}_{normalized[:24]}_{digest}"


def get_embeddings(settings: Settings | None = None):
    current_settings = settings or get_settings()
    try:
        return create_embeddings(current_settings)
    except MissingModelProviderConfigError as exc:
        raise MissingOpenAIKeyError(str(exc)) from exc


def get_vector_store(settings: Settings | None = None, embedding_function=None):
    from langchain_chroma import Chroma

    current_settings = settings or get_settings()
    current_settings.chroma_path.mkdir(parents=True, exist_ok=True)
    return Chroma(
        collection_name=_safe_collection_name(current_settings),
        embedding_function=embedding_function or get_embeddings(current_settings),
        persist_directory=str(current_settings.chroma_path),
        collection_metadata={"hnsw:space": "cosine"},
    )


def collection_count(vector_store) -> int:
    return int(vector_store._collection.count())


def replace_documents(vector_store, documents: Iterable[Document]) -> int:
    """Remplace le contenu de la collection pour une indexation idempotente."""

    document_list = list(documents)
    existing = set(vector_store.get(include=[]).get("ids", []))
    ids = [str(document.metadata["document_id"]) for document in document_list]

    # Upsert avant nettoyage : un echec d'embedding conserve l'ancien index.
    vector_store.add_documents(document_list, ids=ids)
    stale_ids = sorted(existing - set(ids))
    if stale_ids:
        vector_store.delete(ids=stale_ids)
    return len(document_list)

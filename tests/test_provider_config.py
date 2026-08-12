from src.config import Settings
from src.rag.vector_store import _safe_collection_name


def test_ollama_is_default_provider():
    settings = Settings()

    assert settings.llm_provider == "ollama"
    assert settings.active_chat_model == "qwen2.5-coder:7b"
    assert settings.active_embedding_model == "nomic-embed-text"


def test_openai_provider_uses_openai_models():
    settings = Settings(
        LLM_PROVIDER="openai",
        OPENAI_MODEL="gpt-4o-mini",
        OPENAI_EMBEDDING_MODEL="text-embedding-3-small",
        OPENAI_API_KEY="test",
    )

    assert settings.active_chat_model == "gpt-4o-mini"
    assert settings.active_embedding_model == "text-embedding-3-small"


def test_chroma_collection_depends_on_embedding_provider():
    openai_settings = Settings(
        LLM_PROVIDER="openai",
        OPENAI_API_KEY="test",
        OPENAI_EMBEDDING_MODEL="text-embedding-3-small",
    )
    ollama_settings = Settings(
        LLM_PROVIDER="ollama",
        OLLAMA_EMBEDDING_MODEL="nomic-embed-text",
    )

    assert _safe_collection_name(openai_settings) != _safe_collection_name(ollama_settings)

from typing import TypeVar

from pydantic import BaseModel

from src.config import Settings, get_settings


StructuredModel = TypeVar("StructuredModel", bound=BaseModel)


class MissingModelProviderConfigError(RuntimeError):
    pass


def create_chat_model(settings: Settings | None = None):
    current_settings = settings or get_settings()

    if current_settings.llm_provider == "openai":
        from langchain_openai import ChatOpenAI

        if not current_settings.has_openai_key:
            raise MissingModelProviderConfigError(
                "OPENAI_API_KEY est absente. Ajoute une cle API ou utilise LLM_PROVIDER=ollama."
            )
        return ChatOpenAI(
            model=current_settings.openai_model,
            temperature=0,
            api_key=current_settings.api_key_value(),
        )

    from langchain_ollama import ChatOllama

    return ChatOllama(
        model=current_settings.ollama_chat_model,
        base_url=current_settings.ollama_base_url,
        temperature=0,
        validate_model_on_init=True,
    )


def create_structured_chat_model(
    schema: type[StructuredModel],
    settings: Settings | None = None,
):
    llm = create_chat_model(settings)
    return llm.with_structured_output(schema, method="json_schema")


def create_embeddings(settings: Settings | None = None):
    current_settings = settings or get_settings()

    if current_settings.llm_provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not current_settings.has_openai_key:
            raise MissingModelProviderConfigError(
                "OPENAI_API_KEY est absente. Ajoute une cle API ou utilise LLM_PROVIDER=ollama."
            )
        return OpenAIEmbeddings(
            model=current_settings.openai_embedding_model,
            api_key=current_settings.api_key_value(),
        )

    from langchain_ollama import OllamaEmbeddings

    return OllamaEmbeddings(
        model=current_settings.ollama_embedding_model,
        base_url=current_settings.ollama_base_url,
    )

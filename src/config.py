from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    """Configuration de l'application, chargée depuis l'environnement et .env."""

    llm_provider: Literal["openai", "ollama"] = Field(
        default="ollama",
        alias="LLM_PROVIDER",
    )
    openai_api_key: SecretStr | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", alias="OPENAI_MODEL")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small",
        alias="OPENAI_EMBEDDING_MODEL",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_BASE_URL",
    )
    ollama_chat_model: str = Field(
        default="qwen2.5-coder:7b",
        alias="OLLAMA_CHAT_MODEL",
    )
    ollama_embedding_model: str = Field(
        default="nomic-embed-text",
        alias="OLLAMA_EMBEDDING_MODEL",
    )
    chroma_directory: str = Field(default="data/chroma_db", alias="CHROMA_DIRECTORY")
    rag_top_k: int = Field(default=5, ge=1, le=20, alias="RAG_TOP_K")
    rag_example_k: int = Field(default=2, ge=1, le=10, alias="RAG_EXAMPLE_K")
    sql_dialect: Literal["sqlite"] = Field(default="sqlite", alias="SQL_DIALECT")
    sql_row_limit: int = Field(default=100, ge=1, le=10_000, alias="SQL_ROW_LIMIT")
    sql_timeout_seconds: float = Field(
        default=5.0,
        gt=0,
        le=60,
        alias="SQL_TIMEOUT_SECONDS",
    )
    default_mode: Literal["simple", "langchain"] = Field(
        default="simple",
        alias="DEFAULT_MODE",
    )

    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    @property
    def chroma_path(self) -> Path:
        path = Path(self.chroma_directory)
        return path if path.is_absolute() else BASE_DIR / path

    @property
    def has_openai_key(self) -> bool:
        return bool(self.openai_api_key and self.openai_api_key.get_secret_value().strip())

    @property
    def active_chat_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_model
        return self.ollama_chat_model

    @property
    def active_embedding_model(self) -> str:
        if self.llm_provider == "openai":
            return self.openai_embedding_model
        return self.ollama_embedding_model

    def api_key_value(self) -> str:
        return self.openai_api_key.get_secret_value() if self.openai_api_key else ""


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

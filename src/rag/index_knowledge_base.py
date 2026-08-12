from src.config import Settings, get_settings
from src.rag.document_builder import build_documents
from src.rag.vector_store import get_vector_store, replace_documents


def index_knowledge_base(
    settings: Settings | None = None,
    vector_store=None,
) -> int:
    current_settings = settings or get_settings()
    documents = build_documents()
    store = vector_store or get_vector_store(current_settings)
    return replace_documents(store, documents)


def main() -> None:
    settings = get_settings()
    try:
        count = index_knowledge_base(settings=settings)
    except Exception as exc:
        raise SystemExit(f"Indexation Chroma impossible : {exc}") from exc
    print(f"Index Chroma reconstruit : {count} documents dans {settings.chroma_path}")


if __name__ == "__main__":
    main()

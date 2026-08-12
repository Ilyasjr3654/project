from langchain_core.embeddings import Embeddings

from src.config import Settings
from src.rag.document_builder import build_documents
from src.rag.vector_store import collection_count, get_vector_store, replace_documents


class DeterministicEmbeddings(Embeddings):
    def embed_documents(self, texts):
        return [self.embed_query(text) for text in texts]

    def embed_query(self, text):
        normalized = text.lower()
        return [
            float(len(normalized)),
            float(normalized.count("a")),
            float(normalized.count("e")),
            float(normalized.count("i")),
        ]


def test_real_chroma_store_is_idempotent_without_api(tmp_path):
    settings = Settings(
        OPENAI_API_KEY="test",
        CHROMA_DIRECTORY=str(tmp_path / "chroma"),
    )
    store = get_vector_store(settings, embedding_function=DeterministicEmbeddings())
    documents = build_documents()

    replace_documents(store, documents)
    replace_documents(store, documents)

    assert collection_count(store) == len(documents)

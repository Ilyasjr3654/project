import json
from collections import Counter

from src.rag.document_builder import build_documents, get_core_documents
from src.rag.vector_store import replace_documents


class FakeVectorStore:
    def __init__(self):
        self.documents = {}

    def get(self, include=None):
        return {"ids": list(self.documents)}

    def delete(self, ids):
        for document_id in ids:
            self.documents.pop(document_id, None)

    def add_documents(self, documents, ids):
        self.documents.update(dict(zip(ids, documents)))


def test_builds_one_semantic_document_per_knowledge_item():
    documents = build_documents()
    counts = Counter(document.metadata["type"] for document in documents)

    assert len(documents) == 40
    assert counts == {
        "table": 4,
        "relationship": 3,
        "business_rule": 7,
        "kpi": 8,
        "glossary": 8,
        "sql_example": 10,
    }
    assert len(get_core_documents(documents)) == 8


def test_chroma_metadata_contains_only_scalar_values():
    for document in build_documents():
        assert all(
            isinstance(value, (str, int, float, bool))
            for value in document.metadata.values()
        )
        assert isinstance(json.loads(document.metadata["tables"]), list)


def test_index_rebuild_is_idempotent():
    store = FakeVectorStore()
    documents = build_documents()

    first_count = replace_documents(store, documents)
    second_count = replace_documents(store, documents)

    assert first_count == second_count == len(documents)
    assert len(store.documents) == len(documents)

import unicodedata

import pytest

from src.config import Settings
from src.rag.document_builder import build_documents
from src.rag.retriever import retrieve_knowledge


def _normalize(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in normalized if not unicodedata.combining(char))


class FakeCollection:
    def __init__(self, size):
        self.size = size

    def count(self):
        return self.size


class FakeSemanticStore:
    def __init__(self):
        self.documents = build_documents()
        self._collection = FakeCollection(len(self.documents))

    def similarity_search_with_relevance_scores(self, question, k, filter=None):
        normalized = _normalize(question)
        profiles = {
            "chiffre d'affaires": ("kpi", "chiffre_affaires"),
            "ventes par region": ("kpi", "chiffre_affaires_par_region"),
            "produits les plus vendus": ("kpi", "top_produits"),
            "evolution mensuelle": ("kpi", "evolution_mensuelle"),
            "commandes annulees": ("business_rule", "cancelled_orders_excluded"),
        }
        target = next(
            (value for key, value in profiles.items() if key in normalized),
            ("kpi", "chiffre_affaires"),
        )
        candidates = [
            document
            for document in self.documents
            if not filter or document.metadata["type"] == filter["type"]
        ]
        ranked = sorted(
            candidates,
            key=lambda document: (
                document.metadata["type"] == target[0]
                and document.metadata["name"] == target[1]
            ),
            reverse=True,
        )
        return [(document, 0.95 - index * 0.01) for index, document in enumerate(ranked[:k])]


class BrokenSemanticStore(FakeSemanticStore):
    def similarity_search_with_relevance_scores(self, question, k, filter=None):
        raise RuntimeError("temporary retrieval failure")


@pytest.fixture
def settings():
    return Settings(OPENAI_API_KEY="test", RAG_TOP_K=3, RAG_EXAMPLE_K=1)


@pytest.mark.parametrize(
    ("question", "expected_type", "expected_name", "expected_text"),
    [
        ("chiffre d'affaires", "kpi", "chiffre_affaires", "prix_unitaire"),
        (
            "ventes par region",
            "kpi",
            "chiffre_affaires_par_region",
            "clients.client_id = commandes.client_id",
        ),
        (
            "produits les plus vendus",
            "kpi",
            "top_produits",
            "SUM(lignes_commandes.quantite)",
        ),
        (
            "evolution mensuelle",
            "kpi",
            "evolution_mensuelle",
            "commandes.date_commande",
        ),
        (
            "commandes annulees",
            "business_rule",
            "cancelled_orders_excluded",
            "commandes annulees",
        ),
    ],
)
def test_retrieval_composes_relevant_and_core_context(
    settings,
    question,
    expected_type,
    expected_name,
    expected_text,
):
    result = retrieve_knowledge(
        question,
        settings=settings,
        vector_store=FakeSemanticStore(),
    )

    retrieved_ids = {
        (document.metadata["type"], document.metadata["name"])
        for document in result.documents
    }
    assert (expected_type, expected_name) in retrieved_ids
    assert _normalize(expected_text) in _normalize(result.final_context)
    assert "commandes.statut = 'validee'" not in result.core_context
    assert "commandes.statut = 'valid" in result.core_context


def test_retrieval_falls_back_to_core_context_when_similarity_search_fails(settings):
    result = retrieve_knowledge(
        "quel est le panier moyen",
        settings=settings,
        vector_store=BrokenSemanticStore(),
    )

    assert result.documents == []
    assert "Aucun document similaire n'a pu etre recupere." in result.retrieved_context
    assert "commandes.statut = 'valid" in result.core_context

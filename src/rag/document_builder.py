import hashlib
import json
from pathlib import Path
from typing import Any, Callable

import yaml
from langchain_core.documents import Document

from src.config import BASE_DIR


KNOWLEDGE_DIR = BASE_DIR / "knowledge"
KNOWLEDGE_FILES = {
    "table": "tables.yaml",
    "relationship": "relationships.yaml",
    "business_rule": "business_rules.yaml",
    "kpi": "kpis.yaml",
    "glossary": "glossary.yaml",
    "sql_example": "sql_examples.yaml",
}
CORE_BUSINESS_RULES = {"validated_orders_default"}


def _join_values(values: list[str]) -> str:
    return ", ".join(str(value) for value in values) if values else "Aucun"


def _format_table(item: dict[str, Any]) -> str:
    columns = "\n".join(
        f"- {column['name']} ({column['type']}): {column['description']}"
        for column in item["columns"]
    )
    return (
        f"TABLE: {item['name']}\n"
        f"Rôle: {item['role']}\n"
        f"Granularité: {item['granularity']}\n"
        f"Clé primaire: {item['primary_key']}\n"
        f"Clés étrangères: {_join_values(item.get('foreign_keys', []))}\n"
        f"Colonnes:\n{columns}\n"
        f"Exemples: {_join_values(item.get('examples', []))}"
    )


def _format_relationship(item: dict[str, Any]) -> str:
    return (
        f"RELATION: {item['left']} = {item['right']}\n"
        f"Cardinalité: {item['cardinality']}\n"
        f"Tables: {_join_values(item['tables'])}"
    )


def _format_business_rule(item: dict[str, Any]) -> str:
    return (
        f"RÈGLE MÉTIER: {item['rule']}\n"
        f"Tables: {_join_values(item['tables'])}\n"
        f"Indicateurs concernés: {_join_values(item.get('applies_to', []))}"
    )


def _format_kpi(item: dict[str, Any]) -> str:
    return (
        f"KPI: {item['label']}\n"
        f"Définition: {item['definition']}\n"
        f"Calcul: {item['calculation']}\n"
        f"Tables: {_join_values(item['tables'])}\n"
        f"Filtre par défaut: {item['default_filter']}"
    )


def _format_glossary(item: dict[str, Any]) -> str:
    return (
        f"GLOSSAIRE: {_join_values(item['terms'])}\n"
        f"Signification: {item['meaning']}\n"
        f"Tables: {_join_values(item['tables'])}"
    )


def _format_sql_example(item: dict[str, Any]) -> str:
    return (
        f"EXEMPLE TEXT-TO-SQL\n"
        f"Question: {item['question']}\n"
        f"Intention: {item['intent']}\n"
        f"Tables: {_join_values(item['tables'])}\n"
        f"SQL SQLite de référence:\n{item['sql'].strip()}"
    )


DOCUMENT_FORMATTERS: dict[str, Callable[[dict[str, Any]], str]] = {
    "table": _format_table,
    "relationship": _format_relationship,
    "business_rule": _format_business_rule,
    "kpi": _format_kpi,
    "glossary": _format_glossary,
    "sql_example": _format_sql_example,
}


def _load_yaml(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    documents = payload.get("documents", [])
    if not isinstance(documents, list):
        raise ValueError(f"Le fichier {path.name} doit contenir une liste 'documents'.")
    return documents


def _tables_for(document_type: str, item: dict[str, Any]) -> list[str]:
    if document_type == "table":
        return [item["name"]]
    return list(item.get("tables", []))


def _document_id(document_type: str, name: str, content: str) -> str:
    raw_value = f"{document_type}:{name}:{content}".encode("utf-8")
    return hashlib.sha256(raw_value).hexdigest()[:32]


def build_documents(knowledge_dir: Path = KNOWLEDGE_DIR) -> list[Document]:
    """Construit un document sémantique par table, règle, KPI ou exemple."""

    documents: list[Document] = []
    for document_type, filename in KNOWLEDGE_FILES.items():
        source_path = knowledge_dir / filename
        for item in _load_yaml(source_path):
            name = str(item["name"])
            content = DOCUMENT_FORMATTERS[document_type](item)
            tables = _tables_for(document_type, item)
            document_id = _document_id(document_type, name, content)
            documents.append(
                Document(
                    page_content=content,
                    metadata={
                        "document_id": document_id,
                        "type": document_type,
                        "name": name,
                        "tables": json.dumps(tables, ensure_ascii=False),
                        "source": filename,
                    },
                )
            )
    return documents


def get_core_documents(documents: list[Document] | None = None) -> list[Document]:
    source_documents = documents or build_documents()
    return [
        document
        for document in source_documents
        if document.metadata["type"] in {"table", "relationship"}
        or (
            document.metadata["type"] == "business_rule"
            and document.metadata["name"] in CORE_BUSINESS_RULES
        )
    ]


def format_document(document: Document, score: float | None = None) -> str:
    metadata = document.metadata
    score_text = "" if score is None else f" | score={score:.3f}"
    return (
        f"[{metadata['type']}:{metadata['name']} | source={metadata['source']}"
        f"{score_text}]\n{document.page_content}"
    )


def build_core_context(documents: list[Document] | None = None) -> str:
    return "\n\n---\n\n".join(
        format_document(document) for document in get_core_documents(documents)
    )

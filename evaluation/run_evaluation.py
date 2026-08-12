import argparse
import json
from pathlib import Path
from statistics import mean
from time import perf_counter
from typing import Any

import pandas as pd
import yaml

from src.config import BASE_DIR, get_settings
from src.services.reporting_service import run_reporting
from src.sql.executor import execute_read_only
from src.sql.validator import validate_sql_query


DATASET_PATH = BASE_DIR / "evaluation" / "evaluation_dataset.yaml"


def load_cases(path: Path = DATASET_PATH) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as stream:
        return list((yaml.safe_load(stream) or {}).get("cases", []))


def _canonical_value(value: Any) -> Any:
    if pd.isna(value):
        return None
    if isinstance(value, (float, int)):
        return round(float(value), 6)
    return str(value)


def _canonical_frame(dataframe: pd.DataFrame) -> tuple[list[str], list[str]]:
    columns = sorted(map(str, dataframe.columns))
    rows = [
        json.dumps(
            [_canonical_value(row[column]) for column in columns],
            ensure_ascii=False,
            sort_keys=True,
        )
        for _, row in dataframe[columns].iterrows()
    ]
    return columns, sorted(rows)


def results_are_equivalent(left: pd.DataFrame, right: pd.DataFrame) -> bool:
    return _canonical_frame(left) == _canonical_frame(right)


def _document_recall(result, expected_documents: list[str]) -> float:
    if not expected_documents or not result.rag:
        return 1.0 if not expected_documents else 0.0
    retrieved_names = {
        document.metadata.get("name") for document in result.rag.documents
    }
    final_context = result.rag.final_context
    found = {
        name
        for name in expected_documents
        if name in retrieved_names or f":{name} |" in final_context
    }
    return len(found) / len(expected_documents)


def _table_precision(result, expected_tables: list[str]) -> float:
    selected = set(result.sql_generation.used_tables) if result.sql_generation else set()
    expected = set(expected_tables)
    if not selected:
        return 1.0 if not expected else 0.0
    return len(selected & expected) / len(selected)


def _reference_result(case: dict[str, Any]) -> pd.DataFrame:
    validation = validate_sql_query(case["reference_sql"])
    if not validation.is_valid or not validation.sql:
        raise ValueError(f"SQL de référence invalide : {validation.message}")
    return execute_read_only(validation.sql).dataframe


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started_at = perf_counter()
    result = run_reporting(case["question"])
    elapsed_ms = (perf_counter() - started_at) * 1000

    document_recall = _document_recall(result, case.get("expected_documents", []))
    table_precision = _table_precision(result, case["expected_tables"])
    selected_tables = set(result.sql_generation.used_tables) if result.sql_generation else set()
    expected_tables = set(case["expected_tables"])
    table_match = selected_tables == expected_tables
    sql_valid = bool(result.validation and result.validation.is_valid)

    result_equivalent = False
    if result.status == "ready" and result.dataframe is not None and sql_valid:
        result_equivalent = results_are_equivalent(
            result.dataframe,
            _reference_result(case),
        )

    presentation_match = bool(
        result.presentation
        and result.presentation.presentation == case["expected_presentation"]
    )
    applied_rules = set(
        result.sql_generation.applied_business_rules if result.sql_generation else []
    )
    expected_rules = set(case.get("expected_rules", []))
    rules_match = expected_rules.issubset(applied_rules)

    return {
        "question": case["question"],
        "status": result.status,
        "document_recall": document_recall,
        "table_precision": table_precision,
        "table_match": table_match,
        "sql_valid": sql_valid,
        "result_equivalent": result_equivalent,
        "presentation_match": presentation_match,
        "rules_match": rules_match,
        "global_success": all(
            [
                document_recall == 1.0,
                table_match,
                sql_valid,
                result_equivalent,
                presentation_match,
                rules_match,
            ]
        ),
        "response_ms": elapsed_ms,
        "errors": result.errors,
    }


def summarize(results: list[dict[str, Any]]) -> dict[str, float]:
    if not results:
        return {}
    return {
        "rag_document_recall": mean(item["document_recall"] for item in results),
        "selected_table_precision": mean(item["table_precision"] for item in results),
        "valid_sql_rate": mean(float(item["sql_valid"]) for item in results),
        "result_equivalence_rate": mean(
            float(item["result_equivalent"]) for item in results
        ),
        "global_success_rate": mean(float(item["global_success"]) for item in results),
        "average_response_ms": mean(item["response_ms"] for item in results),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Évalue le pipeline RAG Text-to-SQL.")
    parser.add_argument("--limit", type=int, default=None, help="Nombre de cas à exécuter")
    args = parser.parse_args()

    settings = get_settings()
    if not settings.has_openai_key:
        raise SystemExit("OPENAI_API_KEY est requise pour l'évaluation avec API.")

    cases = load_cases()
    selected_cases = cases[: args.limit] if args.limit else cases
    results: list[dict[str, Any]] = []
    for index, case in enumerate(selected_cases, start=1):
        result = evaluate_case(case)
        results.append(result)
        verdict = "OK" if result["global_success"] else "ECHEC"
        print(f"[{index}/{len(selected_cases)}] {verdict} - {case['question']}")

    print(json.dumps(summarize(results), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

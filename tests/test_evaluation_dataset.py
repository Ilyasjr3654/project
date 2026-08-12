from evaluation.run_evaluation import load_cases
from src.sql.validator import validate_sql_query


def test_evaluation_dataset_contains_at_least_twenty_valid_references():
    cases = load_cases()

    assert len(cases) >= 20
    for case in cases:
        assert validate_sql_query(case["reference_sql"]).is_valid is True

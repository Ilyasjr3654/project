from dataclasses import dataclass, field
import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError
from sqlglot.optimizer.scope import Scope, traverse_scope

from src.config import get_settings
from src.sql.schema import ALLOWED_SCHEMA, ALLOWED_TABLES, SYSTEM_SCHEMAS


FORBIDDEN_KEYWORDS = (
    "DROP",
    "DELETE",
    "UPDATE",
    "INSERT",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "PRAGMA",
    "ATTACH",
    "DETACH",
)


@dataclass(frozen=True)
class SQLValidationResult:
    is_valid: bool
    message: str
    sql: str | None = None
    tables: list[str] = field(default_factory=list)
    columns: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def _remove_literals_and_comments(sql: str) -> str:
    without_comments = re.sub(r"--[^\n]*|/\*.*?\*/", " ", sql, flags=re.DOTALL)
    without_strings = re.sub(r"'(?:''|[^'])*'", "''", without_comments)
    return re.sub(r'"(?:""|[^"])*"', '""', without_strings)


def _forbidden_keyword(sql: str) -> str | None:
    inspectable_sql = _remove_literals_and_comments(sql)
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", inspectable_sql, flags=re.IGNORECASE):
            return keyword
    return None


def _parse_single_statement(sql: str, dialect: str) -> tuple[exp.Expression | None, str | None]:
    try:
        statements = [statement for statement in sqlglot.parse(sql, read=dialect) if statement]
    except ParseError as exc:
        return None, f"SQL invalide pour le dialecte {dialect} : {exc}."
    if len(statements) != 1:
        return None, "Une seule instruction SQL est autorisée."
    return statements[0], None


def _forbidden_expression(expression: exp.Expression) -> str | None:
    forbidden_types = tuple(
        expression_type
        for expression_type in (
            getattr(exp, "Insert", None),
            getattr(exp, "Update", None),
            getattr(exp, "Delete", None),
            getattr(exp, "Drop", None),
            getattr(exp, "Create", None),
            getattr(exp, "Alter", None),
            getattr(exp, "TruncateTable", None),
            getattr(exp, "Command", None),
        )
        if expression_type is not None
    )
    dangerous = next(expression.find_all(*forbidden_types), None)
    return dangerous.key.upper() if dangerous is not None else None


def _validate_tables(
    expression: exp.Expression,
) -> tuple[list[str], dict[str, str], list[str]]:
    errors: list[str] = []
    tables: set[str] = set()
    aliases: dict[str, str] = {}
    cte_names = {cte.alias_or_name.lower() for cte in expression.find_all(exp.CTE)}

    for table_expression in expression.find_all(exp.Table):
        table_name = table_expression.name.lower()
        database_name = (table_expression.db or "").lower()
        catalog_name = (table_expression.catalog or "").lower()
        if database_name in SYSTEM_SCHEMAS or catalog_name in SYSTEM_SCHEMAS:
            errors.append(f"Schéma système interdit : {database_name or catalog_name}.")
            continue
        if table_name in SYSTEM_SCHEMAS:
            errors.append(f"Table système interdite : {table_name}.")
            continue
        if table_name in cte_names:
            continue
        if database_name or catalog_name:
            errors.append(
                f"Les noms qualifiés par un schéma ne sont pas autorisés : {table_expression.sql()}."
            )
            continue
        if table_name not in ALLOWED_TABLES:
            errors.append(f"Table non autorisée ou inconnue : {table_name}.")
            continue
        tables.add(table_name)
        aliases[table_name] = table_name
        aliases[table_expression.alias_or_name.lower()] = table_name

    return sorted(tables), aliases, errors


def _scope_source_columns(scope: Scope) -> dict[str, set[str]]:
    source_columns: dict[str, set[str]] = {}
    for alias, (_, source) in scope.selected_sources.items():
        if isinstance(source, exp.Table):
            source_columns[alias.lower()] = set(
                ALLOWED_SCHEMA.get(source.name.lower(), {})
            )
        elif isinstance(source, Scope):
            output_columns = {
                name.lower() for name in source.expression.named_selects if name
            }
            if "*" in output_columns:
                output_columns.remove("*")
                for nested_columns in _scope_source_columns(source).values():
                    output_columns.update(nested_columns)
            source_columns[alias.lower()] = output_columns
    return source_columns


def _validate_columns(expression: exp.Expression) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    columns: set[str] = set()

    for scope in traverse_scope(expression):
        source_columns = _scope_source_columns(scope)
        selectable_aliases = {
            projection.alias.lower()
            for projection in scope.expression.expressions
            if projection.alias
        }
        for column_expression in scope.columns:
            column_name = column_expression.name.lower()
            qualifier = column_expression.table.lower()
            if column_name == "*":
                continue

            columns.add(column_expression.sql())
            if qualifier:
                available_columns = source_columns.get(qualifier)
                if available_columns is None:
                    errors.append(f"Alias de table inconnu : {qualifier}.")
                elif column_name not in available_columns:
                    errors.append(f"Colonne inconnue dans {qualifier} : {column_name}.")
                continue

            if column_name in selectable_aliases:
                continue

            matching_sources = [
                source_name
                for source_name, available_columns in source_columns.items()
                if column_name in available_columns
            ]
            if not matching_sources:
                errors.append(f"Colonne inconnue : {column_name}.")
            elif len(matching_sources) > 1:
                errors.append(
                    f"Colonne ambiguë : {column_name}. Qualifie-la avec son alias de table."
                )

    return sorted(columns), errors


def _is_single_row_aggregation(expression: exp.Expression) -> bool:
    if not isinstance(expression, exp.Select) or expression.args.get("group"):
        return False
    return any(
        projection.find(exp.AggFunc) is not None
        for projection in expression.expressions
    )


def _has_aggregation(expression: exp.Expression) -> bool:
    if not isinstance(expression, exp.Select):
        return False
    return any(
        projection.find(exp.AggFunc) is not None
        for projection in expression.expressions
    )


def has_limit(sql: str, dialect: str | None = None) -> bool:
    selected_dialect = dialect or get_settings().sql_dialect
    expression, error = _parse_single_statement(sql, selected_dialect)
    return bool(expression is not None and error is None and expression.args.get("limit"))


def is_single_row_aggregation(sql: str, dialect: str | None = None) -> bool:
    selected_dialect = dialect or get_settings().sql_dialect
    expression, error = _parse_single_statement(sql, selected_dialect)
    return bool(
        expression is not None
        and error is None
        and _is_single_row_aggregation(expression)
    )


def apply_safe_limit(
    sql: str,
    limit: int | None = None,
    dialect: str | None = None,
) -> str:
    settings = get_settings()
    selected_dialect = dialect or settings.sql_dialect
    selected_limit = limit or settings.sql_row_limit
    expression, error = _parse_single_statement(sql, selected_dialect)
    if expression is None or error:
        return sql.strip()
    if expression.args.get("limit") or _has_aggregation(expression):
        return f"{expression.sql(dialect=selected_dialect)};"
    limited_expression = expression.limit(selected_limit, copy=True)
    return f"{limited_expression.sql(dialect=selected_dialect)};"


def validate_sql_query(
    sql: str,
    dialect: str | None = None,
    row_limit: int | None = None,
) -> SQLValidationResult:
    if not sql or not sql.strip():
        return SQLValidationResult(False, "La requête SQL est vide.", errors=["SQL vide"])

    settings = get_settings()
    selected_dialect = dialect or settings.sql_dialect
    selected_limit = row_limit or settings.sql_row_limit

    keyword = _forbidden_keyword(sql)
    if keyword:
        message = f"Mot-clé SQL interdit détecté : {keyword}."
        return SQLValidationResult(False, message, errors=[message])

    expression, parse_error = _parse_single_statement(sql, selected_dialect)
    if expression is None:
        return SQLValidationResult(False, parse_error or "SQL invalide.", errors=[parse_error or "SQL invalide"])

    dangerous_expression = _forbidden_expression(expression)
    if dangerous_expression:
        message = f"Instruction SQL interdite : {dangerous_expression}."
        return SQLValidationResult(False, message, errors=[message])

    if not isinstance(expression, exp.Select):
        message = "Seules les requêtes SELECT, éventuellement précédées de WITH, sont autorisées."
        return SQLValidationResult(False, message, errors=[message])

    tables, _, table_errors = _validate_tables(expression)
    columns, column_errors = _validate_columns(expression)
    errors = table_errors + column_errors
    if errors:
        return SQLValidationResult(
            False,
            "Requête SQL refusée : " + " ".join(errors),
            tables=tables,
            columns=columns,
            errors=errors,
        )

    safe_sql = apply_safe_limit(sql, limit=selected_limit, dialect=selected_dialect)
    limit_added = safe_sql.rstrip(";") != expression.sql(dialect=selected_dialect)
    message = "Requête validée."
    if limit_added:
        message += f" LIMIT {selected_limit} ajouté par sécurité."
    return SQLValidationResult(
        True,
        message,
        sql=safe_sql,
        tables=tables,
        columns=columns,
    )

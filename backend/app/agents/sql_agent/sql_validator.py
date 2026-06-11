"""
SQL Validator.
Validates generated SQL for safety using sqlglot AST parsing.
Only SELECT statements are allowed — no DDL or DML.
"""

import logging
import sqlglot
from sqlglot import expressions as exp

logger = logging.getLogger(__name__)

# Disallowed statement types
BLOCKED_STATEMENTS = (
    exp.Create, exp.Drop, exp.Alter, exp.Insert,
    exp.Update, exp.Delete, exp.Command,
)

# Disallowed function names
BLOCKED_FUNCTIONS = {
    'system', 'shell', 'exec', 'eval', 'load_extension',
    'install', 'copy', 'export',
}


def validate_sql(sql: str) -> tuple[bool, str]:
    """
    Validate that the SQL is safe to execute.

    Returns:
        (is_valid, error_message) — if valid, error_message is empty.
    """
    if not sql or not sql.strip():
        return False, "Empty SQL query."

    sql = sql.strip().rstrip(';')

    try:
        parsed = sqlglot.parse(sql, dialect="duckdb")
    except sqlglot.errors.ParseError as e:
        return False, f"SQL parse error: {e}"

    if not parsed:
        return False, "Could not parse SQL."

    for statement in parsed:
        if statement is None:
            continue

        # Check statement type
        if isinstance(statement, BLOCKED_STATEMENTS):
            return False, f"Blocked statement type: {type(statement).__name__}. Only SELECT is allowed."

        # Must be a SELECT (or subquery/union that resolves to SELECT)
        if not isinstance(statement, (exp.Select, exp.Union, exp.Intersect, exp.Except, exp.Subquery)):
            # Check if it wraps a select
            selects = list(statement.find_all(exp.Select))
            if not selects:
                return False, f"Only SELECT queries allowed. Got: {type(statement).__name__}"

        # Check for blocked function calls
        for func in statement.find_all(exp.Anonymous):
            func_name = func.name.lower() if hasattr(func, 'name') else ""
            if func_name in BLOCKED_FUNCTIONS:
                return False, f"Blocked function: {func_name}"

        # Check for COPY / EXPORT
        sql_upper = sql.upper().strip()
        for keyword in ['COPY', 'EXPORT', 'IMPORT', 'LOAD', 'INSTALL', 'ATTACH']:
            if sql_upper.startswith(keyword):
                return False, f"Blocked operation: {keyword}"

    return True, ""

"""
Semantic dictionary.
Detects columns across tables that represent the same concept
(e.g., location, city, job_location → "location").
"""

import logging
from difflib import SequenceMatcher
from collections import defaultdict
import duckdb

logger = logging.getLogger(__name__)


# Common semantic groups and their known aliases
KNOWN_ALIASES = {
    "location": {"location", "city", "job_location", "office", "site", "branch", "region", "area"},
    "name": {"name", "full_name", "employee_name", "candidate_name", "person_name", "first_name"},
    "email": {"email", "email_address", "e_mail", "mail"},
    "phone": {"phone", "phone_number", "mobile", "contact_number", "telephone"},
    "date": {"date", "created_at", "updated_at", "timestamp", "created_date"},
    "salary": {"salary", "compensation", "pay", "wage", "ctc", "annual_salary"},
    "department": {"department", "dept", "division", "team", "unit", "group"},
    "status": {"status", "state", "current_status", "offer_status", "application_status"},
    "id": {"id", "employee_id", "candidate_id", "user_id", "record_id"},
}


def build_semantic_dictionary(
    conn: duckdb.DuckDBPyConnection,
    table_names: list[str],
) -> dict[str, list[tuple[str, str]]]:
    """
    Build equivalence classes for semantically similar columns.

    Returns:
        Dict mapping semantic group name → list of (table, column) tuples.
    """
    # Collect all columns
    all_columns: list[tuple[str, str]] = []  # (table, column)
    for tbl in table_names:
        if tbl.startswith('_'):
            continue
        try:
            cols = conn.execute(
                f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}'"
            ).fetchall()
            for (col_name,) in cols:
                all_columns.append((tbl, col_name))
        except Exception:
            continue

    # Build groups
    groups: dict[str, list[tuple[str, str]]] = defaultdict(list)

    for tbl, col in all_columns:
        col_lower = col.lower()
        matched = False

        # Check against known aliases
        for group_name, aliases in KNOWN_ALIASES.items():
            for alias in aliases:
                if col_lower == alias or alias in col_lower or col_lower in alias:
                    groups[group_name].append((tbl, col))
                    matched = True
                    break
            if matched:
                break

        # If no known alias, try to find similar columns
        if not matched:
            for group_name, members in list(groups.items()):
                for _, existing_col in members:
                    if _column_similarity(col, existing_col) > 0.8:
                        groups[group_name].append((tbl, col))
                        matched = True
                        break
                if matched:
                    break

    # Filter: only keep groups with columns from multiple tables or multiple columns
    semantic_groups = {
        k: v for k, v in groups.items()
        if len(v) >= 2
    }

    # Store in DuckDB
    _store_dictionary(conn, semantic_groups)

    return semantic_groups


def _column_similarity(a: str, b: str) -> float:
    """Calculate name similarity between two columns."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def _store_dictionary(
    conn: duckdb.DuckDBPyConnection,
    groups: dict[str, list[tuple[str, str]]],
):
    """Persist semantic dictionary to DuckDB."""
    # Clear existing entries
    conn.execute("DELETE FROM _semantic_dictionary")

    for group_name, members in groups.items():
        for tbl, col in members:
            conn.execute("""
                INSERT INTO _semantic_dictionary (semantic_group, table_name, column_name, confidence)
                VALUES (?, ?, ?, ?)
            """, [group_name, tbl, col, 1.0])

    logger.info(f"Stored {len(groups)} semantic groups")

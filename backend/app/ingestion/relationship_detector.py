"""
Relationship detector.
Discovers foreign key relationships between tables by:
1. Name matching — identical column names across tables
2. Value overlap — columns sharing >80% of distinct values
"""

import logging
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import duckdb

logger = logging.getLogger(__name__)


@dataclass
class Relationship:
    source_table: str
    source_column: str
    target_table: str
    target_column: str
    relationship_type: str  # one-to-one, one-to-many, many-to-many
    confidence: float
    detection_method: str  # name_match, value_overlap, semantic

    def to_dict(self) -> dict:
        return asdict(self)


def _column_name_similarity(a: str, b: str) -> float:
    """Calculate similarity between two column names."""
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


def discover_relationships(
    conn: duckdb.DuckDBPyConnection,
    table_names: list[str],
) -> list[Relationship]:
    """
    Discover foreign key relationships across all tables.

    Strategy:
    1. Find columns with identical names across different tables.
    2. For columns with similar names (>0.8 similarity), check value overlap.

    Args:
        conn: DuckDB connection (read).
        table_names: List of user data table names.

    Returns:
        List of discovered Relationship objects.
    """
    relationships: list[Relationship] = []
    # Filter out internal metadata tables
    user_tables = [t for t in table_names if not t.startswith('_')]

    if len(user_tables) < 2:
        return relationships

    # Gather column info for each table
    table_columns: dict[str, list[str]] = {}
    for tbl in user_tables:
        try:
            cols = conn.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{tbl}'").fetchall()
            table_columns[tbl] = [row[0] for row in cols]
        except Exception as e:
            logger.warning(f"Could not get columns for {tbl}: {e}")
            continue

    # Compare every pair of tables
    checked = set()
    for tbl_a in user_tables:
        for tbl_b in user_tables:
            if tbl_a == tbl_b:
                continue
            pair_key = tuple(sorted([tbl_a, tbl_b]))
            if pair_key in checked:
                continue
            checked.add(pair_key)

            cols_a = table_columns.get(tbl_a, [])
            cols_b = table_columns.get(tbl_b, [])

            for col_a in cols_a:
                for col_b in cols_b:
                    sim = _column_name_similarity(col_a, col_b)
                    if sim < 0.8:
                        continue

                    # Check value overlap
                    try:
                        overlap = _check_value_overlap(conn, tbl_a, col_a, tbl_b, col_b)
                    except Exception:
                        overlap = 0.0

                    if overlap < 0.3:
                        continue

                    method = "name_match" if sim == 1.0 else "value_overlap"
                    confidence = (sim + overlap) / 2.0

                    # Determine relationship type
                    rel_type = _detect_relationship_type(conn, tbl_a, col_a, tbl_b, col_b)

                    relationships.append(Relationship(
                        source_table=tbl_a,
                        source_column=col_a,
                        target_table=tbl_b,
                        target_column=col_b,
                        relationship_type=rel_type,
                        confidence=round(confidence, 3),
                        detection_method=method,
                    ))

    return relationships


def _check_value_overlap(
    conn: duckdb.DuckDBPyConnection,
    table_a: str, col_a: str,
    table_b: str, col_b: str,
) -> float:
    """Calculate the fraction of values in col_a that also appear in col_b."""
    result = conn.execute(f"""
        WITH
        a AS (SELECT DISTINCT "{col_a}" AS val FROM "{table_a}" WHERE "{col_a}" IS NOT NULL),
        b AS (SELECT DISTINCT "{col_b}" AS val FROM "{table_b}" WHERE "{col_b}" IS NOT NULL)
        SELECT
            (SELECT COUNT(*) FROM a INNER JOIN b ON CAST(a.val AS VARCHAR) = CAST(b.val AS VARCHAR)) AS overlap,
            (SELECT COUNT(*) FROM a) AS total_a,
            (SELECT COUNT(*) FROM b) AS total_b
    """).fetchone()

    if not result:
        return 0.0
    overlap, total_a, total_b = result
    if total_a == 0 and total_b == 0:
        return 0.0
    denom = min(total_a, total_b) if min(total_a, total_b) > 0 else 1
    return overlap / denom


def _detect_relationship_type(
    conn: duckdb.DuckDBPyConnection,
    table_a: str, col_a: str,
    table_b: str, col_b: str,
) -> str:
    """Detect if relationship is one-to-one, one-to-many, or many-to-many."""
    try:
        a_unique = conn.execute(
            f'SELECT COUNT(DISTINCT "{col_a}") = COUNT(*) FROM "{table_a}" WHERE "{col_a}" IS NOT NULL'
        ).fetchone()[0]
        b_unique = conn.execute(
            f'SELECT COUNT(DISTINCT "{col_b}") = COUNT(*) FROM "{table_b}" WHERE "{col_b}" IS NOT NULL'
        ).fetchone()[0]

        if a_unique and b_unique:
            return "one-to-one"
        elif a_unique or b_unique:
            return "one-to-many"
        else:
            return "many-to-many"
    except Exception:
        return "unknown"

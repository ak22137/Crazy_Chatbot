"""
SQL Agent.
The core intelligence: takes a user question, retrieves relevant schema,
generates SQL via Mistral, validates, executes, and self-repairs on failure.
"""

import json
import time
import uuid
import logging
import re
from dataclasses import dataclass, field

import duckdb

from app.llm.mistral_client import chat, parse_json_response
from app.llm.prompts import SQL_GENERATION, SQL_REPAIR, TABLE_SELECTION
from app.agents.history_utils import format_history_context
from app.agents.sql_agent.sql_validator import validate_sql
from app.ingestion.metadata_builder import get_all_metadata

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
MAX_RESULT_ROWS = 200


def _extract_sql_from_text(text: str) -> str:
    """Best-effort SQL extraction from non-JSON model responses."""
    if not text:
        return ""

    raw = text.strip()

    # Prefer SQL fenced block.
    fenced = re.search(r"```(?:sql)?\s*([\s\S]*?)\s*```", raw, flags=re.IGNORECASE)
    if fenced:
        candidate = fenced.group(1).strip()
        if candidate.lower().startswith(("select", "with")):
            return candidate.rstrip(";")

    # Fallback: first WITH... or SELECT... statement.
    stmt_match = re.search(r"(?is)\b(with|select)\b[\s\S]*", raw)
    if not stmt_match:
        return ""

    candidate = stmt_match.group(0).strip()
    # If model returned extra explanation after SQL, keep only until first semicolon.
    if ";" in candidate:
        candidate = candidate.split(";", 1)[0]

    return candidate.strip()


def _extract_sql_from_parsed(parsed: dict | list | str | None) -> str:
    """Extract SQL from parsed JSON using common key variants and nested objects."""
    if parsed is None:
        return ""

    if isinstance(parsed, str):
        return _extract_sql_from_text(parsed)

    if isinstance(parsed, list):
        for item in parsed:
            sql = _extract_sql_from_parsed(item)
            if sql:
                return sql
        return ""

    if not isinstance(parsed, dict):
        return ""

    for key in ("sql", "query", "sql_query", "statement"):
        value = parsed.get(key)
        if isinstance(value, str):
            sql = _extract_sql_from_text(value)
            if sql:
                return sql

    for value in parsed.values():
        sql = _extract_sql_from_parsed(value)
        if sql:
            return sql

    return ""


@dataclass
class SQLResult:
    success: bool
    sql: str = ""
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0
    explanation: str = ""
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "success": self.success,
            "sql": self.sql,
            "columns": self.columns,
            "rows": self.rows,
            "row_count": self.row_count,
            "execution_time_ms": self.execution_time_ms,
            "explanation": self.explanation,
            "error": self.error,
        }

    def results_as_text(self) -> str:
        """Format results as a readable text table for the LLM."""
        if not self.rows:
            return "No results."
        lines = [" | ".join(self.columns)]
        lines.append("-" * len(lines[0]))
        for row in self.rows[:50]:  # Limit for LLM context
            lines.append(" | ".join(str(v) for v in row))
        if self.row_count > 50:
            lines.append(f"... and {self.row_count - 50} more rows")
        return "\n".join(lines)


def _build_schema_context(
    metadata: dict,
    conn: duckdb.DuckDBPyConnection | None = None,
    tables: list[str] | None = None,
) -> str:
    """Build a concise schema string for the LLM prompt.

    For low-cardinality string columns, the actual distinct values are
    listed so the LLM can filter correctly (e.g. status / workflow columns).
    """
    lines = []
    for tbl_name, tbl_info in metadata.items():
        if tables and tbl_name not in tables:
            continue
        cols = []
        for col_name, col_info in tbl_info["columns"].items():
            pk = " [PK]" if col_info.get("primary_key") else ""
            dtype = col_info["type"]
            distinct = col_info.get("distinct_count", 0) or 0

            extra = ""
            if conn is not None and dtype == "string" and 0 < distinct <= 30:
                values = _get_distinct_values(conn, tbl_name, col_name, limit=30)
                if values:
                    extra = f" — allowed values: {', '.join(values)}"
            if not extra:
                samples = col_info.get("sample_values", [])
                sample_str = f" (e.g., {', '.join(samples[:3])})" if samples else ""
                extra = sample_str

            cols.append(f"  - {col_name}: {dtype}{pk}{extra}")
        lines.append(f"Table: {tbl_name} ({tbl_info['row_count']} rows)")
        lines.extend(cols)
        lines.append("")
    return "\n".join(lines)


def _get_distinct_values(
    conn: duckdb.DuckDBPyConnection,
    table_name: str,
    column_name: str,
    limit: int = 30,
) -> list[str]:
    """Fetch distinct non-null values for a low-cardinality column."""
    try:
        rows = conn.execute(
            f'SELECT DISTINCT "{column_name}" FROM "{table_name}" '
            f'WHERE "{column_name}" IS NOT NULL LIMIT {limit}'
        ).fetchall()
        return [str(r[0]) for r in rows if r[0] is not None and str(r[0]).strip() != ""]
    except Exception:
        return []


def _build_table_summaries(metadata: dict) -> str:
    """Build brief table summaries for table selection."""
    lines = []
    for tbl_name, tbl_info in metadata.items():
        col_names = list(tbl_info["columns"].keys())
        lines.append(f"- {tbl_name}: {tbl_info['row_count']} rows, columns: {', '.join(col_names)}")
    return "\n".join(lines)


def _get_relationships_context(conn: duckdb.DuckDBPyConnection) -> str:
    """Get relationship context from DuckDB."""
    try:
        rels = conn.execute("""
            SELECT source_table, source_column, target_table, target_column, relationship_type
            FROM _relationships
        """).fetchall()
        if not rels:
            return "No relationships detected."
        lines = []
        for src_tbl, src_col, tgt_tbl, tgt_col, rel_type in rels:
            lines.append(f"- {src_tbl}.{src_col} → {tgt_tbl}.{tgt_col} ({rel_type})")
        return "\n".join(lines)
    except Exception:
        return "No relationships available."


def _get_semantic_hints(conn: duckdb.DuckDBPyConnection) -> str:
    """Get semantic dictionary hints."""
    try:
        groups = conn.execute("""
            SELECT semantic_group, table_name, column_name
            FROM _semantic_dictionary
            ORDER BY semantic_group
        """).fetchall()
        if not groups:
            return "No semantic groups."
        current_group = None
        lines = []
        for group, tbl, col in groups:
            if group != current_group:
                current_group = group
                lines.append(f"\n{group}:")
            lines.append(f"  - {tbl}.{col}")
        return "\n".join(lines)
    except Exception:
        return "No semantic hints available."


def _select_tables(question: str, metadata: dict, history: list[dict] | None = None) -> list[str]:
    """Use LLM to select relevant tables for the question."""
    if len(metadata) <= 3:
        # If few tables, just use all of them
        return list(metadata.keys())

    history_context = format_history_context(history or [])

    prompt = TABLE_SELECTION.format(
        table_summaries=_build_table_summaries(metadata),
        question=question,
        conversation_history=history_context,
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=256,
        json_mode=True,
    )

    parsed = parse_json_response(response)
    tables = parsed.get("tables", list(metadata.keys()))
    # Validate table names
    valid_tables = [t for t in tables if t in metadata]
    return valid_tables or list(metadata.keys())


def run_sql_agent(
    question: str,
    read_conn: duckdb.DuckDBPyConnection,
    write_conn: duckdb.DuckDBPyConnection | None = None,
    history: list[dict] | None = None,
) -> SQLResult:
    """
    Full SQL agent pipeline:
    1. Retrieve metadata
    2. Select relevant tables (schema pruning)
    3. Generate SQL via Mistral
    4. Validate SQL
    5. Execute SQL
    6. If error → repair and retry (up to MAX_RETRIES)

    Args:
        question: User's natural language question.
        read_conn: Read-only DuckDB connection for query execution.
        write_conn: Write connection for logging (optional).

    Returns:
        SQLResult with query results or error info.
    """
    start_time = time.time()
    query_id = str(uuid.uuid4())[:8]

    # 1. Get full metadata
    metadata = get_all_metadata(read_conn)
    if not metadata:
        return SQLResult(success=False, error="No data tables found. Please upload a file first.")

    # 2. Select relevant tables
    selected_tables = _select_tables(question, metadata, history=history)
    schema_context = _build_schema_context(metadata, read_conn, selected_tables)

    # 3. Get relationships and semantic hints
    relationships_ctx = _get_relationships_context(read_conn)
    semantic_hints = _get_semantic_hints(read_conn)

    history_context = format_history_context(history or [])

    # 4. Generate SQL
    prompt = SQL_GENERATION.format(
        schema_context=schema_context,
        relationships=relationships_ctx,
        semantic_hints=semantic_hints,
        question=question,
        conversation_history=history_context,
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1024,
        json_mode=True,
    )

    parsed = parse_json_response(response)
    sql = _extract_sql_from_parsed(parsed) or _extract_sql_from_text(response)
    explanation = parsed.get("explanation", "")

    if not sql:
        # One-shot normalization fallback for providers that ignore json_mode.
        normalize_prompt = (
            "Return ONLY valid JSON with keys sql and explanation. "
            "The sql must be a DuckDB SELECT query.\n"
            f"Original question: {question}\n"
            f"Schema context:\n{schema_context}\n"
            f"Previous model output:\n{response}"
        )
        normalized = chat(
            messages=[{"role": "user", "content": normalize_prompt}],
            temperature=0.0,
            max_tokens=1024,
            json_mode=True,
        )
        normalized_parsed = parse_json_response(normalized)
        sql = _extract_sql_from_parsed(normalized_parsed) or _extract_sql_from_text(normalized)
        if not explanation:
            explanation = normalized_parsed.get("explanation", "") if isinstance(normalized_parsed, dict) else ""

    if not sql:
        return SQLResult(success=False, error="LLM did not generate a SQL query.", explanation=explanation)

    # 5. Try executing with retry loop
    last_error = ""
    for attempt in range(MAX_RETRIES + 1):
        # Validate
        is_valid, validation_error = validate_sql(sql)
        if not is_valid:
            last_error = f"Validation error: {validation_error}"
            logger.warning(f"SQL validation failed (attempt {attempt+1}): {validation_error}")
            if attempt < MAX_RETRIES:
                sql = _repair_sql(question, schema_context, sql, validation_error)
                continue
            else:
                break

        # Execute
        try:
            exec_start = time.time()
            result = read_conn.execute(sql)
            columns = [desc[0] for desc in result.description] if result.description else []
            rows = result.fetchmany(MAX_RESULT_ROWS)
            # Get total count
            row_count = len(rows)
            # Try to get full count if limited
            if row_count == MAX_RESULT_ROWS:
                try:
                    count_result = read_conn.execute(f"SELECT COUNT(*) FROM ({sql}) AS _cnt").fetchone()
                    row_count = count_result[0]
                except Exception:
                    pass
            exec_time = (time.time() - exec_start) * 1000

            # Convert rows to serializable format
            clean_rows = []
            for row in rows:
                clean_rows.append([
                    str(v) if v is not None else None
                    for v in row
                ])

            total_time = (time.time() - start_time) * 1000

            # Log query
            if write_conn:
                try:
                    write_conn.execute("""
                        INSERT INTO _query_log (query_id, question, intent, generated_sql, execution_time_ms, row_count)
                        VALUES (?, ?, 'SQL_ANALYTICS', ?, ?, ?)
                    """, [query_id, question, sql, total_time, row_count])
                except Exception:
                    pass

            return SQLResult(
                success=True,
                sql=sql,
                columns=columns,
                rows=clean_rows,
                row_count=row_count,
                execution_time_ms=round(exec_time, 2),
                explanation=explanation,
            )

        except Exception as e:
            last_error = str(e)
            logger.warning(f"SQL execution failed (attempt {attempt+1}): {e}")
            if attempt < MAX_RETRIES:
                sql = _repair_sql(question, schema_context, sql, last_error)
            continue

    # All retries failed
    total_time = (time.time() - start_time) * 1000
    if write_conn:
        try:
            write_conn.execute("""
                INSERT INTO _query_log (query_id, question, intent, generated_sql, execution_time_ms, error)
                VALUES (?, ?, 'SQL_ANALYTICS', ?, ?, ?)
            """, [query_id, question, sql, total_time, last_error])
        except Exception:
            pass

    return SQLResult(success=False, sql=sql, error=last_error, explanation=explanation)


def _repair_sql(question: str, schema_context: str, failed_sql: str, error: str) -> str:
    """Ask the LLM to fix a failed SQL query."""
    prompt = SQL_REPAIR.format(
        question=question,
        schema_context=schema_context,
        failed_sql=failed_sql,
        error=error,
    )

    response = chat(
        messages=[{"role": "user", "content": prompt}],
        temperature=0.0,
        max_tokens=1024,
        json_mode=True,
    )

    parsed = parse_json_response(response)
    new_sql = _extract_sql_from_parsed(parsed) or _extract_sql_from_text(response) or failed_sql
    logger.info(f"Repaired SQL: {new_sql}")
    return new_sql

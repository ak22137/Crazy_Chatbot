"""
DuckDB connection manager.
- Write connection: single, for ingestion operations
- Read connections: per-request, for query execution
"""

import duckdb
from pathlib import Path
from contextlib import contextmanager
from app.config import settings

_write_conn: duckdb.DuckDBPyConnection | None = None


def _init_metadata_tables(conn: duckdb.DuckDBPyConnection):
    """Create internal metadata tables if they don't exist."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _uploads (
            upload_id    VARCHAR PRIMARY KEY,
            filename     VARCHAR NOT NULL,
            file_type    VARCHAR NOT NULL,
            uploaded_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            file_size    BIGINT,
            status       VARCHAR DEFAULT 'processing'
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _metadata_tables (
            table_name   VARCHAR PRIMARY KEY,
            upload_id    VARCHAR,
            sheet_name   VARCHAR,
            description  VARCHAR,
            row_count    BIGINT,
            column_count INTEGER,
            created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _metadata_columns (
            table_name     VARCHAR,
            column_name    VARCHAR,
            data_type      VARCHAR,
            nullable       BOOLEAN,
            is_primary_key BOOLEAN DEFAULT FALSE,
            is_foreign_key BOOLEAN DEFAULT FALSE,
            fk_references  VARCHAR,
            description    VARCHAR,
            sample_values  VARCHAR,
            distinct_count BIGINT,
            null_count     BIGINT,
            PRIMARY KEY (table_name, column_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _relationships (
            source_table    VARCHAR,
            source_column   VARCHAR,
            target_table    VARCHAR,
            target_column   VARCHAR,
            relationship_type VARCHAR,
            confidence      FLOAT,
            detection_method  VARCHAR,
            PRIMARY KEY (source_table, source_column, target_table, target_column)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _semantic_dictionary (
            semantic_group VARCHAR,
            table_name     VARCHAR,
            column_name    VARCHAR,
            confidence     FLOAT,
            PRIMARY KEY (semantic_group, table_name, column_name)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS _query_log (
            query_id        VARCHAR PRIMARY KEY,
            question        VARCHAR,
            intent          VARCHAR,
            generated_sql   VARCHAR,
            execution_time_ms FLOAT,
            row_count       BIGINT,
            error           VARCHAR,
            created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)


def get_write_connection() -> duckdb.DuckDBPyConnection:
    """Get the singleton write connection. Creates DB and metadata tables on first call."""
    global _write_conn
    if _write_conn is None:
        Path(settings.duckdb_path).parent.mkdir(parents=True, exist_ok=True)
        _write_conn = duckdb.connect(settings.duckdb_path)
        _init_metadata_tables(_write_conn)
    return _write_conn


def get_read_connection() -> duckdb.DuckDBPyConnection:
    """Get the shared connection for query execution."""
    return get_write_connection()


@contextmanager
def read_connection():
    """Context manager for read operations.

    DuckDB rejects opening the same file with a different configuration while
    the app's long-lived write connection is active, so reads share it.
    """
    conn = get_read_connection()
    yield conn


def close_all():
    """Close the write connection. Call on shutdown."""
    global _write_conn
    if _write_conn is not None:
        _write_conn.close()
        _write_conn = None

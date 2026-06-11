"""
Metadata builder.
Generates and stores table-level and column-level metadata
in DuckDB's internal catalog tables.
"""

import json
import logging
import duckdb
from app.ingestion.schema_detector import TableSchema

logger = logging.getLogger(__name__)


def store_table_metadata(
    conn: duckdb.DuckDBPyConnection,
    schema: TableSchema,
    upload_id: str,
    sheet_name: str,
):
    """
    Store table and column metadata in the internal catalog.

    Args:
        conn: DuckDB write connection.
        schema: The detected TableSchema.
        upload_id: ID of the upload this table belongs to.
        sheet_name: Original Excel sheet name.
    """
    # Upsert table metadata
    conn.execute("""
        INSERT OR REPLACE INTO _metadata_tables
        (table_name, upload_id, sheet_name, description, row_count, column_count)
        VALUES (?, ?, ?, ?, ?, ?)
    """, [
        schema.table_name,
        upload_id,
        sheet_name,
        f"Table from sheet '{sheet_name}' with {schema.row_count} rows and {schema.column_count} columns.",
        schema.row_count,
        schema.column_count,
    ])

    # Upsert column metadata
    for col in schema.columns:
        conn.execute("""
            INSERT OR REPLACE INTO _metadata_columns
            (table_name, column_name, data_type, nullable, is_primary_key,
             description, sample_values, distinct_count, null_count)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, [
            schema.table_name,
            col.name,
            col.data_type,
            col.nullable,
            col.is_primary_key,
            f"{'Primary key. ' if col.is_primary_key else ''}{'Categorical. ' if col.is_categorical else ''}{col.data_type} column with {col.distinct_count} distinct values.",
            json.dumps(col.sample_values),
            col.distinct_count,
            col.null_count,
        ])

    logger.info(f"Stored metadata for table '{schema.table_name}' ({schema.column_count} columns)")


def store_relationships(
    conn: duckdb.DuckDBPyConnection,
    relationships: list,
):
    """Store discovered relationships in the catalog."""
    for rel in relationships:
        conn.execute("""
            INSERT OR REPLACE INTO _relationships
            (source_table, source_column, target_table, target_column,
             relationship_type, confidence, detection_method)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, [
            rel.source_table, rel.source_column,
            rel.target_table, rel.target_column,
            rel.relationship_type, rel.confidence, rel.detection_method,
        ])

    logger.info(f"Stored {len(relationships)} relationships")


def get_all_metadata(conn: duckdb.DuckDBPyConnection) -> dict:
    """Retrieve the full metadata catalog for all tables."""
    tables = conn.execute("""
        SELECT table_name, description, row_count, column_count
        FROM _metadata_tables ORDER BY table_name
    """).fetchall()

    result = {}
    for tbl_name, desc, rows, cols in tables:
        columns = conn.execute("""
            SELECT column_name, data_type, nullable, is_primary_key,
                   description, sample_values, distinct_count
            FROM _metadata_columns
            WHERE table_name = ?
            ORDER BY column_name
        """, [tbl_name]).fetchall()

        result[tbl_name] = {
            "description": desc,
            "row_count": rows,
            "column_count": cols,
            "columns": {
                col_name: {
                    "type": dtype,
                    "nullable": nullable,
                    "primary_key": pk,
                    "description": cdesc,
                    "sample_values": json.loads(samples) if samples else [],
                    "distinct_count": distinct,
                }
                for col_name, dtype, nullable, pk, cdesc, samples, distinct in columns
            }
        }

    return result


def get_table_names(conn: duckdb.DuckDBPyConnection) -> list[str]:
    """Get all user data table names (excluding internal _ tables)."""
    result = conn.execute("""
        SELECT table_name FROM _metadata_tables ORDER BY table_name
    """).fetchall()
    return [r[0] for r in result]

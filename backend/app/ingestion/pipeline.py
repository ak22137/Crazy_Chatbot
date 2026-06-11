"""
Ingestion pipeline orchestrator.
Takes an uploaded file through the full pipeline:
  Parse → Store in DuckDB → Export Parquet → Detect Schema →
  Discover Relationships → Build Metadata → Build Semantic Dictionary
"""

import uuid
import logging
from pathlib import Path
from dataclasses import dataclass, field

import pandas as pd
import duckdb

from app.config import settings
from app.ingestion.excel_parser import parse_file
from app.ingestion.schema_detector import detect_schema, TableSchema
from app.ingestion.relationship_detector import discover_relationships, Relationship
from app.ingestion.metadata_builder import store_table_metadata, store_relationships, get_table_names
from app.ingestion.semantic_dictionary import build_semantic_dictionary

logger = logging.getLogger(__name__)


@dataclass
class IngestionResult:
    upload_id: str
    filename: str
    tables: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    semantic_groups: dict = field(default_factory=dict)
    status: str = "success"
    error: str | None = None

    def to_dict(self) -> dict:
        return {
            "upload_id": self.upload_id,
            "filename": self.filename,
            "tables": self.tables,
            "relationships": self.relationships,
            "semantic_groups": {k: [{"table": t, "column": c} for t, c in v] for k, v in self.semantic_groups.items()},
            "status": self.status,
            "error": self.error,
        }


def _make_table_name(filename: str, sheet_name: str) -> str:
    """Generate a safe DuckDB table name from filename + sheet."""
    base = Path(filename).stem.lower()
    base = "".join(c if c.isalnum() or c == '_' else '_' for c in base)
    sheet = sheet_name.lower()
    sheet = "".join(c if c.isalnum() or c == '_' else '_' for c in sheet)
    name = f"{base}_{sheet}" if sheet != "sheet1" else base
    # Ensure it doesn't start with underscore (reserved for metadata)
    if name.startswith('_'):
        name = f"t{name}"
    return name


def run_ingestion(
    file_path: str | Path,
    filename: str,
    conn: duckdb.DuckDBPyConnection,
) -> IngestionResult:
    """
    Run the full ingestion pipeline for a single uploaded file.

    Args:
        file_path: Path to the uploaded file on disk.
        filename: Original filename (for naming tables).
        conn: DuckDB write connection.

    Returns:
        IngestionResult with summary of what was created.
    """
    upload_id = str(uuid.uuid4())[:8]
    result = IngestionResult(upload_id=upload_id, filename=filename)

    try:
        # 1. Record the upload
        file_size = Path(file_path).stat().st_size
        file_type = Path(filename).suffix.lower().lstrip('.')
        conn.execute("""
            INSERT INTO _uploads (upload_id, filename, file_type, file_size, status)
            VALUES (?, ?, ?, ?, 'processing')
        """, [upload_id, filename, file_type, file_size])

        # 2. Parse file
        logger.info(f"Parsing file: {filename}")
        sheets = parse_file(file_path)
        if not sheets:
            raise ValueError("No readable data found in the file.")

        created_tables: list[str] = []

        for sheet_name, df in sheets:
            table_name = _make_table_name(filename, sheet_name)

            # 3. Store in DuckDB
            logger.info(f"Creating table '{table_name}' ({len(df)} rows, {len(df.columns)} cols)")
            conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')
            conn.register("_tmp_df", df)
            conn.execute(f'CREATE TABLE "{table_name}" AS SELECT * FROM _tmp_df')
            conn.unregister("_tmp_df")

            # 4. Export to Parquet
            parquet_dir = Path(settings.parquet_dir)
            parquet_dir.mkdir(parents=True, exist_ok=True)
            parquet_path = parquet_dir / f"{table_name}.parquet"
            conn.execute(f"COPY \"{table_name}\" TO '{parquet_path}' (FORMAT PARQUET)")
            logger.info(f"Exported Parquet: {parquet_path}")

            # 5. Detect schema
            schema = detect_schema(table_name, df)

            # 6. Store metadata
            store_table_metadata(conn, schema, upload_id, sheet_name)

            result.tables.append({
                "table_name": table_name,
                "sheet_name": sheet_name,
                "row_count": schema.row_count,
                "column_count": schema.column_count,
                "columns": [c.name for c in schema.columns],
                "primary_key": schema.primary_key_candidates[:1],
            })
            created_tables.append(table_name)

        # 7. Discover relationships across ALL tables (including pre-existing)
        all_tables = get_table_names(conn)
        relationships = discover_relationships(conn, all_tables)
        store_relationships(conn, relationships)
        result.relationships = [r.to_dict() for r in relationships]

        # 8. Build semantic dictionary
        semantic_groups = build_semantic_dictionary(conn, all_tables)
        result.semantic_groups = semantic_groups

        # 9. Mark upload complete
        conn.execute("""
            UPDATE _uploads SET status = 'ready' WHERE upload_id = ?
        """, [upload_id])

        logger.info(f"Ingestion complete: {len(created_tables)} tables, {len(relationships)} relationships")

    except Exception as e:
        logger.error(f"Ingestion failed for {filename}: {e}", exc_info=True)
        result.status = "error"
        result.error = str(e)
        try:
            conn.execute("""
                UPDATE _uploads SET status = 'error' WHERE upload_id = ?
            """, [upload_id])
        except Exception:
            pass

    return result

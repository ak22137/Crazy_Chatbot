"""
Metadata API endpoint.
Explore tables, columns, relationships, and semantic dictionary.
"""

import json
from fastapi import APIRouter
from app.database.connection import read_connection
from app.ingestion.metadata_builder import get_all_metadata

router = APIRouter(prefix="/metadata", tags=["Metadata"])


@router.get("/tables")
async def list_tables():
    """List all tables with their metadata."""
    with read_connection() as conn:
        metadata = get_all_metadata(conn)
    return {"tables": metadata}


@router.get("/tables/{table_name}")
async def get_table_detail(table_name: str):
    """Get detailed metadata for a specific table."""
    with read_connection() as conn:
        metadata = get_all_metadata(conn)
    if table_name not in metadata:
        return {"error": f"Table '{table_name}' not found."}
    return {"table": table_name, **metadata[table_name]}


@router.get("/tables/{table_name}/preview")
async def preview_table(table_name: str, limit: int = 20):
    """Preview the first N rows of a table."""
    with read_connection() as conn:
        try:
            result = conn.execute(f'SELECT * FROM "{table_name}" LIMIT {min(limit, 100)}')
            columns = [desc[0] for desc in result.description]
            rows = result.fetchall()
            return {
                "table": table_name,
                "columns": columns,
                "rows": [[str(v) if v is not None else None for v in row] for row in rows],
                "count": len(rows),
            }
        except Exception as e:
            return {"error": str(e)}


@router.get("/relationships")
async def get_relationships():
    """Get all discovered relationships."""
    with read_connection() as conn:
        try:
            rels = conn.execute("""
                SELECT source_table, source_column, target_table, target_column,
                       relationship_type, confidence, detection_method
                FROM _relationships
                ORDER BY confidence DESC
            """).fetchall()
            return {
                "relationships": [
                    {
                        "source": f"{r[0]}.{r[1]}",
                        "target": f"{r[2]}.{r[3]}",
                        "type": r[4],
                        "confidence": r[5],
                        "method": r[6],
                    }
                    for r in rels
                ]
            }
        except Exception:
            return {"relationships": []}


@router.get("/dictionary")
async def get_semantic_dictionary():
    """Get the semantic dictionary — groups of equivalent columns."""
    with read_connection() as conn:
        try:
            groups = conn.execute("""
                SELECT semantic_group, table_name, column_name, confidence
                FROM _semantic_dictionary
                ORDER BY semantic_group, table_name
            """).fetchall()

            result = {}
            for group, tbl, col, conf in groups:
                if group not in result:
                    result[group] = []
                result[group].append({"table": tbl, "column": col, "confidence": conf})

            return {"semantic_groups": result}
        except Exception:
            return {"semantic_groups": {}}

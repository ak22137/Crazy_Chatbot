"""
File upload API endpoint.
Handles single/multi-file uploads, saves to disk, triggers ingestion pipeline.
"""

import shutil
import logging
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.config import settings
from app.database.connection import get_write_connection
from app.ingestion.pipeline import run_ingestion

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/upload", tags=["Upload"])

ALLOWED_EXTENSIONS = {".xlsx", ".xls", ".csv"}
MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB


class UploadResponse(BaseModel):
    upload_id: str
    filename: str
    status: str
    tables: list[dict] = []
    relationships: list[dict] = []
    semantic_groups: dict = {}
    error: str | None = None


@router.post("", response_model=list[UploadResponse])
async def upload_files(files: list[UploadFile] = File(...)):
    """
    Upload one or more Excel/CSV files.

    Each file is saved, parsed, and loaded into DuckDB.
    Returns metadata about created tables, detected relationships,
    and semantic groups.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files provided.")

    results = []
    conn = get_write_connection()

    for file in files:
        # Validate extension
        suffix = Path(file.filename).suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            results.append(UploadResponse(
                upload_id="",
                filename=file.filename,
                status="error",
                error=f"Unsupported file type: {suffix}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
            ))
            continue

        # Save to disk
        upload_dir = Path(settings.upload_dir)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / file.filename

        try:
            with open(file_path, "wb") as f:
                content = await file.read()
                if len(content) > MAX_FILE_SIZE:
                    results.append(UploadResponse(
                        upload_id="",
                        filename=file.filename,
                        status="error",
                        error=f"File too large. Maximum size: {MAX_FILE_SIZE // (1024*1024)}MB",
                    ))
                    continue
                f.write(content)
        except Exception as e:
            results.append(UploadResponse(
                upload_id="",
                filename=file.filename,
                status="error",
                error=f"Failed to save file: {e}",
            ))
            continue

        # Run ingestion
        try:
            ingestion_result = run_ingestion(str(file_path), file.filename, conn)
            results.append(UploadResponse(
                upload_id=ingestion_result.upload_id,
                filename=ingestion_result.filename,
                status=ingestion_result.status,
                tables=ingestion_result.tables,
                relationships=ingestion_result.relationships,
                semantic_groups={
                    k: [{"table": t, "column": c} for t, c in v]
                    for k, v in ingestion_result.semantic_groups.items()
                },
                error=ingestion_result.error,
            ))
        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            results.append(UploadResponse(
                upload_id="",
                filename=file.filename,
                status="error",
                error=str(e),
            ))

    return results


@router.get("/tables")
async def list_tables():
    """List all uploaded tables with metadata."""
    from app.ingestion.metadata_builder import get_all_metadata
    from app.database.connection import read_connection

    with read_connection() as conn:
        metadata = get_all_metadata(conn)

    return {"tables": metadata}

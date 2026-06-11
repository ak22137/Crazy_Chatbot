"""
FastAPI application entry point.
Excel Intelligence — Conversational Analytics Platform.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database.connection import get_write_connection, close_all
from app.api.v1.upload import router as upload_router
from app.api.v1.chat import router as chat_router
from app.api.v1.metadata import router as metadata_router

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # Startup
    settings.ensure_dirs()
    get_write_connection()  # Initialize DB + metadata tables
    logger.info("🚀 Excel Intelligence backend started")
    logger.info(f"   DuckDB: {settings.duckdb_path}")
    logger.info(f"   Mistral Model: {settings.mistral_model}")

    yield

    # Shutdown
    close_all()
    logger.info("Backend shutdown complete")


app = FastAPI(
    title="Excel Intelligence API",
    description="Conversational analytics platform for Excel data. Upload files, ask questions, get SQL-powered answers.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routers
app.include_router(upload_router, prefix="/api/v1")
app.include_router(chat_router, prefix="/api/v1")
app.include_router(metadata_router, prefix="/api/v1")


@app.get("/api/v1/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "model": settings.mistral_model}

"""
Application configuration via environment variables.
Uses pydantic-settings for validated, typed config.
"""

from pydantic_settings import BaseSettings
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # Mistral AI
    mistral_api_key: str = ""
    mistral_model: str = "mistral-small-latest"

    # DuckDB
    duckdb_path: str = "./storage/analytics.duckdb"

    # Qdrant (optional, for RAG)
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "excel_docs"

    # Storage
    upload_dir: str = "./storage/raw_files"
    parquet_dir: str = "./storage/parquet"

    # Server
    backend_host: str = "0.0.0.0"
    backend_port: int = 8000

    model_config = {
        "env_file": ROOT_DIR / ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }

    def ensure_dirs(self):
        """Create storage directories if they don't exist."""
        for d in [self.upload_dir, self.parquet_dir, Path(self.duckdb_path).parent]:
            Path(d).mkdir(parents=True, exist_ok=True)


settings = Settings()

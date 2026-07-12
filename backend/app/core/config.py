from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    # App
    APP_NAME: str = "Open Analytics AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    SECRET_KEY: str = "change-this-secret-key-in-production-use-256-bit-key"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # CORS
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:80", "http://frontend:3000"]

    # Storage
    UPLOAD_DIR: str = "/app/data/uploads"
    EXPORT_DIR: str = "/app/data/exports"
    DUCKDB_PATH: str = "/app/data/analytics.duckdb"
    METADATA_DB: str = "/app/data/metadata.sqlite"

    # File limits
    MAX_FILE_SIZE_MB: int = 500
    MAX_ROWS_PREVIEW: int = 1000

    # LLM (Ollama)
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    DEFAULT_MODEL: str = "llama3.1"
    LLM_TIMEOUT: int = 180
    MAX_TOKENS: int = 2048
    TEMPERATURE: float = 0.1

    # Query limits
    MAX_QUERY_ROWS: int = 100000
    QUERY_TIMEOUT: int = 30

    class Config:
        env_file = ".env"


settings = Settings()

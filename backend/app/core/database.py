"""Database initialization and connection management."""

import duckdb
import sqlite3
import logging
from app.core.config import settings

logger = logging.getLogger(__name__)


def get_duckdb_connection():
    """Get a DuckDB connection."""
    return duckdb.connect(settings.DUCKDB_PATH)


def get_metadata_connection():
    """Get SQLite metadata connection."""
    conn = sqlite3.connect(settings.METADATA_DB)
    conn.row_factory = sqlite3.Row
    return conn


async def init_db():
    """Initialize all databases."""
    logger.info("Initializing databases...")
    _init_metadata_db()
    _init_duckdb()
    logger.info("Databases initialized.")


def _init_metadata_db():
    """Create SQLite metadata tables."""
    conn = get_metadata_connection()
    cur = conn.cursor()

    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            hashed_password TEXT NOT NULL,
            role TEXT DEFAULT 'viewer',
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS datasets (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            original_filename TEXT NOT NULL,
            file_type TEXT NOT NULL,
            tables_json TEXT NOT NULL,
            row_count INTEGER,
            size_bytes INTEGER,
            uploaded_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS query_history (
            id TEXT PRIMARY KEY,
            user_id TEXT,
            dataset_id TEXT,
            natural_language TEXT NOT NULL,
            generated_sql TEXT NOT NULL,
            is_valid INTEGER DEFAULT 1,
            execution_time_ms INTEGER,
            row_count INTEGER,
            error_message TEXT,
            is_favorite INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS dashboards (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT,
            config_json TEXT NOT NULL,
            created_by TEXT,
            is_public INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saved_queries (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            natural_language TEXT,
            sql_query TEXT NOT NULL,
            dataset_id TEXT,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Create default admin user
    import hashlib
    default_pw = hashlib.sha256("admin123".encode()).hexdigest()
    cur.execute("""
        INSERT OR IGNORE INTO users (username, email, hashed_password, role)
        VALUES ('admin', 'admin@analytics.local', ?, 'admin')
    """, (default_pw,))

    conn.commit()
    conn.close()


def _init_duckdb():
    """Initialize DuckDB with extensions."""
    try:
        conn = get_duckdb_connection()
        conn.execute("INSTALL httpfs")
        conn.execute("LOAD httpfs")
        conn.close()
    except Exception as e:
        logger.warning(f"Could not load DuckDB extensions: {e}")

"""SQLite persistent storage layer with FTS5 search capability."""

import sqlite3
import os
from contextlib import contextmanager
from typing import Generator
from app.core.config import settings


def get_db_path() -> str:
    """Return database file path."""
    return settings.database_path


def init_db(db_path: str | None = None) -> None:
    """Initialize SQLite tables and FTS5 search indexes."""
    path = db_path or get_db_path()
    # Ensure directory exists if path has dirname
    dirname = os.path.dirname(path)
    if dirname:
        os.makedirs(dirname, exist_ok=True)

    with sqlite3.connect(path) as conn:
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA foreign_keys=ON;")

        # Sessions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                platform TEXT NOT NULL,
                working_dir TEXT NOT NULL,
                os_name TEXT NOT NULL,
                quiet_mode INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
        """)

        # Executions table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS executions (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                command TEXT NOT NULL,
                exit_code INTEGER,
                duration_ms REAL NOT NULL,
                raw_bytes INTEGER NOT NULL,
                raw_tokens INTEGER NOT NULL,
                compact_bytes INTEGER NOT NULL,
                compact_tokens INTEGER NOT NULL,
                savings_ratio REAL NOT NULL,
                status TEXT NOT NULL,
                error TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions (id) ON DELETE CASCADE
            );
        """)

        # Execution chunks table for segmented retrieval
        conn.execute("""
            CREATE TABLE IF NOT EXISTS execution_chunks (
                id TEXT PRIMARY KEY,
                execution_id TEXT NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_type TEXT NOT NULL,
                content TEXT NOT NULL,
                byte_size INTEGER NOT NULL,
                token_count INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY (execution_id) REFERENCES executions (id) ON DELETE CASCADE
            );
        """)

        # FTS5 virtual table for full-text query
        conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                chunk_id UNINDEXED,
                execution_id UNINDEXED,
                content,
                tokenize = 'porter unicode61'
            );
        """)

        # Audit logs table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id TEXT PRIMARY KEY,
                user_email TEXT NOT NULL,
                action TEXT NOT NULL,
                resource_type TEXT NOT NULL,
                resource_id TEXT NOT NULL,
                details_json TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
        """)
        conn.commit()


@contextmanager
def get_db(db_path: str | None = None) -> Generator[sqlite3.Connection, None, None]:
    """Context manager providing a SQLite connection with Row factory."""
    path = db_path or get_db_path()
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON;")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

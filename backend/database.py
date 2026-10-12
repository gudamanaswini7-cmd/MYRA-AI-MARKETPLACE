"""Database access for local SQLite development and managed PostgreSQL hosting.

Set DATABASE_URL to a PostgreSQL connection string in production (for example,
from Neon or Supabase). Without DATABASE_URL, the app uses local SQLite.
"""
import os
import sqlite3
from pathlib import Path
from urllib.parse import urlparse

BACKEND_DIR = Path(__file__).resolve().parent
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()
USE_POSTGRES = DATABASE_URL.startswith(("postgres://", "postgresql://"))


def get_connection():
    if USE_POSTGRES:
        try:
            import psycopg
            from psycopg.rows import dict_row
        except ImportError as exc:
            raise RuntimeError(
                "PostgreSQL is configured but psycopg is not installed. "
                "Install dependencies from requirements.txt."
            ) from exc
        return psycopg.connect(DATABASE_URL, row_factory=dict_row, connect_timeout=10)

    if os.environ.get("VERCEL") == "1":
        db_path = Path(os.environ.get("DATABASE_PATH", "/tmp/marketplace_challenge.db"))
    else:
        db_path = Path(os.environ.get("DATABASE_PATH", str(BACKEND_DIR / "marketplace_challenge.db")))
    db_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    if USE_POSTGRES:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS creator_uploads (
                id BIGSERIAL PRIMARY KEY,
                creator_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                status TEXT NOT NULL,
                allowed_to_dashboard INTEGER NOT NULL DEFAULT 0,
                timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
            )
        """
    else:
        create_table_sql = """
            CREATE TABLE IF NOT EXISTS creator_uploads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                creator_name TEXT NOT NULL,
                file_name TEXT NOT NULL,
                file_type TEXT NOT NULL,
                score INTEGER NOT NULL,
                status TEXT NOT NULL,
                allowed_to_dashboard INTEGER NOT NULL DEFAULT 0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """
    with get_connection() as connection:
        connection.execute(create_table_sql)


def save_creator_upload(creator_name, file_name, file_type, score, status, allowed_to_dashboard):
    placeholder = "%s" if USE_POSTGRES else "?"
    query = f"""INSERT INTO creator_uploads
        (creator_name, file_name, file_type, score, status, allowed_to_dashboard)
        VALUES ({placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder}, {placeholder})"""
    with get_connection() as connection:
        connection.execute(
            query,
            (creator_name, file_name, file_type, score, status, int(allowed_to_dashboard)),
        )

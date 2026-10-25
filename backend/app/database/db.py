"""Tiny SQLite helper (standard library only, no ORM).

The database file lives in the storage folder (git-ignored). A fresh connection is opened
per operation: simple, thread-safe for FastAPI's worker threads, and fine at this scale.
Tables are created on first use, so there is no separate migration step.
"""

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from app.core.config import get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS brand_kit (
    id          INTEGER PRIMARY KEY CHECK (id = 1),   -- a single row: one brand per install
    brand_name  TEXT NOT NULL DEFAULT '',
    background  TEXT NOT NULL,
    text_color  TEXT NOT NULL,
    accent      TEXT NOT NULL,
    font        TEXT NOT NULL,
    tone        TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    product_name TEXT NOT NULL,
    photo_ext    TEXT NOT NULL,
    state        TEXT NOT NULL,                        -- JSON: details, copy, graphic settings...
    created_at   TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL,
    email         TEXT NOT NULL UNIQUE,                -- stored lower-case
    password_hash TEXT NOT NULL,                       -- scrypt, never the plain password
    created_at    TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,                       -- SHA-256 of the token; the token itself is never stored
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_tokens (
    token_hash TEXT PRIMARY KEY,                       -- SHA-256 of the emailed token
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose    TEXT NOT NULL,                          -- 'verify' or 'reset'
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Upgrade databases created by an earlier version (CREATE TABLE IF NOT EXISTS never alters tables)."""
    columns = {row["name"] for row in conn.execute("PRAGMA table_info(users)")}
    if "email_verified" not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN email_verified INTEGER NOT NULL DEFAULT 0")
        # Accounts created before verification existed are treated as already verified,
        # so nobody is locked out by upgrading.
        conn.execute("UPDATE users SET email_verified = 1")


def db_path() -> Path:
    folder = get_settings().storage_path
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "zorvi.db"


@contextmanager
def connect() -> Iterator[sqlite3.Connection]:
    """Open the database, make sure the tables exist, commit on success, roll back on error."""
    conn = sqlite3.connect(db_path())
    conn.row_factory = sqlite3.Row
    try:
        conn.executescript(SCHEMA)
        _migrate(conn)
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

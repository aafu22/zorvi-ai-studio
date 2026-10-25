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
"""


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
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

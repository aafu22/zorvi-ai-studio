"""Database helper (no ORM).

Two modes, chosen by the DATABASE_URL setting:
- empty (default): a SQLite file in the storage folder. Simple, and fine for running on your own computer.
- a postgresql:// address: PostgreSQL (for example a free Neon database). Use this on hosts whose disk is
  wiped on restart (Render's free plan), otherwise accounts and saved data disappear.

Both modes give the services the same small interface: ``with connect() as db:`` then
``db.execute("... ? ...", (values,))`` with ``.fetchone()`` / ``.fetchall()``, and rows that can be read by
column name (``row["email"]``) or position (``row[0]``). Write SQL with ``?`` placeholders; they are converted
for PostgreSQL. A fresh connection is opened per operation and committed on success, rolled back on error.
"""

import sqlite3
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings

SCHEMA = """
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

CREATE TABLE IF NOT EXISTS brand_kits (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,   -- one brand per account
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
    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,   -- owner; NULL = saved before accounts owned data
    name         TEXT NOT NULL,
    product_name TEXT NOT NULL,
    photo_ext    TEXT NOT NULL,
    state        TEXT NOT NULL,                        -- JSON: details, copy, graphic settings...
    created_at   TEXT NOT NULL
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
    campaign_columns = {row["name"] for row in conn.execute("PRAGMA table_info(campaigns)")}
    if "user_id" not in campaign_columns:
        # Projects saved before accounts owned data have no owner, so nobody can see them any more.
        conn.execute("ALTER TABLE campaigns ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE CASCADE")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id)")


PG_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id             SERIAL PRIMARY KEY,
    name           TEXT NOT NULL,
    email          TEXT NOT NULL UNIQUE,
    password_hash  TEXT NOT NULL,
    created_at     TEXT NOT NULL,
    email_verified INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS email_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    purpose    TEXT NOT NULL,
    created_at TEXT NOT NULL,
    expires_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS brand_kits (
    user_id     INTEGER PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    brand_name  TEXT NOT NULL DEFAULT '',
    background  TEXT NOT NULL,
    text_color  TEXT NOT NULL,
    accent      TEXT NOT NULL,
    font        TEXT NOT NULL,
    tone        TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id           SERIAL PRIMARY KEY,
    user_id      INTEGER REFERENCES users(id) ON DELETE CASCADE,
    name         TEXT NOT NULL,
    product_name TEXT NOT NULL,
    photo_ext    TEXT NOT NULL,
    state        TEXT NOT NULL,
    created_at   TEXT NOT NULL
);

-- Databases created before projects had owners: add the column (those older projects stay hidden).
ALTER TABLE campaigns ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES users(id) ON DELETE CASCADE;
CREATE INDEX IF NOT EXISTS idx_campaigns_user ON campaigns(user_id);
"""


# ----------------------------------------------------------------------------- helpers shared by both modes


def database_url() -> str:
    return get_settings().database_url.strip()


def is_postgres() -> bool:
    return bool(database_url())


def describe_database() -> str:
    """Human-readable location for logs. Never includes the password."""
    url = database_url()
    if url:
        return f"PostgreSQL at {urlparse(url).hostname or 'unknown host'}"
    return f"SQLite file {db_path()}"


def db_path() -> Path:
    folder = get_settings().storage_path
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "zorvi.db"


# ----------------------------------------------------------------------------- SQLite mode


@contextmanager
def _connect_sqlite() -> Iterator[sqlite3.Connection]:
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


# ----------------------------------------------------------------------------- PostgreSQL mode


def to_pg_sql(sql: str) -> str:
    """Convert '?' placeholders to psycopg's '%s' (and protect any literal percent sign)."""
    return sql.replace("%", "%%").replace("?", "%s")


class PgRow:
    """A result row readable by column name or by position, like sqlite3.Row."""

    __slots__ = ("_names", "_values")

    def __init__(self, names: list[str], values: tuple) -> None:
        self._names = names
        self._values = tuple(values)

    def __getitem__(self, key):
        if isinstance(key, str):
            try:
                return self._values[self._names.index(key)]
            except ValueError:
                raise IndexError(f"No column named {key!r}") from None
        return self._values[key]

    def keys(self) -> list[str]:
        return list(self._names)

    def __iter__(self):
        return iter(self._values)

    def __len__(self) -> int:
        return len(self._values)

    def __repr__(self) -> str:
        return f"PgRow({dict(zip(self._names, self._values))})"


class PgCursor:
    def __init__(self, cursor) -> None:
        self._cursor = cursor

    def _names(self) -> list[str]:
        description = self._cursor.description
        return [column.name for column in description] if description else []

    def fetchone(self):
        row = self._cursor.fetchone()
        return None if row is None else PgRow(self._names(), row)

    def fetchall(self) -> list[PgRow]:
        names = self._names()
        return [PgRow(names, row) for row in self._cursor.fetchall()]

    def __iter__(self):
        return iter(self.fetchall())

    @property
    def rowcount(self) -> int:
        return self._cursor.rowcount


class PgConnection:
    """Gives a psycopg connection the same ``execute(sql, params)`` shape the services use with SQLite."""

    def __init__(self, raw) -> None:
        self._raw = raw

    def execute(self, sql: str, params=()) -> PgCursor:
        cursor = self._raw.cursor()
        cursor.execute(to_pg_sql(sql), tuple(params))
        return PgCursor(cursor)


_pg_schema_ready: set[str] = set()
_pg_schema_lock = threading.Lock()


def _open_pg(url: str):
    try:
        import psycopg
    except ImportError as exc:
        raise RuntimeError(
            "DATABASE_URL is set but the 'psycopg' package is not installed. "
            "Run: pip install -r requirements.txt"
        ) from exc
    last: Exception | None = None
    for attempt in range(2):  # a sleeping hosted database can need a moment on the first connection
        try:
            return psycopg.connect(url, connect_timeout=10)
        except psycopg.OperationalError as exc:
            last = exc
            if attempt == 0:
                time.sleep(1.5)
    assert last is not None
    raise last


def _ensure_pg_schema(raw, url: str) -> None:
    """Create the tables once per server process (not on every request)."""
    if url in _pg_schema_ready:
        return
    with _pg_schema_lock:
        if url in _pg_schema_ready:
            return
        cursor = raw.cursor()
        cursor.execute("SELECT pg_advisory_xact_lock(7274201)")  # two workers starting together must not race
        cursor.execute(PG_SCHEMA)
        raw.commit()
        _pg_schema_ready.add(url)


@contextmanager
def _connect_pg() -> Iterator[PgConnection]:
    url = database_url()
    raw = _open_pg(url)
    try:
        _ensure_pg_schema(raw, url)
        yield PgConnection(raw)
        raw.commit()
    except Exception:
        raw.rollback()
        raise
    finally:
        raw.close()


# ----------------------------------------------------------------------------- public entry point


@contextmanager
def connect() -> Iterator:
    """Open the configured database for one operation (see the module docstring)."""
    manager = _connect_pg() if is_postgres() else _connect_sqlite()
    with manager as conn:
        yield conn

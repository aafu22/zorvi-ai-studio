import pytest

from app.database import db as dbmod


def test_placeholders_are_converted_for_postgres():
    assert dbmod.to_pg_sql("SELECT * FROM t WHERE a = ? AND b = ?") == "SELECT * FROM t WHERE a = %s AND b = %s"


def test_literal_percent_is_protected():
    assert dbmod.to_pg_sql("SELECT '100%' WHERE a = ?") == "SELECT '100%%' WHERE a = %s"


def test_pg_row_reads_by_name_and_position():
    row = dbmod.PgRow(["id", "name"], (7, "Asha"))
    assert row["id"] == 7 and row["name"] == "Asha"
    assert row[0] == 7 and row[1] == "Asha"
    assert len(row) == 2 and list(row) == [7, "Asha"]
    assert dict(row) == {"id": 7, "name": "Asha"}
    assert row  # a one-column row is still "truthy", like sqlite3.Row


def test_pg_row_unknown_column_is_an_error():
    with pytest.raises(IndexError):
        dbmod.PgRow(["id"], (1,))["missing"]


def test_sqlite_is_the_default(storage_env):
    assert dbmod.is_postgres() is False
    assert "SQLite" in dbmod.describe_database()


def test_describe_database_hides_the_password(monkeypatch):
    from app.core.config import get_settings

    monkeypatch.setenv("DATABASE_URL", "postgresql://user:secret-pass@ep-example.neon.tech/neondb?sslmode=require")
    get_settings.cache_clear()
    try:
        text = dbmod.describe_database()
        assert "ep-example.neon.tech" in text
        assert "secret-pass" not in text and "user" not in text
    finally:
        get_settings.cache_clear()


def test_insert_returning_id_works_on_sqlite(storage_env):
    """The services use 'RETURNING id' instead of lastrowid so one query works on both databases."""
    with dbmod.connect() as db:
        cur = db.execute(
            "INSERT INTO campaigns (name, product_name, photo_ext, state, created_at) "
            "VALUES (?, ?, ?, ?, ?) RETURNING id",
            ("n", "p", "jpg", "{}", "now"),
        )
        first = cur.fetchone()["id"]
        cur = db.execute(
            "INSERT INTO campaigns (name, product_name, photo_ext, state, created_at) "
            "VALUES (?, ?, ?, ?, ?) RETURNING id",
            ("n2", "p2", "jpg", "{}", "now"),
        )
        assert cur.fetchone()["id"] == first + 1

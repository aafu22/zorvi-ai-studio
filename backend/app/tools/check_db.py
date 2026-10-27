"""Check which database the backend uses and that it really works.

Run from the backend folder (with your virtual environment active):

    python -m app.tools.check_db

It reads DATABASE_URL from backend/.env. If that is empty it checks the local SQLite file instead.
It only creates the tables and writes to a throw-away TEMP table, so your accounts and data are untouched.
The password is never printed.
"""

import sys
from urllib.parse import unquote, urlparse

from app.core.config import get_settings
from app.database.db import connect, describe_database, is_postgres


def _mask(text: str) -> str:
    """Remove the database password from an error message, in case the driver includes the address."""
    url = get_settings().database_url.strip()
    password = unquote(urlparse(url).password or "") if url else ""
    return text.replace(password, "****") if password else text


def main() -> None:
    print(f"Database: {describe_database()}")
    if not is_postgres():
        print("DATABASE_URL is empty, so the local SQLite file is used.")
        print("(On Render's free plan that file is deleted on restart. Set DATABASE_URL to keep your data.)")
    try:
        with connect() as db:
            print("1. Connected and the tables exist.")
            db.execute("CREATE TEMP TABLE zorvi_check (id INTEGER, note TEXT)")
            db.execute("INSERT INTO zorvi_check (id, note) VALUES (?, ?)", (1, "100% works?"))
            row = db.execute("SELECT id, note FROM zorvi_check WHERE id = ?", (1,)).fetchone()
            assert row is not None and row["note"] == "100% works?" and row[0] == 1
            print("2. Wrote and read back a test row.")
            users = db.execute("SELECT COUNT(*) FROM users").fetchone()[0]
            print(f"3. Accounts currently stored: {users}")
    except Exception as e:
        print(f"\n  FAILED: {type(e).__name__}: {_mask(str(e))}")
        text = str(e).lower()
        if "psycopg" in text and "not installed" in text:
            print("  What to check: run  pip install -r requirements.txt  and try again.")
        elif "password authentication" in text or "authentication failed" in text:
            print("  What to check: the user name or password in DATABASE_URL is wrong. Copy it again from Neon.")
        elif "ssl" in text:
            print("  What to check: the address must end with  ?sslmode=require  (Neon includes it).")
        elif "could not translate host" in text or "name or service not known" in text or "getaddrinfo" in text:
            print("  What to check: the host name in DATABASE_URL is wrong or you are offline.")
        elif "timeout" in text or "timed out" in text or "refused" in text:
            print("  What to check: the database could not be reached. Check your internet or firewall, and that the Neon project is active.")
        else:
            print("  What to check: DATABASE_URL should look like  postgresql://USER:PASSWORD@HOST/DBNAME?sslmode=require")
        sys.exit(1)
    print("\n  SUCCESS: the database works.")


if __name__ == "__main__":
    main()

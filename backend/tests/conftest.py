import os

# The tests must NEVER use your real settings. backend/.env may hold a PostgreSQL address (Neon), real email
# and AI keys, so without this the tests would create accounts in your real database, send real emails and
# call the real AI. Real environment variables beat backend/.env, so setting them here (before anything from
# the app is imported) gives every test the plain defaults: a throw-away SQLite file, no email, no AI key.
for _name, _value in {
    "DATABASE_URL": "",
    "GEMINI_API_KEY": "",
    "SMTP_HOST": "",
    "BREVO_API_KEY": "",
    "BREVO_SENDER_EMAIL": "",
    "APP_ENV": "development",
    "FORCE_HTTPS": "false",
    "FRONTEND_URL": "http://localhost:3000",
    "CORS_ORIGINS": "http://localhost:3000,http://127.0.0.1:3000",
    "REQUIRE_EMAIL_VERIFICATION": "true",
    "SAMPLE_ASSETS_DIR": "",
    "FILE_TTL_HOURS": "24",
    "AI_REQUESTS_PER_MINUTE": "5",
    "AI_REQUESTS_PER_HOUR": "30",
    "AI_DAILY_LIMIT_TOTAL": "500",
}.items():
    os.environ[_name] = _value

import pytest  # noqa: E402  (must come after the environment is set up)

from app.core.config import get_settings  # noqa: E402
from app.services.storage_service import get_storage  # noqa: E402


@pytest.fixture(autouse=True)
def _never_touch_a_real_database():
    """Fail loudly, before any data is written, if a test could reach PostgreSQL."""
    get_settings.cache_clear()
    from app.database.db import is_postgres

    assert not is_postgres(), "A test is pointed at PostgreSQL. Tests must only use their own SQLite file."
    yield


@pytest.fixture
def storage_env(tmp_path, monkeypatch):
    """Point all storage (uploads, SQLite database, logo, saved projects) at a throw-away folder."""
    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    monkeypatch.setenv("MAX_UPLOAD_MB", "1")
    get_settings.cache_clear()
    get_storage.cache_clear()
    yield tmp_path
    get_settings.cache_clear()
    get_storage.cache_clear()


@pytest.fixture
def client(storage_env):
    """A test client whose data goes to a throw-away folder with a 1 MB upload limit."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def _fresh_rate_limits():
    """Every test starts with an empty AI usage count."""
    from app.core import rate_limit

    rate_limit.reset()
    yield
    rate_limit.reset()


@pytest.fixture
def signup_user(client, monkeypatch):
    """A function that creates a signed-in account and returns its Authorization header.

    Email verification is switched off so sign-up returns a session straight away.
    Call it twice with different emails to get two separate users.
    """
    from app.core.config import get_settings
    from app.services import auth_service

    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    get_settings.cache_clear()
    auth_service._failures.clear()
    auth_service._email_requests.clear()

    def make(email: str = "asha@example.com", name: str = "Asha") -> dict[str, str]:
        r = client.post("/api/auth/signup", json={"name": name, "email": email, "password": "correct horse"})
        assert r.status_code == 201, r.text
        return {"Authorization": f"Bearer {r.json()['token']}"}

    return make


@pytest.fixture
def auth_headers(signup_user):
    """Authorization header of one signed-in user."""
    return signup_user()

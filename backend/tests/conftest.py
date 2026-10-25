import pytest

from app.core.config import get_settings
from app.services.storage_service import get_storage


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

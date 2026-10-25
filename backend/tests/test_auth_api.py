import pytest

from app.services import auth_service

SIGNUP = {"name": "Asha", "email": "Asha@Example.com", "password": "correct horse"}


@pytest.fixture(autouse=True)
def _basic_auth_settings(monkeypatch):
    """These tests cover plain sign up / login, so email verification is switched off here.
    The verification and reset flows are tested in test_auth_email_flows.py."""
    from app.core.config import get_settings
    from app.services import email_service

    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "false")
    monkeypatch.setattr(email_service, "send_email", lambda *a, **k: None)
    get_settings.cache_clear()
    auth_service._failures.clear()
    auth_service._email_requests.clear()
    yield
    auth_service._failures.clear()
    auth_service._email_requests.clear()
    get_settings.cache_clear()


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_signup_then_me(client):
    r = client.post("/api/auth/signup", json=SIGNUP)
    assert r.status_code == 201
    body = r.json()
    assert body["user"]["email"] == "asha@example.com"  # normalised to lower-case
    assert "password" not in str(body)

    me = client.get("/api/auth/me", headers=_auth(body["token"]))
    assert me.status_code == 200
    assert me.json()["name"] == "Asha"


def test_signup_duplicate_email_rejected(client):
    assert client.post("/api/auth/signup", json=SIGNUP).status_code == 201
    r = client.post("/api/auth/signup", json={**SIGNUP, "email": "asha@example.com"})
    assert r.status_code == 409


def test_signup_validation(client):
    assert client.post("/api/auth/signup", json={**SIGNUP, "password": "short"}).status_code == 422
    assert client.post("/api/auth/signup", json={**SIGNUP, "email": "not-an-email"}).status_code == 422
    assert client.post("/api/auth/signup", json={**SIGNUP, "name": "   "}).status_code == 422


def test_login_success_and_failure(client):
    client.post("/api/auth/signup", json=SIGNUP)
    ok = client.post("/api/auth/login", json={"email": "ASHA@example.com", "password": SIGNUP["password"]})
    assert ok.status_code == 200
    assert ok.json()["token"]

    bad = client.post("/api/auth/login", json={"email": "asha@example.com", "password": "wrong password"})
    assert bad.status_code == 401
    unknown = client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "whatever1"})
    assert unknown.status_code == 401
    assert bad.json()["detail"] == unknown.json()["detail"]  # does not reveal which emails exist


def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_auth("garbage")).status_code == 401


def test_logout_invalidates_token(client):
    token = client.post("/api/auth/signup", json=SIGNUP).json()["token"]
    assert client.post("/api/auth/logout", headers=_auth(token)).status_code == 204
    assert client.get("/api/auth/me", headers=_auth(token)).status_code == 401


def test_password_is_hashed_in_database(client):
    from app.database.db import connect

    client.post("/api/auth/signup", json=SIGNUP)
    with connect() as conn:
        stored = conn.execute("SELECT password_hash FROM users").fetchone()["password_hash"]
    assert SIGNUP["password"] not in stored
    assert stored.startswith("scrypt$")


def test_too_many_failed_logins_are_throttled(client):
    client.post("/api/auth/signup", json=SIGNUP)
    for _ in range(auth_service.MAX_FAILURES):
        client.post("/api/auth/login", json={"email": "asha@example.com", "password": "nope nope"})
    locked = client.post("/api/auth/login", json={"email": "asha@example.com", "password": SIGNUP["password"]})
    assert locked.status_code == 429

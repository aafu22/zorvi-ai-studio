import re

import pytest

from app.services import auth_service, email_service

USER = {"name": "Asha", "email": "asha@example.com", "password": "correct horse"}


@pytest.fixture
def mailbox(monkeypatch):
    """Require verification and capture outgoing emails instead of sending them."""
    from app.core.config import get_settings

    monkeypatch.setenv("REQUIRE_EMAIL_VERIFICATION", "true")
    monkeypatch.setenv("FRONTEND_URL", "https://zorvi.test")
    get_settings.cache_clear()
    auth_service._failures.clear()
    auth_service._email_requests.clear()
    sent: list[dict] = []
    monkeypatch.setattr(
        email_service, "send_email", lambda to, subject, body: sent.append({"to": to, "subject": subject, "body": body})
    )
    yield sent
    auth_service._failures.clear()
    auth_service._email_requests.clear()
    get_settings.cache_clear()


def _token_from(mail: dict, page: str) -> str:
    match = re.search(rf"https://zorvi\.test/{page}\?token=([\w\-]+)", mail["body"])
    assert match, mail["body"]
    return match.group(1)


def _login(client, password=USER["password"]):
    return client.post("/api/auth/login", json={"email": USER["email"], "password": password})


def test_signup_requires_verification_before_login(client, mailbox):
    r = client.post("/api/auth/signup", json=USER)
    assert r.status_code == 201
    body = r.json()
    assert body["verification_required"] is True
    assert body["token"] is None
    assert len(mailbox) == 1 and mailbox[0]["to"] == USER["email"]

    blocked = _login(client)
    assert blocked.status_code == 403
    assert "verify" in blocked.json()["detail"].lower()


def test_wrong_password_is_not_told_to_verify(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    assert _login(client, "totally wrong").status_code == 401  # not 403: no hint that the account exists


def test_verify_email_then_login(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    token = _token_from(mailbox[0], "verify-email")

    r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 200

    ok = _login(client)
    assert ok.status_code == 200
    assert ok.json()["user"]["email_verified"] is True


def test_verification_link_is_single_use(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    token = _token_from(mailbox[0], "verify-email")
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 200
    assert client.post("/api/auth/verify-email", json={"token": token}).status_code == 400


def test_invalid_verification_token(client, mailbox):
    assert client.post("/api/auth/verify-email", json={"token": "x" * 40}).status_code == 400


def test_expired_verification_token(client, mailbox):
    from app.database.db import connect

    client.post("/api/auth/signup", json=USER)
    token = _token_from(mailbox[0], "verify-email")
    with connect() as conn:
        conn.execute("UPDATE email_tokens SET expires_at = '2000-01-01T00:00:00+00:00'")
    r = client.post("/api/auth/verify-email", json={"token": token})
    assert r.status_code == 400
    assert "expired" in r.json()["detail"].lower()


def test_resend_verification_invalidates_older_link(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    first = _token_from(mailbox[0], "verify-email")
    r = client.post("/api/auth/resend-verification", json={"email": USER["email"]})
    assert r.status_code == 200
    assert len(mailbox) == 2
    second = _token_from(mailbox[1], "verify-email")
    assert first != second
    assert client.post("/api/auth/verify-email", json={"token": first}).status_code == 400
    assert client.post("/api/auth/verify-email", json={"token": second}).status_code == 200


def test_resend_does_not_reveal_unknown_emails(client, mailbox):
    known = client.post("/api/auth/resend-verification", json={"email": "nobody@example.com"})
    assert known.status_code == 200
    assert known.json()["message"] == auth_service.GENERIC_VERIFY_MESSAGE
    assert mailbox == []


def test_forgot_password_sends_link_and_hides_unknown_emails(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    mailbox.clear()

    unknown = client.post("/api/auth/forgot-password", json={"email": "nobody@example.com"})
    known = client.post("/api/auth/forgot-password", json={"email": USER["email"]})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json() == known.json()  # identical answer either way
    assert len(mailbox) == 1 and mailbox[0]["to"] == USER["email"]


def test_reset_password_flow(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    client.post("/api/auth/verify-email", json={"token": _token_from(mailbox[0], "verify-email")})
    old_session = _login(client).json()["token"]

    client.post("/api/auth/forgot-password", json={"email": USER["email"]})
    token = _token_from(mailbox[-1], "reset-password")
    r = client.post("/api/auth/reset-password", json={"token": token, "password": "brand new pass"})
    assert r.status_code == 200

    assert _login(client).status_code == 401  # old password no longer works
    assert _login(client, "brand new pass").status_code == 200
    # every session that existed before the reset was signed out
    assert client.get("/api/auth/me", headers={"Authorization": f"Bearer {old_session}"}).status_code == 401
    # the link cannot be used twice
    again = client.post("/api/auth/reset-password", json={"token": token, "password": "another pass 1"})
    assert again.status_code == 400


def test_reset_validates_new_password_and_token(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    client.post("/api/auth/forgot-password", json={"email": USER["email"]})
    token = _token_from(mailbox[-1], "reset-password")
    assert client.post("/api/auth/reset-password", json={"token": token, "password": "short"}).status_code == 422
    assert client.post("/api/auth/reset-password", json={"token": "y" * 40, "password": "long enough pw"}).status_code == 400
    # a verification link cannot be used to reset a password
    verify_token = _token_from(mailbox[0], "verify-email")
    assert client.post("/api/auth/reset-password", json={"token": verify_token, "password": "long enough pw"}).status_code == 400


def test_reset_also_verifies_email(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    client.post("/api/auth/forgot-password", json={"email": USER["email"]})
    token = _token_from(mailbox[-1], "reset-password")
    client.post("/api/auth/reset-password", json={"token": token, "password": "brand new pass"})
    assert _login(client, "brand new pass").status_code == 200


def test_email_requests_are_throttled(client, mailbox):
    client.post("/api/auth/signup", json=USER)
    mailbox.clear()
    for _ in range(auth_service.MAX_EMAILS + 3):
        client.post("/api/auth/forgot-password", json={"email": USER["email"]})
    assert len(mailbox) < auth_service.MAX_EMAILS + 3  # extra requests were silently dropped


def test_tokens_are_stored_hashed(client, mailbox):
    from app.database.db import connect

    client.post("/api/auth/signup", json=USER)
    token = _token_from(mailbox[0], "verify-email")
    with connect() as conn:
        stored = conn.execute("SELECT token_hash FROM email_tokens").fetchone()["token_hash"]
    assert token not in stored


def test_old_database_is_upgraded(tmp_path, monkeypatch):
    """A users table made by the earlier version (no email_verified column) is upgraded, and existing
    accounts count as verified so nobody is locked out."""
    import sqlite3

    from app.core.config import get_settings

    monkeypatch.setenv("STORAGE_DIR", str(tmp_path / "storage"))
    get_settings.cache_clear()
    (tmp_path / "storage").mkdir()
    old = sqlite3.connect(tmp_path / "storage" / "zorvi.db")
    old.execute(
        "CREATE TABLE users (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, "
        "email TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, created_at TEXT NOT NULL)"
    )
    old.execute("INSERT INTO users (name, email, password_hash, created_at) VALUES ('Old', 'old@example.com', 'x', 'now')")
    old.commit()
    old.close()

    from app.database.db import connect

    with connect() as conn:
        assert conn.execute("SELECT email_verified FROM users").fetchone()["email_verified"] == 1
    get_settings.cache_clear()

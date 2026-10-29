"""Who may call what: sign-in on private routes, per-account data, AI rate limits, and the database upgrade."""

import io
import sqlite3
import types

import pytest
from PIL import Image

from app.core import rate_limit
from app.core.config import get_settings
from app.core.errors import AppError
from app.database import db as dbmod
from app.services import history_service
from app.services.marketing import marketing_service as svc
from tests.test_marketing_service import GOOD, FakeClient

BRAND = {"brand_name": "Luna", "colors": {"background": "#000000", "text": "#ffffff", "accent": "#ff00aa"},
         "font": "serif", "tone": "luxury"}
AI_BODY = {"product_name": "Rose Ring", "description": "Sterling silver ring with a rose quartz stone."}


def png(size=(120, 80), color="orange") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def upload(client) -> dict:
    r = client.post("/api/images/upload", files={"file": ("p.png", png(), "image/png")})
    assert r.status_code == 201
    return r.json()


def save_project(client, headers, name="Launch") -> int:
    image = upload(client)
    r = client.post("/api/history", headers=headers,
                    json={"image_id": image["id"], "name": name, "product_name": "Ring", "state": {}})
    assert r.status_code == 201, r.text
    return r.json()["id"]


# ------------------------------------------------------------ private routes need sign-in

PRIVATE_ROUTES = [
    ("get", "/api/history"),
    ("post", "/api/history"),
    ("post", "/api/history/1/open"),
    ("get", "/api/history/1/thumbnail"),
    ("get", "/api/history/1/photo"),
    ("delete", "/api/history/1"),
    ("get", "/api/brand-kit"),
    ("put", "/api/brand-kit"),
    ("delete", "/api/brand-kit"),
    ("post", "/api/brand-kit/logo"),
    ("get", "/api/brand-kit/logo"),
    ("delete", "/api/brand-kit/logo"),
    ("post", "/api/marketing/generate"),
    ("post", "/api/photo-assistant/analyze"),
]


@pytest.mark.parametrize("method,path", PRIVATE_ROUTES)
def test_private_routes_reject_signed_out_visitors(client, method, path):
    assert getattr(client, method)(path).status_code == 401
    bad = getattr(client, method)(path, headers={"Authorization": "Bearer not-a-real-token"})
    assert bad.status_code == 401


def test_open_features_still_work_without_an_account(client):
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/graphics/options").status_code == 200
    image = upload(client)
    assert client.post("/api/graphics/render", json={"image_id": image["id"], "headline": "Hi"}).status_code == 200
    assert client.post("/api/marketing/template", json=AI_BODY).status_code == 200
    assert client.post("/api/copy/generate", json={"product_name": "Soy Candle"}).status_code == 200
    assert client.post("/api/demo/start").status_code == 200


def test_logging_out_ends_access(client, auth_headers):
    assert client.get("/api/history", headers=auth_headers).status_code == 200
    assert client.post("/api/auth/logout", headers=auth_headers).status_code == 204
    assert client.get("/api/history", headers=auth_headers).status_code == 401


# ------------------------------------------------------------ one account cannot see another's data


def test_history_is_private_per_account(client, signup_user):
    alice = signup_user("alice@example.com", "Alice")
    bob = signup_user("bob@example.com", "Bob")
    cid = save_project(client, alice)

    assert client.get("/api/history", headers=bob).json() == []
    assert client.get(f"/api/history/{cid}/thumbnail", headers=bob).status_code == 404
    assert client.get(f"/api/history/{cid}/photo", headers=bob).status_code == 404
    assert client.post(f"/api/history/{cid}/open", headers=bob).status_code == 404
    assert client.delete(f"/api/history/{cid}", headers=bob).status_code == 404

    assert [c["id"] for c in client.get("/api/history", headers=alice).json()] == [cid]  # untouched
    assert client.get(f"/api/history/{cid}/photo", headers=alice).status_code == 200


def test_brand_kit_is_private_per_account(client, signup_user):
    alice = signup_user("alice@example.com", "Alice")
    bob = signup_user("bob@example.com", "Bob")
    assert client.put("/api/brand-kit", json=BRAND, headers=alice).status_code == 200
    client.post("/api/brand-kit/logo", files={"file": ("l.png", png(), "image/png")}, headers=alice)

    seen_by_bob = client.get("/api/brand-kit", headers=bob).json()
    assert seen_by_bob["configured"] is False and seen_by_bob["has_logo"] is False
    assert client.get("/api/brand-kit/logo", headers=bob).status_code == 404

    client.delete("/api/brand-kit", headers=bob)  # Bob resetting his own kit must not touch Alice's
    seen_by_alice = client.get("/api/brand-kit", headers=alice).json()
    assert seen_by_alice["brand_name"] == "Luna" and seen_by_alice["has_logo"] is True


# ------------------------------------------------------------ AI endpoints: sign-in + rate limits


def _use_fake_model(monkeypatch):
    monkeypatch.setattr(svc, "default_client", lambda: FakeClient(GOOD))


def _set_limits(monkeypatch, **env):
    for key, value in env.items():
        monkeypatch.setenv(key, str(value))
    get_settings.cache_clear()


def test_photo_assistant_needs_sign_in_then_a_key(client, auth_headers, monkeypatch):
    files = {"file": ("p.png", png(), "image/png")}
    assert client.post("/api/photo-assistant/analyze", files=files).status_code == 401
    monkeypatch.setenv("GEMINI_API_KEY", "")
    get_settings.cache_clear()
    r = client.post("/api/photo-assistant/analyze", files={"file": ("p.png", png(), "image/png")}, headers=auth_headers)
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]


def test_per_minute_limit_blocks_then_other_users_are_unaffected(client, signup_user, monkeypatch):
    _use_fake_model(monkeypatch)
    _set_limits(monkeypatch, AI_REQUESTS_PER_MINUTE=2)
    alice = signup_user("alice@example.com", "Alice")
    bob = signup_user("bob@example.com", "Bob")

    assert client.post("/api/marketing/generate", json=AI_BODY, headers=alice).status_code == 200
    assert client.post("/api/marketing/generate", json=AI_BODY, headers=alice).status_code == 200
    blocked = client.post("/api/marketing/generate", json=AI_BODY, headers=alice)
    assert blocked.status_code == 429 and "try again in" in blocked.json()["detail"]
    assert client.post("/api/marketing/generate", json=AI_BODY, headers=bob).status_code == 200


def test_template_drafts_are_not_rate_limited(client, auth_headers, monkeypatch):
    _set_limits(monkeypatch, AI_REQUESTS_PER_MINUTE=1)
    for _ in range(3):
        assert client.post("/api/marketing/template", json=AI_BODY, headers=auth_headers).status_code == 200


def test_daily_cap_covers_all_users(client, signup_user, monkeypatch):
    _use_fake_model(monkeypatch)
    _set_limits(monkeypatch, AI_DAILY_LIMIT_TOTAL=1)
    alice = signup_user("alice@example.com", "Alice")
    bob = signup_user("bob@example.com", "Bob")
    assert client.post("/api/marketing/generate", json=AI_BODY, headers=alice).status_code == 200
    r = client.post("/api/marketing/generate", json=AI_BODY, headers=bob)
    assert r.status_code == 429 and "daily" in r.json()["detail"]


# ------------------------------------------------------------ rate limiter on its own


def test_limit_window_slides_and_refused_requests_are_not_counted(storage_env, monkeypatch):
    _set_limits(monkeypatch, AI_REQUESTS_PER_MINUTE=1)
    now = [1000.0]
    monkeypatch.setattr(rate_limit, "time", types.SimpleNamespace(time=lambda: now[0]))

    rate_limit.check_ai_limit(7)
    now[0] = 1030.0
    with pytest.raises(AppError) as exc:
        rate_limit.check_ai_limit(7)
    assert exc.value.status_code == 429 and "30 seconds" in exc.value.detail
    now[0] = 1059.0
    with pytest.raises(AppError):
        rate_limit.check_ai_limit(7)  # the refusals above did not push the window forward
    now[0] = 1061.0
    rate_limit.check_ai_limit(7)  # a minute after the first counted request: allowed again


def test_hourly_limit(storage_env, monkeypatch):
    _set_limits(monkeypatch, AI_REQUESTS_PER_MINUTE=100, AI_REQUESTS_PER_HOUR=2)
    now = [5000.0]
    monkeypatch.setattr(rate_limit, "time", types.SimpleNamespace(time=lambda: now[0]))
    rate_limit.check_ai_limit(1)
    now[0] += 120
    rate_limit.check_ai_limit(1)
    now[0] += 120
    with pytest.raises(AppError) as exc:
        rate_limit.check_ai_limit(1)
    assert "hourly" in exc.value.detail
    now[0] += 3600
    rate_limit.check_ai_limit(1)


# ------------------------------------------------------------ upgrading an older database


def test_old_database_is_upgraded_and_old_projects_stay_hidden(storage_env):
    path = dbmod.db_path()
    old = sqlite3.connect(path)
    old.executescript(
        """
        CREATE TABLE campaigns (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, product_name TEXT NOT NULL,
            photo_ext TEXT NOT NULL, state TEXT NOT NULL, created_at TEXT NOT NULL);
        INSERT INTO campaigns (name, product_name, photo_ext, state, created_at)
            VALUES ('before accounts', 'Ring', 'png', '{}', '2026-01-01T00:00:00+00:00');
        """
    )
    old.commit()
    old.close()

    with dbmod.connect() as db:
        columns = {row["name"] for row in db.execute("PRAGMA table_info(campaigns)")}
        assert "user_id" in columns
        assert db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1  # nothing was deleted
        assert db.execute("SELECT COUNT(*) FROM brand_kits").fetchone()[0] == 0
    assert history_service.list_campaigns(1) == []  # unowned projects belong to no account
    with dbmod.connect() as db:  # connecting again must not fail or repeat the upgrade
        assert db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0] == 1

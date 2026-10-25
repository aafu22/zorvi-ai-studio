"""HTTP-level tests for /api/marketing (need FastAPI installed)."""

from app.services.marketing import marketing_service as svc
from tests.test_marketing_service import GOOD, FakeClient

BODY = {"product_name": "Rose Ring", "description": "Sterling silver ring with a rose quartz stone."}


def test_generate_validates_input(client):
    assert client.post("/api/marketing/generate", json={"product_name": ""}).status_code == 422
    assert client.post("/api/marketing/generate", json={**BODY, "tone": "angry"}).status_code == 422


def test_generate_without_key_returns_a_helpful_503(client, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "")
    from app.core.config import get_settings

    get_settings.cache_clear()
    r = client.post("/api/marketing/generate", json=BODY)
    assert r.status_code == 503 and "GEMINI_API_KEY" in r.json()["detail"]
    get_settings.cache_clear()


def test_generate_with_a_fake_model(client, monkeypatch):
    monkeypatch.setattr(svc, "default_client", lambda: FakeClient(GOOD))
    r = client.post("/api/marketing/generate", json=BODY)
    body = r.json()
    assert r.status_code == 200 and body["source"]["is_ai"] is True
    assert len(body["content"]["captions"]) == 3 and body["warnings"] == []


def test_template_endpoint_works_without_a_key(client):
    r = client.post("/api/marketing/template", json={**BODY, "tone": "playful"})
    assert r.status_code == 200 and r.json()["source"]["is_ai"] is False

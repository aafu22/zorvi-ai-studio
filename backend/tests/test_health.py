from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_ok():
    r = client.get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["app"] == "Zorvi AI Studio"
    assert set(body["capabilities"]) == {"llm_provider"}


def test_cors_allows_local_frontend():
    r = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert r.headers.get("access-control-allow-origin") == "http://localhost:3000"


def test_cors_blocks_unknown_origin():
    r = client.get("/api/health", headers={"Origin": "http://evil.example"})
    assert "access-control-allow-origin" not in r.headers

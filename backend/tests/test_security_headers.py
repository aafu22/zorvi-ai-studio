def test_security_headers_present(client):
    r = client.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert r.headers["referrer-policy"] == "no-referrer"


def test_auth_responses_are_not_cacheable(client):
    r = client.post("/api/auth/forgot-password", json={"email": "someone@example.com"})
    assert r.status_code == 200
    assert r.headers["cache-control"] == "no-store"

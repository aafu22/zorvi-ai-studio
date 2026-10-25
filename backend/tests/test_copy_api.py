def test_generate_copy_ok(client):
    r = client.post(
        "/api/copy/generate",
        json={"product_name": "Soy Candle", "category": "Candles & fragrance", "tone": "playful", "seed": 5},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["provider"]["is_ai"] is False
    assert len(body["captions"]) == 7
    assert body["hashtags"] and body["ctas"] and len(body["promos"]) == 3


def test_generate_copy_requires_product_name(client):
    assert client.post("/api/copy/generate", json={}).status_code == 422
    assert client.post("/api/copy/generate", json={"product_name": "  "}).status_code == 422


def test_generate_copy_rejects_bad_values(client):
    assert client.post("/api/copy/generate", json={"product_name": "x", "tone": "angry"}).status_code == 422
    assert client.post("/api/copy/generate", json={"product_name": "x", "provider": "llm"}).status_code == 422

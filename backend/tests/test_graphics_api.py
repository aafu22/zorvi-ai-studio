import io

from PIL import Image


def upload_png(client) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (300, 200), "orange").save(buf, format="PNG")
    r = client.post("/api/images/upload", files={"file": ("p.png", buf.getvalue(), "image/png")})
    return r.json()["id"]


def test_options_endpoint(client):
    body = client.get("/api/graphics/options").json()
    assert {t["id"] for t in body["templates"]} == {"classic", "overlay", "frame", "offer"}
    assert [s["id"] for s in body["sizes"]] == ["square", "portrait", "story"]
    assert [f["id"] for f in body["fonts"]] == ["sans", "serif", "display"]


def test_render_full_size_and_preview(client):
    image_id = upload_png(client)
    payload = {"image_id": image_id, "template": "offer", "size": "portrait", "headline": "Hello", "badge": "10% off"}
    full = client.post("/api/graphics/render", json=payload)
    assert full.status_code == 200 and full.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(full.content)).size == (1080, 1350)
    small = client.post("/api/graphics/render?preview=true", json=payload)
    assert Image.open(io.BytesIO(small.content)).size == (540, 675)


def test_render_unknown_image_is_404(client):
    r = client.post("/api/graphics/render", json={"image_id": "0" * 32})
    assert r.status_code == 404


def test_render_traversal_id_is_404(client):
    r = client.post("/api/graphics/render", json={"image_id": "../../etc/passwd"})
    assert r.status_code == 404


def test_render_validates_payload(client):
    image_id = upload_png(client)
    base = {"image_id": image_id}
    assert client.post("/api/graphics/render", json={**base, "template": "nope"}).status_code == 422
    assert client.post("/api/graphics/render", json={**base, "colors": {"background": "red"}}).status_code == 422
    assert client.post("/api/graphics/render", json={**base, "headline": "x" * 61}).status_code == 422
    assert client.post("/api/graphics/render", json={**base, "size": "huge"}).status_code == 422

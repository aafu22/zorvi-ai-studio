"""HTTP-level tests for the image endpoints."""

import io
import os
import time

from PIL import Image

from app.core.config import get_settings


def png_bytes(size=(120, 80), color="orange") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def upload(client, data: bytes, name="photo.png", mime="image/png"):
    return client.post("/api/images/upload", files={"file": (name, data, mime)})


def test_upload_valid_png(client):
    data = png_bytes()
    r = upload(client, data)
    assert r.status_code == 201
    body = r.json()
    assert (body["width"], body["height"], body["format"]) == (120, 80, "PNG")
    assert len(body["id"]) == 32
    # the stored original is byte-for-byte what was uploaded
    assert client.get(body["original_url"]).content == data


def test_client_filename_is_never_used_on_disk(client):
    r = upload(client, png_bytes(), name="../../evil.png")
    assert r.status_code == 201
    stored = list((get_settings().storage_path / "originals").iterdir())
    assert len(stored) == 1
    assert stored[0].name == f"{r.json()['id']}.png"


def test_upload_rejects_non_image_with_image_name(client):
    r = upload(client, b"just some text", name="fake.png")
    assert r.status_code == 400
    assert "valid image" in r.json()["detail"]


def test_upload_rejects_gif(client):
    buf = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buf, format="GIF")
    r = upload(client, buf.getvalue(), name="a.gif", mime="image/gif")
    assert r.status_code == 415


def test_upload_rejects_oversize(client):
    r = upload(client, b"0" * (1024 * 1024 + 10))  # limit is 1 MB in tests
    assert r.status_code == 413


def test_upload_rejects_empty(client):
    assert upload(client, b"").status_code == 400


def test_unknown_and_malicious_ids_return_404(client):
    for bad in ["0" * 32, "ZZZ", "..%2F..%2Fetc%2Fpasswd", "%2e%2e"]:
        assert client.get(f"/api/images/{bad}/original").status_code == 404
        assert client.post(f"/api/images/{bad}/process", json={}).status_code == 404


def test_process_returns_requested_size_and_keeps_original(client):
    data = png_bytes()
    img = upload(client, data).json()
    r = client.post(f"/api/images/{img['id']}/process", json={"preset": "story", "fit": "cover"})
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert Image.open(io.BytesIO(r.content)).size == (1080, 1920)
    assert client.get(img["original_url"]).content == data  # untouched


def test_process_validates_payload(client):
    img = upload(client, png_bytes()).json()
    url = f"/api/images/{img['id']}/process"
    assert client.post(url, json={"background": "red"}).status_code == 422
    assert client.post(url, json={"preset": "huge"}).status_code == 422
    assert client.post(url, json={"brightness": 9}).status_code == 422


def test_delete_removes_image(client):
    img = upload(client, png_bytes()).json()
    assert client.delete(f"/api/images/{img['id']}").status_code == 204
    assert client.get(img["original_url"]).status_code == 404
    assert client.delete(f"/api/images/{img['id']}").status_code == 404


def test_expired_files_are_cleaned_up_on_next_upload(client):
    old = upload(client, png_bytes()).json()
    path = next((get_settings().storage_path / "originals").glob(f"{old['id']}.*"))
    two_days_ago = time.time() - 48 * 3600
    os.utime(path, (two_days_ago, two_days_ago))
    upload(client, png_bytes())  # triggers cleanup (default TTL is 24h)
    assert client.get(old["original_url"]).status_code == 404

"""HTTP-level tests for Brand Kit, history, export and demo endpoints."""

import io
import zipfile

from PIL import Image


def png(size=(120, 80), color="orange") -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="PNG")
    return buf.getvalue()


def upload(client) -> dict:
    r = client.post("/api/images/upload", files={"file": ("p.png", png(), "image/png")})
    assert r.status_code == 201
    return r.json()


# ---------------------------------------------------------------- brand kit


def test_brand_kit_roundtrip(client, auth_headers):
    assert client.get("/api/brand-kit", headers=auth_headers).json()["configured"] is False
    body = {"brand_name": "Luna", "colors": {"background": "#000000", "text": "#ffffff", "accent": "#ff00aa"},
            "font": "serif", "tone": "luxury"}
    saved = client.put("/api/brand-kit", json=body, headers=auth_headers)
    assert saved.status_code == 200 and saved.json()["configured"] is True
    assert client.get("/api/brand-kit", headers=auth_headers).json()["brand_name"] == "Luna"
    assert client.put("/api/brand-kit", json={"font": "wingdings"}, headers=auth_headers).status_code == 422
    assert client.delete("/api/brand-kit", headers=auth_headers).status_code == 204
    assert client.get("/api/brand-kit", headers=auth_headers).json()["configured"] is False


def test_brand_logo_upload_serve_and_delete(client, auth_headers):
    assert client.get("/api/brand-kit/logo", headers=auth_headers).status_code == 404
    r = client.post("/api/brand-kit/logo", files={"file": ("logo.png", png(), "image/png")}, headers=auth_headers)
    assert r.status_code == 200 and r.json()["has_logo"] is True
    served = client.get("/api/brand-kit/logo", headers=auth_headers)
    assert served.status_code == 200 and served.headers["content-type"] == "image/png"
    assert client.post("/api/brand-kit/logo", files={"file": ("x.png", b"nope", "image/png")}, headers=auth_headers).status_code == 400
    assert client.delete("/api/brand-kit/logo", headers=auth_headers).json()["has_logo"] is False


def test_graphic_with_logo_flag_renders_with_and_without_a_logo(client, auth_headers):
    image = upload(client)
    payload = {"image_id": image["id"], "headline": "Hi", "brand_name": "Luna", "show_logo": True}
    assert client.post("/api/graphics/render", json=payload, headers=auth_headers).status_code == 200  # no logo yet: still fine
    client.post("/api/brand-kit/logo", files={"file": ("logo.png", png(color="crimson"), "image/png")}, headers=auth_headers)
    with_logo = client.post("/api/graphics/render", json=payload, headers=auth_headers)
    assert with_logo.status_code == 200
    # Signed-out visitors can still render; they just never get anyone's logo.
    without_login = client.post("/api/graphics/render", json=payload)
    assert without_login.status_code == 200 and without_login.content != with_logo.content


# ---------------------------------------------------------------- history


def test_history_save_list_open_delete(client, auth_headers):
    image = upload(client)
    state = {"details": {"product_name": "Ring"}, "style": "luxury"}
    saved = client.post("/api/history", json={"image_id": image["id"], "name": "Launch", "product_name": "Ring", "state": state}, headers=auth_headers)
    assert saved.status_code == 201
    cid = saved.json()["id"]
    assert [c["name"] for c in client.get("/api/history", headers=auth_headers).json()] == ["Launch"]
    assert client.get(f"/api/history/{cid}/thumbnail", headers=auth_headers).headers["content-type"] == "image/jpeg"
    assert client.get(f"/api/history/{cid}/photo", headers=auth_headers).status_code == 200
    opened = client.post(f"/api/history/{cid}/open", headers=auth_headers).json()
    assert opened["state"] == state and opened["image"]["id"] != image["id"]
    assert client.delete(f"/api/history/{cid}", headers=auth_headers).status_code == 204
    assert client.get("/api/history", headers=auth_headers).json() == []
    assert client.post(f"/api/history/{cid}/open", headers=auth_headers).status_code == 404


def test_history_validates_payload(client, auth_headers):
    image = upload(client)
    assert client.post("/api/history", json={"image_id": image["id"], "name": "", "state": {}}, headers=auth_headers).status_code == 422
    assert client.post("/api/history", json={"image_id": "0" * 32, "name": "x", "state": {}}, headers=auth_headers).status_code == 404


# ---------------------------------------------------------------- export


def kit_payload(image_id, **extra):
    return {
        "image_id": image_id,
        "details": {"product_name": "Rose Ring", "style": "minimal"},
        "copy": {"provider": {"id": "template", "label": "Template-based (not AI-generated)", "is_ai": False},
                 "captions": [{"tone": "friendly", "text": "Hello"}], "hashtags": "#a #b",
                 "short_descriptions": ["Short."], "promos": [], "ctas": ["Shop"]},
        "graphic": {"headline": "Rose Ring"},
        **extra,
    }


def test_export_kit_downloads_a_zip(client):
    image = upload(client)
    r = client.post("/api/export/kit", json=kit_payload(image["id"], sizes=["square"]))
    assert r.status_code == 200 and r.headers["content-type"] == "application/zip"
    assert 'filename="zorvi-rose-ring-kit.zip"' in r.headers["content-disposition"]
    names = zipfile.ZipFile(io.BytesIO(r.content)).namelist()
    assert "graphics/classic-square.png" in names and "marketing-copy.md" in names


def test_export_kit_errors(client):
    assert client.post("/api/export/kit", json=kit_payload("0" * 32)).status_code == 404
    image = upload(client)
    assert client.post("/api/export/kit", json=kit_payload(image["id"], sizes=["huge"])).status_code == 422
    assert client.post("/api/export/kit", json=kit_payload(image["id"], sizes=[])).status_code == 422


# ---------------------------------------------------------------- demo


def test_demo_start_returns_a_usable_project(client):
    demo = client.post("/api/demo/start").json()
    assert demo["details"]["product_name"] and demo["style"]
    assert client.get(demo["image"]["original_url"]).status_code == 200
    r = client.post("/api/graphics/render", json={"image_id": demo["image"]["id"], "headline": "Amber Glow"})
    assert r.status_code == 200

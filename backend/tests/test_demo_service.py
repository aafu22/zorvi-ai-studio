"""Demo mode: sample product with no account and no upload."""

import io

import pytest
from PIL import Image

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.copy import CopyRequest
from app.schemas.graphics import GraphicRequest
from app.services import demo_service, graphics_service
from app.services.copywriting.registry import get_provider
from app.services.storage_service import get_storage


def test_demo_loads_sample_as_a_temporary_upload(storage_env):
    demo = demo_service.start_demo()
    stored = get_storage().find_original(demo.image.id)
    assert stored is not None
    assert stored.read_bytes() == (get_settings().sample_assets_path / "sample-product.jpg").read_bytes()
    assert (demo.image.width, demo.image.height, demo.image.format) == (1600, 1600, "JPEG")
    assert demo.details.product_name and demo.style == "aesthetic"


def test_each_demo_start_gets_its_own_upload(storage_env):
    assert demo_service.start_demo().image.id != demo_service.start_demo().image.id


def test_demo_details_work_with_the_copy_generator(storage_env):
    demo = demo_service.start_demo()
    resp = get_provider("template").generate(
        CopyRequest(**demo.details.model_dump(), style=demo.style, seed=1))
    assert len(resp.captions) == 7 and "15% off" in resp.captions[0].text


def test_demo_photo_renders_in_every_template(storage_env):
    demo = demo_service.start_demo()
    path = get_storage().find_original(demo.image.id)
    for template in ("classic", "overlay", "frame", "offer"):
        body, _ = graphics_service.render_graphic(
            path, GraphicRequest(image_id=demo.image.id, template=template, headline="Amber Glow", badge="15% off"))
        assert Image.open(io.BytesIO(body)).size == (1080, 1080)


def test_missing_sample_gives_a_clear_error(storage_env, monkeypatch):
    monkeypatch.setenv("SAMPLE_ASSETS_DIR", str(storage_env / "nowhere"))
    get_settings.cache_clear()
    with pytest.raises(AppError) as exc:
        demo_service.start_demo()
    assert exc.value.status_code == 404 and "sample" in exc.value.detail.lower()


def test_sample_asset_is_a_valid_photo_of_reasonable_size():
    path = get_settings().sample_assets_path / "sample-product.jpg"
    assert path.is_file() and path.stat().st_size < 400_000

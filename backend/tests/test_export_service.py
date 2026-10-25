"""Marketing kit ZIP export."""

import io
import json
import zipfile

import pytest
from PIL import Image, ImageDraw

from app.schemas.export import ExportRequest
from app.services import export_service

PHOTO_NAME = "photo.png"


@pytest.fixture
def photo(tmp_path):
    img = Image.new("RGB", (800, 600), (200, 170, 150))
    ImageDraw.Draw(img).ellipse([250, 150, 550, 450], fill=(240, 240, 240))
    path = tmp_path / PHOTO_NAME
    img.save(path)
    return path


@pytest.fixture
def logo(tmp_path):
    path = tmp_path / "logo.png"
    Image.new("RGBA", (300, 120), (220, 20, 60, 255)).save(path)
    return path


def request(**overrides) -> ExportRequest:
    data = {
        "image_id": "x",
        "details": {
            "product_name": "Rose Quartz Ring", "category": "Jewellery & accessories",
            "description": "Silver ring with a rose quartz stone.", "target_audience": "gift buyers",
            "tone": "friendly", "brand_name": "Luna Studio", "offer": "20% off", "style": "aesthetic",
        },
        "copy": {
            "provider": {"id": "template", "label": "Template-based (not AI-generated)", "is_ai": False},
            "captions": [{"tone": "friendly", "text": "Meet the ring ✨\n\nShop now"}],
            "hashtags": "#RoseQuartzRing #Jewellery",
            "short_descriptions": ["A lovely ring.", "Another line."],
            "promos": [{"kind": "headline", "text": "Rose Quartz Ring: 20% off"}],
            "ctas": ["Shop now. Link in bio."],
        },
        "graphic": {"template": "classic", "headline": "Rose Quartz Ring", "cta": "Shop now",
                    "colors": {"background": "#ffffff", "text": "#111111", "accent": "#ff00aa"}},
    }
    data.update(overrides)
    return ExportRequest(**data)


def open_zip(data: bytes) -> zipfile.ZipFile:
    zf = zipfile.ZipFile(io.BytesIO(data))
    assert zf.testzip() is None  # archive is intact
    return zf


def test_kit_contains_every_promised_file(photo):
    zf = open_zip(export_service.build_kit(photo, request()))
    assert sorted(zf.namelist()) == sorted([
        "images/product-square.png",
        "graphics/classic-square.png", "graphics/classic-portrait.png", "graphics/classic-story.png",
        "marketing-copy.md", "product-description.txt", "campaign.json", "README.txt",
    ])


def test_graphics_have_instagram_sizes(photo):
    zf = open_zip(export_service.build_kit(photo, request()))
    sizes = {n: Image.open(io.BytesIO(zf.read(n))).size for n in zf.namelist() if n.startswith("graphics/")}
    assert sizes == {
        "graphics/classic-square.png": (1080, 1080),
        "graphics/classic-portrait.png": (1080, 1350),
        "graphics/classic-story.png": (1080, 1920),
    }


def test_size_selection_and_json_toggle(photo):
    zf = open_zip(export_service.build_kit(photo, request(sizes=["story", "story"], include_json=False)))
    names = zf.namelist()
    assert [n for n in names if n.startswith("graphics/")] == ["graphics/classic-story.png"]
    assert "campaign.json" not in names
    assert "campaign.json" not in zf.read("README.txt").decode()  # README lists only what is really there


def test_text_files_contain_the_users_edited_text(photo):
    zf = open_zip(export_service.build_kit(photo, request()))
    md = zf.read("marketing-copy.md").decode("utf-8")
    assert "Meet the ring ✨" in md and "#RoseQuartzRing #Jewellery" in md and "Shop now. Link in bio." in md
    assert "not written by an AI model" in md
    desc = zf.read("product-description.txt").decode("utf-8")
    assert "A lovely ring." in desc and "Silver ring with a rose quartz stone." in desc


def test_campaign_json_is_valid_and_complete(photo):
    zf = open_zip(export_service.build_kit(photo, request()))
    data = json.loads(zf.read("campaign.json"))
    assert data["details"]["product_name"] == "Rose Quartz Ring"
    assert data["copy"]["provider"]["is_ai"] is False
    assert data["copy"]["hashtags"] == "#RoseQuartzRing #Jewellery"
    assert data["graphic_design"]["template"] == "classic"
    assert data["graphic_sizes"] == ["square", "portrait", "story"]
    assert "created_utc" in data


def test_ai_provider_is_described_as_ai(photo):
    ai_copy = request().model_dump(by_alias=True)["copy"]
    ai_copy["provider"] = {"id": "llm", "label": "Some LLM", "is_ai": True}
    zf = open_zip(export_service.build_kit(photo, request(copy=ai_copy)))
    assert "AI model" in zf.read("marketing-copy.md").decode()
    assert "written by an AI model" in zf.read("README.txt").decode()


def test_original_photo_is_never_modified(photo):
    before = photo.read_bytes()
    export_service.build_kit(photo, request())
    assert photo.read_bytes() == before


def test_every_zip_entry_name_is_safe_even_with_hostile_input(photo):
    hostile = request()
    hostile.details.product_name = "../../evil\\name"
    hostile.graphic.headline = "../../etc/passwd"
    zf = open_zip(export_service.build_kit(photo, hostile))
    for name in zf.namelist():
        assert not name.startswith("/") and ".." not in name and "\\" not in name
    assert export_service.kit_filename(hostile.details) == "zorvi-evil-name-kit.zip"


def test_logo_appears_only_when_requested(photo, logo):
    def graphic(show_logo):
        return request(graphic={"template": "classic", "headline": "Hi", "brand_name": "Luna",
                                "show_logo": show_logo}, sizes=["square"])
    with_logo = open_zip(export_service.build_kit(photo, graphic(True), logo_path=logo))
    without = open_zip(export_service.build_kit(photo, graphic(False), logo_path=logo))
    no_file = open_zip(export_service.build_kit(photo, graphic(True), logo_path=None))
    a = with_logo.read("graphics/classic-square.png")
    assert a != without.read("graphics/classic-square.png")
    assert without.read("graphics/classic-square.png") == no_file.read("graphics/classic-square.png")
    crimson = Image.open(io.BytesIO(a)).convert("RGB").getcolors(2_000_000)
    assert any(c == (220, 20, 60) for _, c in crimson)  # the logo's colour is really drawn


@pytest.mark.parametrize("text,expected", [
    ("Rose Quartz Ring!", "rose-quartz-ring"),
    ("  --Hello__World--  ", "hello-world"),
    ("🎉🎉", "campaign"),
    ("", "campaign"),
    ("a" * 100, "a" * 40),
])
def test_slugify(text, expected):
    assert export_service.slugify(text) == expected

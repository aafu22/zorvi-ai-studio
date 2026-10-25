"""Tests for the social graphics renderer (no HTTP involved)."""

import io

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.schemas.graphics import GraphicColors, GraphicRequest
from app.services import graphics_service as g

TEMPLATES = ["classic", "overlay", "frame", "offer"]
SIZES = {"square": (1080, 1080), "portrait": (1080, 1350), "story": (1080, 1920)}
ACCENT = "#ff00aa"
ACCENT_RGB = (255, 0, 170)


@pytest.fixture
def photo(tmp_path):
    img = Image.new("RGB", (800, 600), (200, 170, 150))
    ImageDraw.Draw(img).ellipse([250, 150, 550, 450], fill=(240, 240, 240))
    path = tmp_path / "photo.png"
    img.save(path)
    return path


def make(**overrides) -> GraphicRequest:
    data = dict(
        image_id="x",
        template="classic",
        size="square",
        headline="Rose Quartz Ring",
        subheadline="Delicate silver ring with a rose quartz stone.",
        cta="Shop now",
        badge="20% off",
        brand_name="Luna Studio",
        colors=GraphicColors(background="#ffffff", text="#111111", accent=ACCENT),
    )
    data.update(overrides)
    return GraphicRequest(**data)


def render(photo, req, **kw) -> Image.Image:
    body, _ = g.render_graphic(photo, req, **kw)
    return Image.open(io.BytesIO(body)).convert("RGB")


def has_colour(img: Image.Image, rgb) -> bool:
    return any(c == rgb for _, c in img.getcolors(maxcolors=2_000_000))


# ---------- every template at every size ----------


@pytest.mark.parametrize("template", TEMPLATES)
@pytest.mark.parametrize("size", ["square", "portrait", "story"])
def test_output_dimensions(photo, template, size):
    assert render(photo, make(template=template, size=size)).size == SIZES[size]


@pytest.mark.parametrize("template", TEMPLATES)
def test_all_text_empty_still_renders(photo, template):
    req = make(template=template, headline="", subheadline="", cta="", badge="", brand_name="")
    assert render(photo, req).size == (1080, 1080)


@pytest.mark.parametrize("template", TEMPLATES)
def test_extreme_text_does_not_crash(photo, template):
    req = make(
        template=template,
        size="story",
        headline="W" * 60,
        subheadline="Supercalifragilisticexpialidocious " * 3,
        cta="C" * 30,
        badge="9" * 14,
        brand_name="B" * 40,
    )
    assert render(photo, req).size == (1080, 1920)


@pytest.mark.parametrize("font", ["sans", "serif", "display"])
def test_each_font_renders(photo, font):
    assert render(photo, make(font=font)).size == (1080, 1080)


def test_bundled_fonts_are_present_and_loadable():
    for font_id, (regular, bold) in g.FONT_FILES.items():
        for name in (regular, bold):
            assert (g.FONT_DIR / name).is_file(), name
        assert isinstance(g.load_font(font_id, True, 40), ImageFont.FreeTypeFont)


def test_options_match_what_can_be_rendered():
    assert {t.id for t in g.OPTIONS.templates} == set(g.TEMPLATES)
    assert {s.id: (s.width, s.height) for s in g.OPTIONS.sizes} == SIZES
    assert {f.id for f in g.OPTIONS.fonts} == set(g.FONT_FILES)


# ---------- colours ----------


def test_background_colour_is_applied(photo):
    img = render(photo, make(colors=GraphicColors(background="#123456", text="#ffffff", accent=ACCENT)))
    assert img.getpixel((2, 1078)) == (0x12, 0x34, 0x56)  # bottom-left corner, no photo there


def test_accent_used_for_cta_only_when_cta_given(photo):
    assert has_colour(render(photo, make()), ACCENT_RGB)
    assert not has_colour(render(photo, make(cta="")), ACCENT_RGB)


def test_badge_only_drawn_by_offer_template(photo):
    base = dict(cta="", brand_name="")
    assert has_colour(render(photo, make(template="offer", **base)), ACCENT_RGB)
    assert not has_colour(render(photo, make(template="classic", **base)), ACCENT_RGB)
    assert not has_colour(render(photo, make(template="offer", badge="", **base)), ACCENT_RGB)


def test_overlay_text_area_is_strongly_covered_by_background_colour(photo):
    img = render(photo, make(template="overlay", colors=GraphicColors(background="#000000", text="#ffffff", accent=ACCENT)))
    r, g_, b = img.getpixel((2, 1040))
    assert max(r, g_, b) < 25  # near-solid backdrop under the text


def test_text_contrast_helpers():
    assert g.readable_on((255, 255, 255)) == (17, 17, 17)
    assert g.readable_on((0, 0, 0)) == (255, 255, 255)
    assert g.contrast_ratio((255, 255, 255), (0, 0, 0)) == pytest.approx(21, rel=0.01)


# ---------- text helpers ----------


def test_emoji_and_control_characters_are_stripped():
    assert g.sanitize_text("Sale 🎉 now\x00!") == "Sale now !"
    assert g.sanitize_text("₹499 only") == "₹499 only"


def test_fit_text_never_exceeds_its_box():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    long = "A very long product headline that goes on and on and on " * 4
    block = g.fit_text(draw, long, "sans", True, 400, 120, 90, 20)
    assert block is not None
    assert block.height <= 120
    assert all(draw.textlength(line, font=block.font) <= 400 for line in block.lines)
    assert block.lines[-1].endswith("…")


def test_fit_text_prefers_large_text_when_short():
    draw = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    short = g.fit_text(draw, "Hi", "sans", True, 600, 300, 100, 20)
    long = g.fit_text(draw, "A much longer headline for this box", "sans", True, 600, 300, 100, 20)
    assert short.font.size > long.font.size


# ---------- photo handling ----------


def test_original_file_is_never_modified(photo):
    before = photo.read_bytes()
    render(photo, make(template="overlay", size="story"))
    assert photo.read_bytes() == before


def test_photo_adjustments_change_output(photo):
    plain = render(photo, make(template="overlay", cta="", brand_name="", headline="", subheadline=""))
    dark = render(photo, make(template="overlay", cta="", brand_name="", headline="", subheadline="",
                              photo={"brightness": 0.5}))
    assert dark.getpixel((540, 100))[0] < plain.getpixel((540, 100))[0]


def test_preview_is_a_scaled_copy_of_the_export(photo):
    full = render(photo, make(size="story"))
    small = render(photo, make(size="story"), preview_width=540)
    assert small.size == (540, 960)
    assert full.resize((540, 960)).getpixel((10, 10)) == pytest.approx(small.getpixel((10, 10)), abs=6)


def test_jpeg_output(photo):
    body, media = g.render_graphic(photo, make(output_format="jpeg"))
    assert media == "image/jpeg" and Image.open(io.BytesIO(body)).format == "JPEG"

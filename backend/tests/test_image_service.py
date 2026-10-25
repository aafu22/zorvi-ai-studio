"""Unit tests for image validation and editing (no HTTP involved)."""

import io

import pytest
from PIL import Image, ImageStat

from app.core.errors import AppError
from app.schemas.images import ProcessRequest
from app.services import image_service


def make_png(path, size=(200, 100), color=(10, 120, 200, 255)):
    Image.new("RGBA", size, color).save(path, format="PNG")
    return path


def make_half_image(path):
    """200x100 image: left half red, right half blue."""
    img = Image.new("RGB", (200, 100), (255, 0, 0))
    img.paste((0, 0, 255), (100, 0, 200, 100))
    img.save(path, format="PNG")
    return path


def decode(body: bytes) -> Image.Image:
    return Image.open(io.BytesIO(body)).convert("RGB")


# ---------- validation ----------


def test_inspect_accepts_png():
    buf = io.BytesIO()
    Image.new("RGB", (40, 30), "red").save(buf, format="PNG")
    info = image_service.inspect_image(buf.getvalue())
    assert (info.format, info.width, info.height) == ("PNG", 40, 30)


def test_inspect_rejects_text_file():
    with pytest.raises(AppError) as exc:
        image_service.inspect_image(b"this is not an image")
    assert exc.value.status_code == 400


def test_inspect_rejects_gif():
    buf = io.BytesIO()
    Image.new("RGB", (10, 10), "red").save(buf, format="GIF")
    with pytest.raises(AppError) as exc:
        image_service.inspect_image(buf.getvalue())
    assert exc.value.status_code == 415


def test_inspect_rejects_truncated_png():
    buf = io.BytesIO()
    Image.new("RGB", (300, 300), "red").save(buf, format="PNG")
    with pytest.raises(AppError):
        image_service.inspect_image(buf.getvalue()[:-40])


# ---------- presets and output size ----------


@pytest.mark.parametrize(
    "preset,expected",
    [("square", (1080, 1080)), ("portrait", (1080, 1350)), ("story", (1080, 1920))],
)
@pytest.mark.parametrize("fit", ["cover", "contain"])
def test_preset_output_sizes(tmp_path, preset, expected, fit):
    src = make_png(tmp_path / "a.png")
    body, media = image_service.process_image(src, ProcessRequest(preset=preset, fit=fit))
    assert media == "image/png"
    assert decode(body).size == expected


def test_original_preset_keeps_size(tmp_path):
    src = make_png(tmp_path / "a.png", size=(321, 123))
    body, _ = image_service.process_image(src, ProcessRequest(preset="original"))
    assert decode(body).size == (321, 123)


def test_jpeg_output(tmp_path):
    src = make_png(tmp_path / "a.png")
    body, media = image_service.process_image(src, ProcessRequest(output_format="jpeg"))
    assert media == "image/jpeg"
    assert Image.open(io.BytesIO(body)).format == "JPEG"


# ---------- background ----------


def test_contain_letterbox_uses_background_colour(tmp_path):
    src = make_png(tmp_path / "wide.png", size=(400, 200))
    opts = ProcessRequest(preset="story", fit="contain", background="#ff0000")
    out = decode(image_service.process_image(src, opts)[0])
    assert out.getpixel((0, 0)) == (255, 0, 0)  # empty space above the photo
    assert out.getpixel((540, 960)) == (10, 120, 200)  # photo in the middle


def test_transparent_png_gets_background(tmp_path):
    src = tmp_path / "t.png"
    Image.new("RGBA", (100, 100), (0, 0, 0, 0)).save(src, format="PNG")
    opts = ProcessRequest(preset="square", fit="cover", background="#00ff00")
    out = decode(image_service.process_image(src, opts)[0])
    assert out.getpixel((500, 500)) == (0, 255, 0)


def test_invalid_background_rejected():
    with pytest.raises(ValueError):
        ProcessRequest(background="red")


# ---------- crop ----------


def test_cover_crop_focus_moves_window(tmp_path):
    src = make_half_image(tmp_path / "h.png")
    left = decode(image_service.process_image(
        src, ProcessRequest(preset="square", fit="cover", zoom=2.0, focus_x=0.0))[0])
    right = decode(image_service.process_image(
        src, ProcessRequest(preset="square", fit="cover", zoom=2.0, focus_x=1.0))[0])
    assert left.getpixel((540, 540)) == (255, 0, 0)
    assert right.getpixel((540, 540)) == (0, 0, 255)


def test_zoom_one_cover_shows_both_halves_in_wide_to_square(tmp_path):
    src = make_half_image(tmp_path / "h.png")
    out = decode(image_service.process_image(
        src, ProcessRequest(preset="square", fit="cover", zoom=1.0))[0])
    # 200x100 -> centred 100x100 crop: left edge is red, right edge is blue
    assert out.getpixel((5, 540))[0] > 200
    assert out.getpixel((1074, 540))[2] > 200


# ---------- adjustments ----------


def mean_brightness(img: Image.Image) -> float:
    return sum(ImageStat.Stat(img).mean) / 3


def test_brightness_changes_output(tmp_path):
    src = make_png(tmp_path / "a.png")
    base = decode(image_service.process_image(src, ProcessRequest(fit="cover"))[0])
    bright = decode(image_service.process_image(src, ProcessRequest(fit="cover", brightness=1.5))[0])
    dark = decode(image_service.process_image(src, ProcessRequest(fit="cover", brightness=0.5))[0])
    assert mean_brightness(dark) < mean_brightness(base) < mean_brightness(bright)


def test_saturation_zero_gives_grey(tmp_path):
    src = make_png(tmp_path / "a.png", color=(255, 0, 0, 255))
    out = decode(image_service.process_image(src, ProcessRequest(fit="cover", saturation=0.0))[0])
    r, g, b = out.getpixel((540, 540))
    assert abs(r - g) < 3 and abs(g - b) < 3


# ---------- originals are never modified ----------


def test_original_file_unchanged_after_processing(tmp_path):
    src = make_png(tmp_path / "a.png")
    before = src.read_bytes()
    image_service.process_image(src, ProcessRequest(preset="story", brightness=1.3, zoom=2.0))
    assert src.read_bytes() == before


def test_exif_orientation_is_applied(tmp_path):
    src = tmp_path / "rot.jpg"
    img = Image.new("RGB", (200, 100), (255, 0, 0))
    exif = Image.Exif()
    exif[0x0112] = 6  # rotate 90 degrees clockwise when displayed
    img.save(src, format="JPEG", exif=exif)
    body, _ = image_service.process_image(src, ProcessRequest(preset="original"))
    assert decode(body).size == (100, 200)

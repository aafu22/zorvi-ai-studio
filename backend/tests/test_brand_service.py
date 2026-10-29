"""Brand Kit: SQLite settings + logo handling (real database and files in a temp folder)."""

import io

import pytest
from pydantic import ValidationError
from PIL import Image

from app.core.errors import AppError
from app.schemas.brand import BrandKitIn
from app.schemas.graphics import GraphicColors
from app.services import brand_service

U = 1  # the account that owns the Brand Kit in these tests


def png_bytes(size=(200, 100), color=(10, 120, 200, 128)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_blank_kit_before_first_save(storage_env):
    kit = brand_service.get_kit(U)
    assert kit.configured is False and kit.has_logo is False and kit.logo_url is None
    assert kit.font == "sans" and kit.tone == "friendly"


def test_save_and_read_back(storage_env):
    saved = brand_service.save_kit(U, BrandKitIn(
        brand_name="  Hearth   & Honey ",
        colors=GraphicColors(background="#101010", text="#fafafa", accent="#c9a227"),
        font="serif", tone="luxury"))
    assert saved.configured is True
    assert saved.brand_name == "Hearth & Honey"
    assert (saved.colors.background, saved.colors.accent) == ("#101010", "#c9a227")
    assert (saved.font, saved.tone) == ("serif", "luxury")
    assert brand_service.get_kit(U) == saved  # really persisted, not just returned


def test_saving_again_updates_the_single_row(storage_env):
    brand_service.save_kit(U, BrandKitIn(brand_name="One"))
    brand_service.save_kit(U, BrandKitIn(brand_name="Two", tone="playful"))
    kit = brand_service.get_kit(U)
    assert (kit.brand_name, kit.tone) == ("Two", "playful")
    from app.database.db import connect
    with connect() as db:
        assert db.execute("SELECT COUNT(*) FROM brand_kits WHERE user_id = ?", (U,)).fetchone()[0] == 1


def test_invalid_values_rejected_by_schema():
    with pytest.raises(ValidationError):
        BrandKitIn(colors=GraphicColors(background="red"))
    with pytest.raises(ValidationError):
        BrandKitIn(font="comic-sans")
    with pytest.raises(ValidationError):
        BrandKitIn(brand_name="x" * 41)


def test_logo_is_stored_as_png_with_transparency(storage_env):
    kit = brand_service.save_logo(U, png_bytes())
    assert kit.has_logo and kit.logo_url == "/api/brand-kit/logo"
    path = brand_service.logo_path(U)
    with Image.open(path) as logo:
        assert logo.format == "PNG" and logo.mode == "RGBA"
        assert logo.getpixel((5, 5))[3] == 128  # alpha kept


def test_large_logo_is_shrunk(storage_env):
    brand_service.save_logo(U, png_bytes(size=(1500, 900)))
    with Image.open(brand_service.logo_path(U)) as logo:
        assert max(logo.size) == brand_service.LOGO_MAX_SIDE
        assert logo.size == (600, 360)  # aspect ratio kept


def test_jpeg_logo_accepted(storage_env):
    buf = io.BytesIO()
    Image.new("RGB", (80, 80), "red").save(buf, format="JPEG")
    assert brand_service.save_logo(U, buf.getvalue()).has_logo


def test_bad_logos_rejected(storage_env):
    with pytest.raises(AppError) as e1:
        brand_service.save_logo(U, b"not an image")
    assert e1.value.status_code == 400
    gif = io.BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    with pytest.raises(AppError) as e2:
        brand_service.save_logo(U, gif.getvalue())
    assert e2.value.status_code == 415
    with pytest.raises(AppError) as e3:
        brand_service.save_logo(U, b"0" * (brand_service.LOGO_MAX_BYTES + 1))
    assert e3.value.status_code == 413
    assert brand_service.logo_path(U) is None  # nothing half-saved


def test_replacing_and_deleting_logo(storage_env):
    brand_service.save_logo(U, png_bytes(size=(100, 100)))
    brand_service.save_logo(U, png_bytes(size=(50, 20)))
    with Image.open(brand_service.logo_path(U)) as logo:
        assert logo.size == (50, 20)
    assert brand_service.delete_logo(U).has_logo is False
    assert brand_service.logo_path(U) is None
    brand_service.delete_logo(U)  # deleting twice is harmless


def test_resetting_kit_removes_settings_and_logo(storage_env):
    brand_service.save_kit(U, BrandKitIn(brand_name="Gone"))
    brand_service.save_logo(U, png_bytes())
    brand_service.delete_kit(U)
    kit = brand_service.get_kit(U)
    assert kit.configured is False and kit.has_logo is False and kit.brand_name == ""


def test_each_account_has_its_own_kit_and_logo(storage_env):
    brand_service.save_kit(1, BrandKitIn(brand_name="Alpha", tone="luxury"))
    brand_service.save_logo(1, png_bytes())
    other = brand_service.get_kit(2)
    assert other.configured is False and other.has_logo is False and other.brand_name == ""
    assert brand_service.logo_path(2) is None

    brand_service.save_kit(2, BrandKitIn(brand_name="Beta", tone="playful"))
    assert brand_service.get_kit(1).brand_name == "Alpha"
    assert brand_service.get_kit(2).brand_name == "Beta"

    brand_service.delete_kit(2)  # resetting one account leaves the other untouched
    assert brand_service.get_kit(1).configured is True and brand_service.get_kit(1).has_logo is True

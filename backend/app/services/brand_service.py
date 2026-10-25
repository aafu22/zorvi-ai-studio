"""Brand Kit: one saved brand (name, colours, font, tone) plus an optional logo.

Settings live in SQLite. The logo is a normalised PNG kept at storage/brand/logo.png.
It is stored until the user removes it, because the Brand Kit exists to be reused.
"""

import io
import os
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.db import connect
from app.schemas.brand import BrandKitIn, BrandKitOut
from app.schemas.graphics import GraphicColors
from app.services import image_service

LOGO_MAX_SIDE = 600
LOGO_MAX_BYTES = 2 * 1024 * 1024


def _brand_dir() -> Path:
    path = get_settings().storage_path / "brand"
    path.mkdir(parents=True, exist_ok=True)
    return path


def logo_path() -> Path | None:
    path = _brand_dir() / "logo.png"
    return path if path.is_file() else None


def get_kit() -> BrandKitOut:
    has_logo = logo_path() is not None
    logo_url = "/api/brand-kit/logo" if has_logo else None
    with connect() as db:
        row = db.execute("SELECT * FROM brand_kit WHERE id = 1").fetchone()
    if row is None:
        return BrandKitOut(configured=False, has_logo=has_logo, logo_url=logo_url)
    return BrandKitOut(
        brand_name=row["brand_name"],
        colors=GraphicColors(
            background=row["background"], text=row["text_color"], accent=row["accent"]
        ),
        font=row["font"],
        tone=row["tone"],
        configured=True,
        has_logo=has_logo,
        logo_url=logo_url,
    )


def save_kit(kit: BrandKitIn) -> BrandKitOut:
    with connect() as db:
        db.execute(
            """
            INSERT INTO brand_kit (id, brand_name, background, text_color, accent, font, tone, updated_at)
            VALUES (1, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                brand_name = excluded.brand_name, background = excluded.background,
                text_color = excluded.text_color, accent = excluded.accent,
                font = excluded.font, tone = excluded.tone, updated_at = excluded.updated_at
            """,
            (
                kit.brand_name, kit.colors.background, kit.colors.text, kit.colors.accent,
                kit.font, kit.tone, datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return get_kit()


def delete_kit() -> None:
    """Remove saved settings and the logo (back to a blank Brand Kit)."""
    with connect() as db:
        db.execute("DELETE FROM brand_kit WHERE id = 1")
    delete_logo()


def save_logo(data: bytes) -> BrandKitOut:
    """Validate, normalise (PNG, max 600 px, EXIF rotation applied) and store the logo."""
    if len(data) > LOGO_MAX_BYTES:
        raise AppError(413, "Logo is too large. The limit is 2 MB.")
    image_service.inspect_image(data)  # raises AppError for non-images and unsupported types
    try:
        with Image.open(io.BytesIO(data)) as src:
            logo = ImageOps.exif_transpose(src).convert("RGBA")
    except Exception as exc:
        raise AppError(400, "That file is not a valid image.") from exc
    logo.thumbnail((LOGO_MAX_SIDE, LOGO_MAX_SIDE), Image.Resampling.LANCZOS)

    target = _brand_dir() / "logo.png"
    temp = target.with_suffix(".tmp")
    logo.save(temp, format="PNG")
    os.replace(temp, target)  # atomic: a reader never sees a half-written logo
    return get_kit()


def delete_logo() -> BrandKitOut:
    path = logo_path()
    if path is not None:
        path.unlink(missing_ok=True)
    return get_kit()

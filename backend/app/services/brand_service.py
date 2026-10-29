"""Brand Kit: one saved brand (name, colours, font, tone) plus an optional logo, per account.

Settings live in the database (one row per user). The logo is a normalised PNG kept at
storage/brand/logo_<user id>.png. It is stored until the user removes it, because the Brand Kit exists
to be reused. Every function takes the owner's ``user_id`` first, so one account never sees another's brand.
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


def _logo_file(user_id: int) -> Path:
    return _brand_dir() / f"logo_{int(user_id)}.png"


def logo_path(user_id: int) -> Path | None:
    path = _logo_file(user_id)
    return path if path.is_file() else None


def get_kit(user_id: int) -> BrandKitOut:
    has_logo = logo_path(user_id) is not None
    logo_url = "/api/brand-kit/logo" if has_logo else None
    with connect() as db:
        row = db.execute("SELECT * FROM brand_kits WHERE user_id = ?", (user_id,)).fetchone()
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


def save_kit(user_id: int, kit: BrandKitIn) -> BrandKitOut:
    with connect() as db:
        db.execute(
            """
            INSERT INTO brand_kits (user_id, brand_name, background, text_color, accent, font, tone, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                brand_name = excluded.brand_name, background = excluded.background,
                text_color = excluded.text_color, accent = excluded.accent,
                font = excluded.font, tone = excluded.tone, updated_at = excluded.updated_at
            """,
            (
                user_id, kit.brand_name, kit.colors.background, kit.colors.text, kit.colors.accent,
                kit.font, kit.tone, datetime.now(timezone.utc).isoformat(timespec="seconds"),
            ),
        )
    return get_kit(user_id)


def delete_kit(user_id: int) -> None:
    """Remove saved settings and the logo (back to a blank Brand Kit)."""
    with connect() as db:
        db.execute("DELETE FROM brand_kits WHERE user_id = ?", (user_id,))
    delete_logo(user_id)


def save_logo(user_id: int, data: bytes) -> BrandKitOut:
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

    target = _logo_file(user_id)
    temp = target.with_suffix(".tmp")
    logo.save(temp, format="PNG")
    os.replace(temp, target)  # atomic: a reader never sees a half-written logo
    return get_kit(user_id)


def delete_logo(user_id: int) -> BrandKitOut:
    path = logo_path(user_id)
    if path is not None:
        path.unlink(missing_ok=True)
    return get_kit(user_id)

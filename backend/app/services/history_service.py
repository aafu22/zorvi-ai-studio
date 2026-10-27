"""Saved projects ("history").

Unlike temporary uploads, a saved project keeps its own copy of the photo so it can be
reopened after the 24 hour upload expiry. This is stored only because the user pressed
Save, and deleting the project deletes the photo and thumbnail too.
"""

import io
import json
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image, ImageOps

from app.core.config import get_settings
from app.core.errors import AppError
from app.database.db import connect
from app.schemas.history import (
    CampaignSummary,
    OpenCampaignResponse,
    SaveCampaignRequest,
)
from app.schemas.images import UploadResponse
from app.services import image_service
from app.services.storage_service import get_storage

MAX_CAMPAIGNS = 50
THUMB_SIZE = (360, 360)
EXTENSION_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}


def _dir() -> Path:
    path = get_settings().storage_path / "campaigns"
    path.mkdir(parents=True, exist_ok=True)
    return path


def photo_path(campaign_id: int, ext: str) -> Path:
    return _dir() / f"{int(campaign_id)}.{ext}"


def thumb_path(campaign_id: int) -> Path:
    return _dir() / f"{int(campaign_id)}_thumb.jpg"


def _summary(row) -> CampaignSummary:
    cid = row["id"]
    return CampaignSummary(
        id=cid,
        name=row["name"],
        product_name=row["product_name"],
        created_at=row["created_at"],
        thumbnail_url=f"/api/history/{cid}/thumbnail",
        photo_url=f"/api/history/{cid}/photo",
    )


def _row(campaign_id: int):
    with connect() as db:
        row = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    if row is None:
        raise AppError(404, "Saved project not found.")
    return row


def list_campaigns() -> list[CampaignSummary]:
    with connect() as db:
        rows = db.execute("SELECT * FROM campaigns ORDER BY id DESC LIMIT ?", (MAX_CAMPAIGNS,)).fetchall()
    return [_summary(r) for r in rows]


def save_campaign(req: SaveCampaignRequest) -> CampaignSummary:
    source = get_storage().find_original(req.image_id)
    if source is None:
        raise AppError(404, "Image not found. It may have expired; please upload it again.")
    with connect() as db:
        count = db.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0]
    if count >= MAX_CAMPAIGNS:
        raise AppError(409, f"History is full ({MAX_CAMPAIGNS} projects). Delete an older project first.")

    data = source.read_bytes()
    ext = source.suffix.lstrip(".")
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with connect() as db:
        cur = db.execute(
            "INSERT INTO campaigns (name, product_name, photo_ext, state, created_at) VALUES (?, ?, ?, ?, ?) "
            "RETURNING id",
            (req.name, req.product_name, ext, json.dumps(req.state), created),
        )
        campaign_id = int(cur.fetchone()["id"])
        try:
            photo_path(campaign_id, ext).write_bytes(data)
            _write_thumbnail(data, thumb_path(campaign_id))
        except Exception as exc:  # roll the row back if the files could not be written
            _remove_files(campaign_id, ext)
            raise AppError(500, "Could not save the project files.") from exc
        row = db.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
    return _summary(row)


def _write_thumbnail(data: bytes, target: Path) -> None:
    with Image.open(io.BytesIO(data)) as src:
        img = ImageOps.exif_transpose(src).convert("RGBA")
    flat = Image.new("RGB", img.size, (255, 255, 255))
    flat.paste(img, mask=img.getchannel("A"))
    ImageOps.fit(flat, THUMB_SIZE, Image.Resampling.LANCZOS).save(target, format="JPEG", quality=82)


def _remove_files(campaign_id: int, ext: str) -> None:
    photo_path(campaign_id, ext).unlink(missing_ok=True)
    thumb_path(campaign_id).unlink(missing_ok=True)


def open_campaign(campaign_id: int) -> OpenCampaignResponse:
    """Restore the saved photo as a fresh temporary upload and return the saved settings."""
    row = _row(campaign_id)
    path = photo_path(campaign_id, row["photo_ext"])
    if not path.is_file():
        raise AppError(404, "The saved photo for this project is missing.")
    data = path.read_bytes()
    info = image_service.inspect_image(data)
    new_id = get_storage().save_original(data, EXTENSION_BY_FORMAT[info.format])
    return OpenCampaignResponse(
        image=UploadResponse(
            id=new_id, width=info.width, height=info.height, format=info.format,
            size_bytes=len(data), original_url=f"/api/images/{new_id}/original",
        ),
        state=json.loads(row["state"]),
    )


def get_thumbnail(campaign_id: int) -> Path:
    _row(campaign_id)
    path = thumb_path(campaign_id)
    if not path.is_file():
        raise AppError(404, "Thumbnail not found.")
    return path


def get_photo(campaign_id: int) -> Path:
    row = _row(campaign_id)
    path = photo_path(campaign_id, row["photo_ext"])
    if not path.is_file():
        raise AppError(404, "The saved photo for this project is missing.")
    return path


def delete_campaign(campaign_id: int) -> None:
    row = _row(campaign_id)
    with connect() as db:
        db.execute("DELETE FROM campaigns WHERE id = ?", (campaign_id,))
    _remove_files(campaign_id, row["photo_ext"])

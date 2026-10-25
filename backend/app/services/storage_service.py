"""File storage for uploaded images.

Security notes:
- Files are stored under server-generated UUID names. User-supplied file names
  never touch the filesystem, so path traversal is not possible.
- Image ids coming from the URL are validated against a strict regex before use.
- Originals are written once and never modified.
"""

from __future__ import annotations

import re
import time
import uuid
from functools import lru_cache
from pathlib import Path

from app.core.config import get_settings

ID_PATTERN = re.compile(r"^[0-9a-f]{32}$")
ALLOWED_EXTENSIONS = ("jpg", "png", "webp")


class StorageService:
    def __init__(self, root: Path) -> None:
        self.root = Path(root).resolve()
        self.originals_dir = self.root / "originals"
        self.originals_dir.mkdir(parents=True, exist_ok=True)

    def save_original(self, data: bytes, extension: str) -> str:
        if extension not in ALLOWED_EXTENSIONS:
            raise ValueError(f"Unsupported extension: {extension}")
        image_id = uuid.uuid4().hex
        (self.originals_dir / f"{image_id}.{extension}").write_bytes(data)
        return image_id

    def find_original(self, image_id: str) -> Path | None:
        """Return the stored file for an id, or None if the id is invalid/unknown."""
        if not ID_PATTERN.fullmatch(image_id):
            return None
        for ext in ALLOWED_EXTENSIONS:
            candidate = (self.originals_dir / f"{image_id}.{ext}").resolve()
            if candidate.is_relative_to(self.originals_dir) and candidate.is_file():
                return candidate
        return None

    def delete_original(self, image_id: str) -> bool:
        path = self.find_original(image_id)
        if path is None:
            return False
        path.unlink(missing_ok=True)
        return True

    def cleanup_expired(self, ttl_hours: float) -> int:
        """Delete stored files older than ttl_hours. Returns number removed."""
        cutoff = time.time() - ttl_hours * 3600
        removed = 0
        for path in self.originals_dir.iterdir():
            if path.is_file() and path.stat().st_mtime < cutoff:
                path.unlink(missing_ok=True)
                removed += 1
        return removed


@lru_cache
def get_storage() -> StorageService:
    return StorageService(get_settings().storage_path)

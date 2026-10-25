from pathlib import Path

from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse

from app.core.config import get_settings
from app.core.errors import AppError
from app.schemas.images import ProcessRequest, UploadResponse
from app.services import image_service
from app.services.storage_service import get_storage

router = APIRouter(prefix="/images", tags=["images"])

EXTENSION_BY_FORMAT = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}
MEDIA_TYPE_BY_EXTENSION = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def _stored_path(image_id: str) -> Path:
    path = get_storage().find_original(image_id)
    if path is None:
        raise AppError(404, "Image not found. It may have expired; please upload it again.")
    return path


@router.post("/upload", response_model=UploadResponse, status_code=201)
async def upload_image(file: UploadFile = File(...)) -> UploadResponse:
    """Validate and store an original product photo. The stored copy is never modified."""
    settings = get_settings()
    limit = settings.max_upload_mb * 1024 * 1024
    data = await file.read(limit + 1)  # read one byte past the limit to detect oversize
    if len(data) > limit:
        raise AppError(413, f"File is too large. The limit is {settings.max_upload_mb} MB.")
    if not data:
        raise AppError(400, "The uploaded file is empty.")

    info = image_service.inspect_image(data)
    storage = get_storage()
    storage.cleanup_expired(settings.file_ttl_hours)
    image_id = storage.save_original(data, EXTENSION_BY_FORMAT[info.format])
    return UploadResponse(
        id=image_id,
        width=info.width,
        height=info.height,
        format=info.format,
        size_bytes=len(data),
        original_url=f"/api/images/{image_id}/original",
    )


@router.get("/{image_id}/original")
def get_original(image_id: str) -> FileResponse:
    path = _stored_path(image_id)
    return FileResponse(
        path,
        media_type=MEDIA_TYPE_BY_EXTENSION.get(path.suffix.lstrip("."), "application/octet-stream"),
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"},
    )


# Plain `def` on purpose: FastAPI runs it in a worker thread, so CPU-heavy Pillow work
# does not block other requests.
@router.post("/{image_id}/process")
def process(image_id: str, options: ProcessRequest) -> Response:
    """Render an edited copy for preview or download."""
    body, media_type = image_service.process_image(_stored_path(image_id), options)
    return Response(content=body, media_type=media_type, headers={"Cache-Control": "no-store"})


@router.delete("/{image_id}", status_code=204)
def delete_image(image_id: str) -> Response:
    if not get_storage().delete_original(image_id):
        raise AppError(404, "Image not found.")
    return Response(status_code=204)

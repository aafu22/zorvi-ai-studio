from fastapi import APIRouter, Response

from app.core.errors import AppError
from app.schemas.export import ExportRequest
from app.services import brand_service, export_service
from app.services.storage_service import get_storage

router = APIRouter(prefix="/export", tags=["export"])


# Plain `def`: building the ZIP renders several images, so it runs in a worker thread.
@router.post("/kit")
def export_kit(request: ExportRequest) -> Response:
    """Build the marketing kit ZIP: edited product image, graphics, copy, description, JSON."""
    path = get_storage().find_original(request.image_id)
    if path is None:
        raise AppError(404, "Image not found. It may have expired; please upload it again.")
    body = export_service.build_kit(path, request, logo_path=brand_service.logo_path())
    filename = export_service.kit_filename(request.details)
    return Response(
        content=body,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "Cache-Control": "no-store",
        },
    )

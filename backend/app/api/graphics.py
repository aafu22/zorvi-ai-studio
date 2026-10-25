from fastapi import APIRouter, Response

from app.core.errors import AppError
from app.schemas.graphics import GraphicOptions, GraphicRequest
from app.services import brand_service, graphics_service
from app.services.storage_service import get_storage

router = APIRouter(prefix="/graphics", tags=["graphics"])

PREVIEW_WIDTH = 540


@router.get("/options", response_model=GraphicOptions)
def graphic_options() -> GraphicOptions:
    """Templates, sizes and fonts, so the UI is driven by what the server can actually render."""
    return graphics_service.OPTIONS


# Plain `def`: runs in a worker thread so Pillow work does not block other requests.
@router.post("/render")
def render_graphic(request: GraphicRequest, preview: bool = False) -> Response:
    """Render a graphic from the stored product photo.

    preview=true returns a smaller image with the identical layout, for fast on-screen updates.
    Without it you get the full-resolution export (1080 px wide).
    """
    path = get_storage().find_original(request.image_id)
    if path is None:
        raise AppError(404, "Image not found. It may have expired; please upload it again.")
    body, media_type = graphics_service.render_graphic(
        path,
        request,
        preview_width=PREVIEW_WIDTH if preview else None,
        logo_path=brand_service.logo_path() if request.show_logo else None,
    )
    return Response(content=body, media_type=media_type, headers={"Cache-Control": "no-store"})

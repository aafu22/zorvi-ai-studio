from fastapi import APIRouter, File, Response, UploadFile
from fastapi.responses import FileResponse

from app.core.errors import AppError
from app.schemas.brand import BrandKitIn, BrandKitOut
from app.services import brand_service

router = APIRouter(prefix="/brand-kit", tags=["brand-kit"])


@router.get("", response_model=BrandKitOut)
def get_brand_kit() -> BrandKitOut:
    return brand_service.get_kit()


@router.put("", response_model=BrandKitOut)
def save_brand_kit(kit: BrandKitIn) -> BrandKitOut:
    return brand_service.save_kit(kit)


@router.delete("", status_code=204)
def reset_brand_kit() -> Response:
    """Remove the saved settings and the logo."""
    brand_service.delete_kit()
    return Response(status_code=204)


@router.post("/logo", response_model=BrandKitOut)
async def upload_logo(file: UploadFile = File(...)) -> BrandKitOut:
    data = await file.read(brand_service.LOGO_MAX_BYTES + 1)  # +1 byte detects oversize
    if not data:
        raise AppError(400, "The uploaded file is empty.")
    return brand_service.save_logo(data)


@router.get("/logo")
def get_logo() -> FileResponse:
    path = brand_service.logo_path()
    if path is None:
        raise AppError(404, "No logo has been uploaded.")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "no-cache"},
    )


@router.delete("/logo", response_model=BrandKitOut)
def delete_logo() -> BrandKitOut:
    return brand_service.delete_logo()

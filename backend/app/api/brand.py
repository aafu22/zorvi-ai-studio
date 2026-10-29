from fastapi import APIRouter, Depends, File, Response, UploadFile
from fastapi.responses import FileResponse

from app.api.auth import get_current_user
from app.core.errors import AppError
from app.schemas.auth import UserOut
from app.schemas.brand import BrandKitIn, BrandKitOut
from app.services import brand_service

# Every route needs a signed-in user and only ever touches that user's own Brand Kit.
router = APIRouter(prefix="/brand-kit", tags=["brand-kit"], dependencies=[Depends(get_current_user)])


@router.get("", response_model=BrandKitOut)
def get_brand_kit(user: UserOut = Depends(get_current_user)) -> BrandKitOut:
    return brand_service.get_kit(user.id)


@router.put("", response_model=BrandKitOut)
def save_brand_kit(kit: BrandKitIn, user: UserOut = Depends(get_current_user)) -> BrandKitOut:
    return brand_service.save_kit(user.id, kit)


@router.delete("", status_code=204)
def reset_brand_kit(user: UserOut = Depends(get_current_user)) -> Response:
    """Remove the saved settings and the logo."""
    brand_service.delete_kit(user.id)
    return Response(status_code=204)


@router.post("/logo", response_model=BrandKitOut)
async def upload_logo(file: UploadFile = File(...), user: UserOut = Depends(get_current_user)) -> BrandKitOut:
    data = await file.read(brand_service.LOGO_MAX_BYTES + 1)  # +1 byte detects oversize
    if not data:
        raise AppError(400, "The uploaded file is empty.")
    return brand_service.save_logo(user.id, data)


@router.get("/logo")
def get_logo(user: UserOut = Depends(get_current_user)) -> FileResponse:
    path = brand_service.logo_path(user.id)
    if path is None:
        raise AppError(404, "No logo has been uploaded.")
    return FileResponse(
        path,
        media_type="image/png",
        headers={"X-Content-Type-Options": "nosniff", "Cache-Control": "private, no-cache"},
    )


@router.delete("/logo", response_model=BrandKitOut)
def delete_logo(user: UserOut = Depends(get_current_user)) -> BrandKitOut:
    return brand_service.delete_logo(user.id)

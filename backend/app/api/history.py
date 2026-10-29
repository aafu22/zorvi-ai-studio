from fastapi import APIRouter, Depends, Response
from fastapi.responses import FileResponse

from app.api.auth import get_current_user
from app.schemas.auth import UserOut
from app.schemas.history import CampaignSummary, OpenCampaignResponse, SaveCampaignRequest
from app.services import history_service

# Every route needs a signed-in user and only ever touches that user's own projects.
router = APIRouter(prefix="/history", tags=["history"], dependencies=[Depends(get_current_user)])

# "private": the response is for one signed-in user, so shared caches must not keep it.
_IMAGE_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"}
_MEDIA = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@router.get("", response_model=list[CampaignSummary])
def list_history(user: UserOut = Depends(get_current_user)) -> list[CampaignSummary]:
    return history_service.list_campaigns(user.id)


@router.post("", response_model=CampaignSummary, status_code=201)
def save_to_history(request: SaveCampaignRequest, user: UserOut = Depends(get_current_user)) -> CampaignSummary:
    return history_service.save_campaign(user.id, request)


@router.post("/{campaign_id}/open", response_model=OpenCampaignResponse)
def open_from_history(campaign_id: int, user: UserOut = Depends(get_current_user)) -> OpenCampaignResponse:
    return history_service.open_campaign(user.id, campaign_id)


@router.get("/{campaign_id}/thumbnail")
def get_thumbnail(campaign_id: int, user: UserOut = Depends(get_current_user)) -> FileResponse:
    return FileResponse(
        history_service.get_thumbnail(user.id, campaign_id), media_type="image/jpeg", headers=_IMAGE_HEADERS
    )


@router.get("/{campaign_id}/photo")
def get_photo(campaign_id: int, user: UserOut = Depends(get_current_user)) -> FileResponse:
    path = history_service.get_photo(user.id, campaign_id)
    return FileResponse(
        path,
        media_type=_MEDIA.get(path.suffix.lstrip("."), "application/octet-stream"),
        headers=_IMAGE_HEADERS,
    )


@router.delete("/{campaign_id}", status_code=204)
def delete_from_history(campaign_id: int, user: UserOut = Depends(get_current_user)) -> Response:
    history_service.delete_campaign(user.id, campaign_id)
    return Response(status_code=204)

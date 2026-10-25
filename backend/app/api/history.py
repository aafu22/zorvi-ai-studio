from fastapi import APIRouter, Response
from fastapi.responses import FileResponse

from app.schemas.history import CampaignSummary, OpenCampaignResponse, SaveCampaignRequest
from app.services import history_service

router = APIRouter(prefix="/history", tags=["history"])

_IMAGE_HEADERS = {"X-Content-Type-Options": "nosniff", "Cache-Control": "private, max-age=300"}
_MEDIA = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


@router.get("", response_model=list[CampaignSummary])
def list_history() -> list[CampaignSummary]:
    return history_service.list_campaigns()


@router.post("", response_model=CampaignSummary, status_code=201)
def save_to_history(request: SaveCampaignRequest) -> CampaignSummary:
    return history_service.save_campaign(request)


@router.post("/{campaign_id}/open", response_model=OpenCampaignResponse)
def open_from_history(campaign_id: int) -> OpenCampaignResponse:
    return history_service.open_campaign(campaign_id)


@router.get("/{campaign_id}/thumbnail")
def get_thumbnail(campaign_id: int) -> FileResponse:
    return FileResponse(history_service.get_thumbnail(campaign_id), media_type="image/jpeg", headers=_IMAGE_HEADERS)


@router.get("/{campaign_id}/photo")
def get_photo(campaign_id: int) -> FileResponse:
    path = history_service.get_photo(campaign_id)
    return FileResponse(
        path,
        media_type=_MEDIA.get(path.suffix.lstrip("."), "application/octet-stream"),
        headers=_IMAGE_HEADERS,
    )


@router.delete("/{campaign_id}", status_code=204)
def delete_from_history(campaign_id: int) -> Response:
    history_service.delete_campaign(campaign_id)
    return Response(status_code=204)

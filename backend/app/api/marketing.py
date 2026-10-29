from fastapi import APIRouter, Depends

from app.api.auth import get_ai_user
from app.schemas.auth import UserOut
from app.schemas.marketing import MarketingRequest, MarketingResponse
from app.services.marketing import marketing_service

router = APIRouter(prefix="/marketing", tags=["marketing"])


# Plain `def`: FastAPI runs it in a worker thread, which suits the blocking Gemini call.
@router.post("/generate", response_model=MarketingResponse)
def generate(request: MarketingRequest, _user: UserOut = Depends(get_ai_user)) -> MarketingResponse:
    """AI-written marketing kit (or one section of it).

    Needs a signed-in user (rate limited, because every call uses the Gemini quota) and GEMINI_API_KEY;
    fails with a clear message otherwise.
    """
    return marketing_service.generate_marketing(request)


@router.post("/template", response_model=MarketingResponse)
def template(request: MarketingRequest) -> MarketingResponse:
    """Rule-based draft, labelled template-based. Works with no API key."""
    return marketing_service.template_marketing(request)

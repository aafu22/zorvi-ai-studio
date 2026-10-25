from fastapi import APIRouter

from app.schemas.copy import CopyRequest, CopyResponse
from app.services.copywriting.registry import get_provider

router = APIRouter(prefix="/copy", tags=["copy"])


# Plain `def`: runs in FastAPI's worker thread pool, which suits a future blocking LLM call.
@router.post("/generate", response_model=CopyResponse)
def generate_copy(request: CopyRequest) -> CopyResponse:
    """Generate captions, hashtags, descriptions, promo copy and CTAs.

    The response's `provider.is_ai` says whether a language model wrote it.
    The built-in provider is template-based and always reports is_ai = false.
    """
    return get_provider(request.provider).generate(request)

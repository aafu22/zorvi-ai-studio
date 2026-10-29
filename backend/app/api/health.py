from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.health import Capabilities, HealthResponse

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Liveness check that also reports which optional features are available."""
    settings = get_settings()
    return HealthResponse(
        status="ok",
        app=settings.app_name,
        version=settings.app_version,
        environment=settings.app_env,
        capabilities=Capabilities(
            llm_provider=settings.llm_configured,
        ),
    )

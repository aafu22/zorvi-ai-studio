from fastapi import APIRouter

from app.schemas.demo import DemoResponse
from app.services import demo_service

router = APIRouter(prefix="/demo", tags=["demo"])


@router.post("/start", response_model=DemoResponse)
def start_demo() -> DemoResponse:
    """Load the built-in sample product. No account and no upload needed."""
    return demo_service.start_demo()

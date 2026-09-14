from fastapi import APIRouter

from app.api.schemas import HealthResponse
from app.core.config import get_settings

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service="trustid-api", environment=settings.app_env)

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import text

from app.api.schemas import HealthResponse
from app.core.config import get_settings
from app.db.session import SessionLocal

router = APIRouter(tags=["system"])


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    settings = get_settings()
    return HealthResponse(status="ok", service="trustid-api", environment=settings.app_env, version="0.1.0", checks={"process": "ok"})


@router.get("/readiness", response_model=HealthResponse)
def readiness() -> HealthResponse:
    """Report whether the API can reach its required relational database.

    Optional providers remain explicit NOT_AVAILABLE capabilities and are not
    allowed to make the process appear dead. No dependency details or secrets
    are returned to callers.
    """
    settings = get_settings()
    db = SessionLocal()
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Service dependencies are not ready.") from exc
    finally:
        db.close()
    return HealthResponse(status="ready", service="trustid-api", environment=settings.app_env, version="0.1.0", checks={"database": "ok"})

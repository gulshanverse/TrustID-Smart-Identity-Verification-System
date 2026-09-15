import logging
import uuid
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.responses import Response

from app.api.v1.analytics import router as analytics_router
from app.api.v1.audit import router as audit_router
from app.api.v1.auth import router as auth_router
from app.api.v1.cases import router as cases_router
from app.api.v1.console import router as console_router
from app.api.v1.documents import documents_router
from app.api.v1.documents import router as document_router
from app.api.v1.face import router as face_router
from app.api.v1.health import router as health_router
from app.api.v1.intelligence import router as intelligence_router
from app.api.v1.ocr import router as ocr_router
from app.api.v1.reports import router as reports_router
from app.api.v1.tampering import router as tampering_router
from app.core.config import get_settings
from app.domain.documents import ObjectStorage, S3ObjectStorage, StoredObject

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
logger = logging.getLogger("trustid.api")
settings = get_settings()


class UnavailableStorage(ObjectStorage):
    def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
        raise RuntimeError("Document storage is not configured in this environment.")

    def delete(self, key: str) -> None:
        return None

    def get(self, key: str) -> bytes:
        raise RuntimeError("Document storage is not configured in this environment.")


def initialize_storage() -> ObjectStorage:
    try:
        return S3ObjectStorage(
            settings.object_storage_endpoint,
            settings.object_storage_bucket,
            settings.object_storage_access_key,
            settings.object_storage_secret_key,
            settings.object_storage_region,
        )
    except Exception as exc:
        logger.critical(
            "object_storage_initialization_failed environment=%s error_type=%s",
            settings.app_env,
            type(exc).__name__,
        )
        if settings.app_env.lower() == "production":
            raise RuntimeError("Production object storage could not be initialized.") from exc
        logger.warning("object_storage_unavailable_local_fallback environment=%s", settings.app_env)
        return UnavailableStorage()


storage = initialize_storage()

app = FastAPI(title=settings.app_name, version="0.1.0", docs_url="/docs", redoc_url="/redoc")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


@app.middleware("http")
async def request_context(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    try:
        response = await call_next(request)
    except Exception:
        logger.exception("Unhandled request failure", extra={"request_id": request_id, "path": request.url.path})
        return JSONResponse(status_code=500, content={"code": "INTERNAL_SERVER_ERROR", "message": "An unexpected error occurred.", "request_id": request_id})
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


app.include_router(health_router, prefix="/api/v1")
app.include_router(auth_router, prefix="/api/v1")
app.include_router(console_router, prefix="/api/v1")
app.include_router(document_router, prefix="/api/v1")
app.include_router(documents_router, prefix="/api/v1")
app.include_router(ocr_router, prefix="/api/v1")
app.include_router(tampering_router, prefix="/api/v1")
app.include_router(face_router, prefix="/api/v1")
app.include_router(intelligence_router, prefix="/api/v1")
app.include_router(cases_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(audit_router, prefix="/api/v1")
app.include_router(reports_router, prefix="/api/v1")

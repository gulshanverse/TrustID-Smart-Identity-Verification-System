from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.face_schemas import FaceEvidenceResponse, FaceVerificationResponse
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.documents import safe_exception_message
from app.domain.face import DemoFaceVerificationProvider, FaceScenario, FaceVerificationResult
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.services.auth_service import AuthUser
from app.services.face_service import FaceVerificationService

MAX_PRESENTED_FACE_BYTES = 5 * 1024 * 1024
router = APIRouter(prefix="/documents", tags=["face-verification"])
logger = logging.getLogger("trustid.face.api")


def to_response(result: FaceVerificationResult) -> FaceVerificationResponse:
    return FaceVerificationResponse(id=result.id, verification_id=result.verification_id, document_id=result.document_id, status=result.status, outcome=result.outcome, similarity_score=result.similarity_score, confidence=result.confidence, provider=result.provider, provider_version=result.provider_version, summary=result.summary, failure_reason=result.failure_reason, document_face_quality=result.document_face_quality, presented_face_quality=result.presented_face_quality, face_count=result.face_count, evidence=[FaceEvidenceResponse(**item.__dict__) for item in result.evidence], created_at=result.created_at, updated_at=result.updated_at)


@router.post("/{document_id}/face-verification", response_model=FaceVerificationResponse, status_code=status.HTTP_201_CREATED)
def compare(document_id: UUID, request: Request, image: UploadFile = File(...), scenario: FaceScenario = Form(FaceScenario.MATCH), user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), db: Session = Depends(get_db)) -> FaceVerificationResponse:
    from app.main import storage
    if get_settings().face_provider.lower() != "demo":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The configured face provider is unavailable.")
    if image.content_type not in {"image/jpeg", "image/png", "image/webp"}:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Use a JPEG, PNG, or WebP presented-face image.")
    content = image.file.read(MAX_PRESENTED_FACE_BYTES + 1)
    if len(content) > MAX_PRESENTED_FACE_BYTES:
        raise HTTPException(status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail="The presented-face image exceeds the 5 MB limit.")
    service = FaceVerificationService(storage, SqlAlchemyFaceRepository(db), DemoFaceVerificationProvider())
    try:
        return to_response(service.process(document_id, user.id, content, image.content_type, scenario))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning(
            "face_processing_failed operation=compare document_id=%s request_id=%s error_type=%s error_message=%s",
            document_id,
            getattr(request.state, "request_id", "unavailable"),
            type(exc).__name__,
            safe_exception_message(exc),
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Face verification could not be completed.") from exc


@router.get("/{document_id}/face-verification", response_model=FaceVerificationResponse)
def latest(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), db: Session = Depends(get_db)) -> FaceVerificationResponse:
    service = FaceVerificationService(__import__("app.main", fromlist=["storage"]).storage, SqlAlchemyFaceRepository(db), DemoFaceVerificationProvider())
    try:
        return to_response(service.get_latest(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.ocr_schemas import OCREvidenceResponse, OCRFieldResponse, OCRResponse
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.ocr import DemoOCRProvider, OCRResult
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.services.auth_service import AuthUser
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/documents", tags=["ocr"])


def get_ocr_service(db: Session = Depends(get_db)) -> OCRService:
    from app.main import storage
    provider_name = get_settings().ocr_provider.lower()
    if provider_name != "demo":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The configured OCR provider is unavailable.")
    return OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider())


def response(result: OCRResult) -> OCRResponse:
    return OCRResponse(id=result.id, document_id=result.document_id, status=result.status, raw_text=result.raw_text, language=result.language, overall_confidence=result.overall_confidence, provider=result.provider, provider_version=result.provider_version, fields=[OCRFieldResponse(name=field.name, value=field.value, normalized_value=field.normalized_value, confidence=field.confidence, source_text=field.source_text, evidence=None if field.evidence is None else OCREvidenceResponse(**field.evidence.__dict__)) for field in result.fields], created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))


@router.post("/{document_id}/ocr", response_model=OCRResponse, status_code=status.HTTP_201_CREATED)
def process_ocr(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), service: OCRService = Depends(get_ocr_service)) -> OCRResponse:
    try:
        return response(service.process(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc


@router.get("/{document_id}/ocr", response_model=OCRResponse)
def get_ocr(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), service: OCRService = Depends(get_ocr_service)) -> OCRResponse:
    try:
        return response(service.get_latest(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

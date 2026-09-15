from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.ocr_schemas import OCREvidenceResponse, OCRFieldResponse, OCRResponse
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.documents import safe_exception_message
from app.domain.ocr import DemoOCRProvider, OCRProvider, OCRResult, ProductionOCRProvider
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.services.auth_service import AuthUser
from app.services.ocr_service import OCRService

router = APIRouter(prefix="/documents", tags=["ocr"])
logger = logging.getLogger("trustid.ocr.api")


def get_ocr_service(db: Session = Depends(get_db)) -> OCRService:
    from app.main import storage
    provider_name = get_settings().ocr_provider.lower()
    provider: OCRProvider
    if provider_name == "demo":
        provider = DemoOCRProvider()
    elif provider_name == "production":
        provider = ProductionOCRProvider()
    else:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The configured OCR provider is unavailable.")
    return OCRService(storage, SqlAlchemyOCRRepository(db), provider)


def response(result: OCRResult) -> OCRResponse:
    return OCRResponse(id=result.id, document_id=result.document_id, status=result.status, raw_text=result.raw_text, language=result.language, overall_confidence=result.overall_confidence, provider=result.provider, provider_version=result.provider_version, fields=[OCRFieldResponse(name=field.name, value=field.value, normalized_value=field.normalized_value, confidence=field.confidence, source_text=field.source_text, evidence=None if field.evidence is None else OCREvidenceResponse(**field.evidence.__dict__)) for field in result.fields], quality=result.quality.as_dict(), mrz=result.mrz.as_dict(), field_consistency=list(result.field_consistency), created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))


@router.post("/{document_id}/ocr", response_model=OCRResponse, status_code=status.HTTP_201_CREATED)
def process_ocr(document_id: UUID, request: Request, user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), service: OCRService = Depends(get_ocr_service)) -> OCRResponse:
    try:
        return response(service.process(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning(
            "ocr_processing_failed operation=process document_id=%s request_id=%s error_type=%s error_message=%s",
            document_id,
            getattr(request.state, "request_id", "unavailable"),
            type(exc).__name__,
            safe_exception_message(exc),
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="OCR processing could not be completed.") from exc


@router.get("/{document_id}/ocr", response_model=OCRResponse)
def get_ocr(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), service: OCRService = Depends(get_ocr_service)) -> OCRResponse:
    try:
        return response(service.get_latest(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

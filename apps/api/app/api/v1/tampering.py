from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.tampering_schemas import (
    TamperingEvidenceResponse,
    TamperingFindingResponse,
    TamperingRequest,
    TamperingResponse,
)
from app.core.config import get_settings
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.documents import safe_exception_message
from app.domain.tampering import DemoTamperingProvider, TamperingResult
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.auth_service import AuthUser
from app.services.tampering_service import TamperingService

router = APIRouter(prefix="/documents", tags=["tampering"])
logger = logging.getLogger("trustid.tampering.api")


def to_response(result: TamperingResult) -> TamperingResponse:
    return TamperingResponse(id=result.id, document_id=result.document_id, status=result.status, technical_signal_score=result.technical_signal_score, overall_confidence=result.overall_confidence, provider=result.provider, provider_version=result.provider_version, summary=result.summary, findings=[TamperingFindingResponse(id=finding.id, finding_type=finding.finding_type, severity=finding.severity, confidence=finding.confidence, title=finding.title, description=finding.description, related_ocr_field=finding.related_ocr_field, evidence=[TamperingEvidenceResponse(**evidence.__dict__) for evidence in finding.evidence]) for finding in result.findings], created_at=result.created_at, updated_at=result.updated_at)


@router.post("/{document_id}/tampering", response_model=TamperingResponse, status_code=status.HTTP_201_CREATED)
def analyze(document_id: UUID, request: TamperingRequest, http_request: Request, user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), db: Session = Depends(get_db)) -> TamperingResponse:
    from app.main import storage
    if get_settings().tampering_provider.lower() != "demo":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The configured tampering provider is unavailable.")
    service = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider(request.scenario))
    try:
        return to_response(service.process(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        logger.warning(
            "tampering_processing_failed operation=analyze document_id=%s request_id=%s error_type=%s error_message=%s",
            document_id,
            getattr(http_request.state, "request_id", "unavailable"),
            type(exc).__name__,
            safe_exception_message(exc),
        )
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Technical tampering analysis could not be completed.") from exc


@router.get("/{document_id}/tampering", response_model=TamperingResponse)
def latest(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), db: Session = Depends(get_db)) -> TamperingResponse:
    from app.main import storage
    if get_settings().tampering_provider.lower() != "demo":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The configured tampering provider is unavailable.")
    service = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider())
    try:
        return to_response(service.get_latest(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

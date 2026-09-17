from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.external_schemas import ExternalVerificationResponse, ExternalVerifyRequest
from app.core.config import get_settings
from app.db.models import ExternalVerificationModel
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.external_verification import (
    ExternalVerificationQuery,
    MockExternalVerificationProvider,
    ProductionExternalVerificationProvider,
)
from app.repositories.intelligence_repository import SqlAlchemyIntelligenceRepository
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/verifications", tags=["external-verification"])


def _provider():
    settings = get_settings()
    if settings.external_verification_provider.lower() == "demo":
        return MockExternalVerificationProvider()
    return ProductionExternalVerificationProvider(configured=False)


def _response(verification_id: UUID, result) -> ExternalVerificationResponse:
    return ExternalVerificationResponse(
        verification_id=verification_id,
        status=result.status.value,
        provider=result.provider,
        provider_version=result.provider_version,
        reason=result.reason,
        query_reference=result.query_reference,
        response_timestamp=result.response_timestamp,
        demo=result.demo,
    )


@router.post("/{verification_id}/external/verify", response_model=ExternalVerificationResponse)
def verify(
    verification_id: UUID,
    request: ExternalVerifyRequest,
    user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)),
    db: Session = Depends(get_db),
) -> ExternalVerificationResponse:
    document = SqlAlchemyIntelligenceRepository(db).get_document_for_verification_owner(
        verification_id, user.id
    )
    if document is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification not found.")
    existing = db.scalar(
        select(ExternalVerificationModel)
        .where(ExternalVerificationModel.verification_id == verification_id)
        .order_by(ExternalVerificationModel.created_at.desc())
    )
    if existing is not None:
        from app.domain.external_verification import ExternalStatus, ExternalVerificationResult

        return _response(
            verification_id,
            ExternalVerificationResult(
                ExternalStatus(existing.status),
                existing.provider,
                existing.provider_version,
                existing.reason,
                existing.query_reference,
                existing.response_timestamp,
                existing.demo,
            ),
        )
    query = ExternalVerificationQuery(
        request.document_type, request.document_number, request.country_code
    )
    result = _provider().verify(query)
    db.add(
        ExternalVerificationModel(
            verification_id=verification_id,
            status=result.status.value,
            provider=result.provider,
            provider_version=result.provider_version,
            reason=result.reason,
            query_reference=result.query_reference,
            response_timestamp=result.response_timestamp,
            demo=result.demo,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
    return _response(verification_id, result)

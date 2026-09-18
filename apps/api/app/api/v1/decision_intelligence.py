from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.decision_intelligence_schemas import *
from app.api.dependencies import require_permission
from app.db.models import AuditEventModel, ExternalVerificationModel
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.decision_intelligence import DecisionIntelligenceResult, DecisionIntelligenceService
from app.domain.evidence import correlate
from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.unavailable import (
    unavailable_face,
    unavailable_ocr,
    unavailable_tampering,
    unavailable_validation,
)
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.repositories.intelligence_repository import SqlAlchemyIntelligenceRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.auth_service import AuthUser
from app.services.verification_analysis import VerificationAnalysisService

router = APIRouter(prefix="/verifications", tags=["decision-intelligence"])


def _build(verification_id: UUID, user: AuthUser, db: Session) -> DecisionIntelligenceResult:
    intelligence = SqlAlchemyIntelligenceRepository(db)
    document = intelligence.get_document_for_verification_owner(verification_id, user.id)
    risk = intelligence.latest_risk(verification_id, user.id)
    validation = None if document is None else intelligence.latest_validation(document.id)
    ocr = (
        None
        if document is None
        else SqlAlchemyOCRRepository(db).get_latest_for_owner(document.id, user.id)
    )
    tampering = (
        None
        if document is None
        else SqlAlchemyTamperingRepository(db).get_latest_for_owner(document.id, user.id)
    )
    face = (
        None
        if document is None
        else SqlAlchemyFaceRepository(db).get_latest_for_owner(document.id, user.id)
    )
    if document is None or risk is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Decision intelligence is unavailable because the authorized analysis is incomplete.",
        )
    if ocr is None:
        ocr = unavailable_ocr(verification_id, document.id)
    if validation is None:
        validation = unavailable_validation(verification_id, document.id)
    if tampering is None:
        tampering = unavailable_tampering(verification_id, document.id)
    if face is None:
        face = unavailable_face(verification_id, document.id)
    external_model = db.scalar(
        select(ExternalVerificationModel)
        .where(ExternalVerificationModel.verification_id == verification_id)
        .order_by(ExternalVerificationModel.created_at.desc())
    )
    external = (
        None
        if external_model is None
        else ExternalVerificationResult(
            ExternalStatus(external_model.status),
            external_model.provider,
            external_model.provider_version,
            external_model.reason,
            external_model.query_reference,
            external_model.response_timestamp,
            external_model.demo,
        )
    )
    cross_document_findings = VerificationAnalysisService(db, user.id).cross_document_findings(verification_id)
    correlation = correlate(verification_id, ocr, validation, tampering, face, risk, external, cross_document_findings)
    return DecisionIntelligenceService().build(
        verification_id, ocr, validation, tampering, face, risk, correlation, external
    )


def _response(result: DecisionIntelligenceResult) -> DecisionIntelligenceResponse:
    return DecisionIntelligenceResponse(
        verification_id=result.verification_id,
        status=result.status,
        version=result.version,
        generated_at=result.generated_at,
        analysis_fingerprint=result.analysis_fingerprint,
        evidence_summary=[
            DecisionEvidenceResponse(
                evidence_id=i.evidence_id,
                category=i.category,
                source=i.source,
                status=i.status,
                severity=i.severity,
                explanation=i.explanation,
                provider=i.provider,
                version=i.version,
                rule_id=i.rule_id,
            )
            for i in result.evidence_summary
        ],
        contradictions=[
            ContradictionResponse(
                code=i.code,
                severity=i.severity,
                evidence_ids=list(i.evidence_ids),
                explanation=i.explanation,
                provenance=i.provenance,
            )
            for i in result.contradictions
        ],
        review_priorities=[
            ReviewPriorityResponse(
                priority=i.priority.value,
                code=i.code,
                explanation=i.explanation,
                evidence_ids=list(i.evidence_ids),
            )
            for i in result.review_priorities
        ],
        missing_information=[
            MissingInformationResponse(code=i.code, status=i.status, explanation=i.explanation)
            for i in result.missing_information
        ],
        risk_context=RiskContextResponse(
            score=result.risk_context.score,
            band=result.risk_context.band,
            assessment_version=result.risk_context.assessment_version,
            factors=list(result.risk_context.factors),
        ),
        provenance=list(result.provenance),
    )


@router.get("/{verification_id}/decision-intelligence", response_model=DecisionIntelligenceResponse)
def get_decision_intelligence(
    verification_id: UUID,
    user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)),
    db: Session = Depends(get_db),
) -> DecisionIntelligenceResponse:
    return _response(_build(verification_id, user, db))


@router.post(
    "/{verification_id}/decision-intelligence", response_model=DecisionIntelligenceResponse
)
def generate_decision_intelligence(
    verification_id: UUID,
    user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)),
    db: Session = Depends(get_db),
) -> DecisionIntelligenceResponse:
    result = _build(verification_id, user, db)
    existing = db.scalar(
        select(AuditEventModel).where(
            AuditEventModel.verification_id == verification_id,
            AuditEventModel.actor_id == user.id,
            AuditEventModel.event_type == "DECISION_INTELLIGENCE_COMPLETED",
        )
    )
    if existing is None:
        db.add(
            AuditEventModel(
                event_type="DECISION_INTELLIGENCE_COMPLETED",
                actor_id=user.id,
                verification_id=verification_id,
                status=result.status,
                provider=result.version,
                created_at=datetime.now(UTC),
            )
        )
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
    return _response(result)

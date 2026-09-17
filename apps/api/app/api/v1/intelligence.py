from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.intelligence_schemas import (
    EvidenceProvenanceResponse,
    EvidenceResponse,
    ModuleStatusResponse,
    RiskFactorResponse,
    RiskResponse,
    ValidationFindingResponse,
    ValidationResponse,
    VerificationAnalysisResponse,
    VerificationFindingResponse,
)
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.evidence import correlate
from app.domain.risk import RiskAssessmentResult
from app.domain.unavailable import (
    unavailable_face,
    unavailable_ocr,
    unavailable_tampering,
    unavailable_validation,
)
from app.domain.validation import DocumentValidationResult
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.repositories.intelligence_repository import SqlAlchemyIntelligenceRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.auth_service import AuthUser
from app.services.verification_analysis import (
    VerificationAnalysisResult,
    VerificationAnalysisService,
)

router = APIRouter(prefix="/verifications", tags=["verification-analysis"])


def risk_response(result: RiskAssessmentResult) -> RiskResponse:
    return RiskResponse(id=result.id, verification_id=result.verification_id, status=result.status.value, risk_score=result.risk_score, risk_level=result.risk_level, recommendation=result.recommendation, confidence=result.confidence, summary=result.summary, assessment_version=result.assessment_version, factors=[RiskFactorResponse(name=item.name, source_module=item.source_module, severity=item.severity, contribution=item.contribution, explanation=item.explanation, evidence_reference=item.evidence_reference) for item in result.factors])


def validation_response(result: DocumentValidationResult) -> ValidationResponse:
    return ValidationResponse(id=result.id, document_id=result.document_id, status=result.status, provider=result.provider, provider_version=result.provider_version, summary=result.summary, findings=[ValidationFindingResponse(name=item.name, severity=item.severity, passed=item.passed, explanation=item.explanation, reference=item.reference, rule_id=item.rule_id, rule_version=item.rule_version, field=item.field, observed=item.observed, expected=item.expected) for item in result.findings])


def analysis_response(result: VerificationAnalysisResult) -> VerificationAnalysisResponse:
    modules = [ModuleStatusResponse(name="OCR", status=result.ocr.status.value, summary="Structured text extraction completed."), ModuleStatusResponse(name="Document validation", status=result.validation.status.value, summary=result.validation.summary), ModuleStatusResponse(name="Tampering", status=result.tampering.status.value, summary=result.tampering.summary), ModuleStatusResponse(name="Face verification", status=result.face.outcome.value, summary=result.face.summary), ModuleStatusResponse(name="Risk assessment", status=result.risk.risk_level.value, summary=result.risk.recommendation)]
    evidence = [EvidenceResponse(evidence_id=item.evidence_id, source_module=item.source_module, evidence_type=item.evidence_type, status=item.status.value, severity=item.severity.value, confidence=item.confidence, score=item.score, explanation=item.explanation, reason_code=item.reason_code, provenance=EvidenceProvenanceResponse(module=item.provenance.module, provider=item.provenance.provider, version=item.provenance.version, rule=item.provenance.rule), created_at=item.created_at) for item in result.correlation.evidence]
    findings = [VerificationFindingResponse(finding_id=item.finding_id, code=item.code, status=item.status.value, severity=item.severity.value, title=item.title, explanation=item.explanation, evidence_ids=list(item.evidence_ids), provenance=EvidenceProvenanceResponse(module=item.provenance.module, provider=item.provenance.provider, version=item.provenance.version, rule=item.provenance.rule), risk_contribution=item.risk_contribution, created_at=item.created_at) for item in result.correlation.findings]
    partial = result.ocr.status.value != "COMPLETED" or result.tampering.status.value != "COMPLETED" or result.face.outcome.value == "NOT_AVAILABLE" or result.validation.status.value == "UNAVAILABLE"
    return VerificationAnalysisResponse(verification_id=result.verification_id, document_id=result.document_id, status="PARTIAL" if partial else "COMPLETED", modules=modules, validation=validation_response(result.validation), risk=risk_response(result.risk), correlation_summary=result.correlation.summary, evidence=evidence, findings=findings)


def latest_result(verification_id: UUID, user: AuthUser, db: Session) -> VerificationAnalysisResponse:
    intelligence = SqlAlchemyIntelligenceRepository(db)
    document = intelligence.get_document_for_verification_owner(verification_id, user.id)
    risk = intelligence.latest_risk(verification_id, user.id)
    validation = None if document is None else intelligence.latest_validation(document.id)
    ocr = None if document is None else SqlAlchemyOCRRepository(db).get_latest_for_owner(document.id, user.id)
    tampering = None if document is None else SqlAlchemyTamperingRepository(db).get_latest_for_owner(document.id, user.id)
    face = None if document is None else SqlAlchemyFaceRepository(db).get_latest_for_owner(document.id, user.id)
    if document is None or risk is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Verification analysis result not found or is incomplete.")
    if validation is None:
        validation = unavailable_validation(verification_id, document.id)
    if ocr is None:
        ocr = unavailable_ocr(verification_id, document.id)
    if tampering is None:
        tampering = unavailable_tampering(verification_id, document.id)
    if face is None:
        face = unavailable_face(verification_id, document.id)
    return analysis_response(VerificationAnalysisResult(verification_id, document.id, ocr, validation, tampering, face, risk, correlate(verification_id, ocr, validation, tampering, face, risk)))


@router.post("/{verification_id}/analyze", response_model=VerificationAnalysisResponse, status_code=status.HTTP_201_CREATED)
def analyze(verification_id: UUID, user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), db: Session = Depends(get_db)) -> VerificationAnalysisResponse:
    try:
        return analysis_response(VerificationAnalysisService(db, user.id).analyze(verification_id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{verification_id}/result", response_model=VerificationAnalysisResponse)
def result(verification_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), db: Session = Depends(get_db)) -> VerificationAnalysisResponse:
    return latest_result(verification_id, user, db)


@router.get("/{verification_id}/risk", response_model=RiskResponse)
def risk(verification_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), db: Session = Depends(get_db)) -> RiskResponse:
    return latest_result(verification_id, user, db).risk

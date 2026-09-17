from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    AuditEventModel,
    DocumentModel,
    DocumentValidationFindingModel,
    DocumentValidationModel,
    RiskAssessmentModel,
    RiskFactorModel,
    VerificationModel,
)
from app.domain.risk import RiskAssessmentResult, RiskFactor, RiskSeverity
from app.domain.validation import (
    DocumentValidationResult,
    ValidationFinding,
    ValidationSeverity,
    ValidationStatus,
)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def validation_from_model(model: DocumentValidationModel) -> DocumentValidationResult:
    findings = tuple(ValidationFinding(item.name, ValidationSeverity(item.severity), item.passed, item.explanation, item.reference, item.rule_id, item.rule_version, item.field, item.observed, item.expected) for item in model.findings)
    return DocumentValidationResult(model.id, model.document_id, ValidationStatus(model.status), model.provider, model.provider_version, model.summary, findings, _iso(model.created_at), _iso(model.updated_at))


def risk_from_model(model: RiskAssessmentModel) -> RiskAssessmentResult:
    factors = tuple(RiskFactor(item.factor_name, item.source_module, RiskSeverity(item.severity), item.contribution, item.explanation, item.evidence_reference) for item in model.factors)
    from app.domain.risk import RiskAssessmentStatus, RiskLevel
    return RiskAssessmentResult(model.id, model.verification_id, RiskAssessmentStatus(model.status), model.risk_score, RiskLevel(model.risk_level), model.recommendation, model.confidence, model.summary, model.assessment_version, factors, _iso(model.created_at), _iso(model.updated_at))


class SqlAlchemyIntelligenceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_document_for_verification_owner(self, verification_id: UUID, owner_id: UUID) -> DocumentModel | None:
        return self.db.scalar(select(DocumentModel).join(VerificationModel).where(DocumentModel.verification_id == verification_id, VerificationModel.id == verification_id, VerificationModel.owner_id == owner_id, DocumentModel.status != "DELETED").order_by(DocumentModel.created_at.desc()))

    def add_validation(self, result: DocumentValidationResult, actor_id: UUID) -> None:
        model = DocumentValidationModel(id=result.id, document_id=result.document_id, status=result.status.value, provider=result.provider, provider_version=result.provider_version, summary=result.summary, created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))
        model.findings.extend(DocumentValidationFindingModel(id=uuid4(), validation_id=result.id, name=item.name, severity=item.severity.value, passed=item.passed, explanation=item.explanation, reference=item.reference, rule_id=item.rule_id, rule_version=item.rule_version, field=item.field, observed=item.observed, expected=item.expected) for item in result.findings)
        self.db.add(model)
        self.db.flush()
        document = self.db.get(DocumentModel, result.document_id)
        if document is not None:
            self.db.add(AuditEventModel(event_type="DOCUMENT_VALIDATION_COMPLETED", actor_id=actor_id, verification_id=document.verification_id, document_id=result.document_id, validation_id=result.id, provider=result.provider, status=result.status.value, created_at=datetime.now(UTC)))

    def add_risk(self, result: RiskAssessmentResult, actor_id: UUID) -> None:
        model = RiskAssessmentModel(id=result.id, verification_id=result.verification_id, status=result.status.value, risk_score=result.risk_score, risk_level=result.risk_level.value, recommendation=result.recommendation, confidence=result.confidence, summary=result.summary, assessment_version=result.assessment_version, created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))
        model.factors.extend(RiskFactorModel(id=uuid4(), risk_assessment_id=result.id, factor_name=item.name, source_module=item.source_module, severity=item.severity.value, contribution=item.contribution, explanation=item.explanation, evidence_reference=item.evidence_reference, created_at=datetime.now(UTC)) for item in result.factors)
        self.db.add(model)
        self.db.flush()
        document = self.get_document_for_verification_owner(result.verification_id, actor_id)
        self.db.add(AuditEventModel(event_type="RISK_ASSESSMENT_COMPLETED", actor_id=actor_id, verification_id=result.verification_id, document_id=None if document is None else document.id, risk_assessment_id=result.id, status=result.status.value, created_at=datetime.now(UTC)))

    def latest_risk(self, verification_id: UUID, owner_id: UUID) -> RiskAssessmentResult | None:
        model = self.db.scalar(select(RiskAssessmentModel).join(VerificationModel).where(RiskAssessmentModel.verification_id == verification_id, VerificationModel.owner_id == owner_id).options(joinedload(RiskAssessmentModel.factors)).order_by(RiskAssessmentModel.created_at.desc()))
        return None if model is None else risk_from_model(model)

    def latest_validation(self, document_id: UUID) -> DocumentValidationResult | None:
        model = self.db.scalar(select(DocumentValidationModel).where(DocumentValidationModel.document_id == document_id).options(joinedload(DocumentValidationModel.findings)).order_by(DocumentValidationModel.created_at.desc()))
        return None if model is None else validation_from_model(model)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

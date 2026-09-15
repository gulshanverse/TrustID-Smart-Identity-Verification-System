from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    AuditEventModel,
    DocumentModel,
    OCRResultModel,
    TamperingEvidenceModel,
    TamperingFindingModel,
    TamperingResultModel,
    VerificationModel,
)
from app.domain.tampering import (
    FindingSeverity,
    FindingType,
    TamperingEvidence,
    TamperingFinding,
    TamperingResult,
    TamperingStatus,
)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _result(model: TamperingResultModel) -> TamperingResult:
    findings = []
    for finding in model.findings:
        evidence = tuple(TamperingEvidence(item.evidence_type, item.page, item.region, item.description, item.source_reference, item.technical_signal, item.confidence) for item in finding.evidence)
        findings.append(TamperingFinding(finding.id, FindingType(finding.finding_type), FindingSeverity(finding.severity), finding.confidence, finding.title, finding.description, evidence, finding.related_ocr_field))
    return TamperingResult(model.id, model.document_id, TamperingStatus(model.status), model.technical_signal_score, model.overall_confidence, model.provider, model.provider_version, model.summary, tuple(findings), _iso(model.created_at), _iso(model.updated_at))


class SqlAlchemyTamperingRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_document_for_owner(self, document_id: UUID, owner_id: UUID) -> DocumentModel | None:
        return self.db.scalar(select(DocumentModel).join(VerificationModel).where(DocumentModel.id == document_id, VerificationModel.owner_id == owner_id, DocumentModel.status.in_(["READY_FOR_ANALYSIS", "OCR_COMPLETE"])))

    def get_latest_ocr(self, document_id: UUID, owner_id: UUID) -> OCRResultModel | None:
        return self.db.scalar(select(OCRResultModel).join(DocumentModel).join(VerificationModel).where(OCRResultModel.document_id == document_id, VerificationModel.owner_id == owner_id).order_by(OCRResultModel.created_at.desc()))

    def add_audit(self, event_type: str, actor_id: UUID, document_id: UUID, status: str, result_id: UUID | None, provider: str) -> None:
        document = self.db.get(DocumentModel, document_id)
        if document is None:
            raise LookupError("Document not found.")
        self.db.add(AuditEventModel(event_type=event_type, actor_id=actor_id, verification_id=document.verification_id, document_id=document_id, tampering_result_id=result_id, provider=provider, status=status, created_at=datetime.now(UTC)))

    def add_result(self, result: TamperingResult, actor_id: UUID) -> None:
        model = TamperingResultModel(id=result.id, document_id=result.document_id, status=result.status.value, technical_signal_score=result.technical_signal_score, overall_confidence=result.overall_confidence, provider=result.provider, provider_version=result.provider_version, summary=result.summary, created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))
        for finding in result.findings:
            finding_model = TamperingFindingModel(id=finding.id, tampering_result_id=result.id, finding_type=finding.finding_type.value, severity=finding.severity.value, confidence=finding.confidence, title=finding.title, description=finding.description, related_ocr_field=finding.related_ocr_field)
            finding_model.evidence.extend(TamperingEvidenceModel(id=uuid4(), tampering_finding_id=finding.id, evidence_type=evidence.evidence_type, page=evidence.page, region=evidence.region, description=evidence.description, source_reference=evidence.source_reference, technical_signal=evidence.technical_signal, confidence=evidence.confidence) for evidence in finding.evidence)
            model.findings.append(finding_model)
        self.db.add(model)
        self.db.flush()
        self.add_audit("TAMPERING_COMPLETED", actor_id, result.document_id, result.status.value, result.id, result.provider)

    def get_latest_for_owner(self, document_id: UUID, owner_id: UUID) -> TamperingResult | None:
        model = self.db.scalar(select(TamperingResultModel).join(DocumentModel).join(VerificationModel).where(TamperingResultModel.document_id == document_id, VerificationModel.owner_id == owner_id).options(joinedload(TamperingResultModel.findings).joinedload(TamperingFindingModel.evidence)).order_by(TamperingResultModel.created_at.desc()))
        return None if model is None else _result(model)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    AuditEventModel,
    DocumentModel,
    OCREvidenceModel,
    OCRFieldModel,
    OCRResultModel,
    VerificationModel,
)
from app.domain.ocr import OCREvidence, OCRField, OCRResult, OCRStatus


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _result(model: OCRResultModel) -> OCRResult:
    fields: list[OCRField] = []
    for field in model.fields:
        evidence = field.evidence[0] if field.evidence else None
        fields.append(OCRField(field.name, field.value, field.normalized_value, field.confidence, field.source_text, None if evidence is None else OCREvidence(evidence.page, evidence.text, evidence.start_offset, evidence.end_offset, evidence.line_index)))
    return OCRResult(model.id, model.document_id, OCRStatus(model.status), model.raw_text, model.language, model.overall_confidence, model.provider, model.provider_version, tuple(fields), _iso(model.created_at), _iso(model.updated_at))


class SqlAlchemyOCRRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_ready_document_for_owner(self, document_id: UUID, owner_id: UUID) -> DocumentModel | None:
        return self.db.scalar(select(DocumentModel).join(VerificationModel).where(DocumentModel.id == document_id, VerificationModel.owner_id == owner_id, DocumentModel.status.in_(["READY_FOR_ANALYSIS", "OCR_COMPLETE"])))

    def mark_ocr_complete(self, document_id: UUID) -> None:
        document = self.db.get(DocumentModel, document_id)
        if document is not None:
            document.status = "OCR_COMPLETE"
            document.updated_at = datetime.now(UTC)

    def add_audit(self, event_type: str, actor_id: UUID, document_id: UUID, status: str, result_id: UUID | None, provider: str) -> None:
        document = self.db.get(DocumentModel, document_id)
        if document is None:
            raise LookupError("Document not found.")
        self.db.add(AuditEventModel(event_type=event_type, actor_id=actor_id, verification_id=document.verification_id, document_id=document_id, ocr_result_id=result_id, provider=provider, status=status, created_at=datetime.now(UTC)))

    def add_result(self, result: OCRResult, actor_id: UUID) -> None:
        model = OCRResultModel(id=result.id, document_id=result.document_id, status=result.status.value, raw_text=result.raw_text, language=result.language, overall_confidence=result.overall_confidence, provider=result.provider, provider_version=result.provider_version, created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))
        for field in result.fields:
            field_model = OCRFieldModel(id=uuid4(), ocr_result_id=result.id, name=field.name, value=field.value, normalized_value=field.normalized_value, confidence=field.confidence, source_text=field.source_text)
            if field.evidence is not None:
                field_model.evidence.append(OCREvidenceModel(id=uuid4(), ocr_field_id=field_model.id, page=field.evidence.page, text=field.evidence.text, start_offset=field.evidence.start_offset, end_offset=field.evidence.end_offset, line_index=field.evidence.line_index))
            model.fields.append(field_model)
        self.db.add(model)
        self.add_audit("OCR_COMPLETED" if result.status == OCRStatus.COMPLETED else "OCR_FAILED", actor_id, result.document_id, result.status.value, result.id, result.provider)

    def get_latest_for_owner(self, document_id: UUID, owner_id: UUID) -> OCRResult | None:
        model = self.db.scalar(select(OCRResultModel).join(DocumentModel).join(VerificationModel).where(OCRResultModel.document_id == document_id, VerificationModel.owner_id == owner_id).options(joinedload(OCRResultModel.fields).joinedload(OCRFieldModel.evidence)).order_by(OCRResultModel.created_at.desc()))
        return None if model is None else _result(model)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

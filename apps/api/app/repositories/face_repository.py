from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.db.models import (
    AuditEventModel,
    DocumentModel,
    FaceVerificationEvidenceModel,
    FaceVerificationModel,
    VerificationModel,
)
from app.domain.face import (
    FaceEvidence,
    FaceOutcome,
    FaceQuality,
    FaceVerificationResult,
    FaceVerificationStatus,
)


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _result(model: FaceVerificationModel) -> FaceVerificationResult:
    evidence = tuple(FaceEvidence(item.name, item.value, item.explanation) for item in model.evidence)
    return FaceVerificationResult(model.id, model.verification_id, model.document_id, FaceVerificationStatus(model.status), FaceOutcome(model.outcome), model.similarity_score, model.confidence, model.provider, model.provider_version, model.summary, model.failure_reason, FaceQuality(model.document_face_quality), FaceQuality(model.presented_face_quality), model.face_count, evidence, _iso(model.created_at), _iso(model.updated_at))


class SqlAlchemyFaceRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get_document_for_owner(self, document_id: UUID, owner_id: UUID) -> DocumentModel | None:
        return self.db.scalar(select(DocumentModel).join(VerificationModel).where(DocumentModel.id == document_id, VerificationModel.owner_id == owner_id, DocumentModel.status.in_(["READY_FOR_ANALYSIS", "OCR_COMPLETE"])))

    def add_audit(self, event_type: str, actor_id: UUID, document_id: UUID, status: str, result_id: UUID | None, provider: str, outcome: str | None = None) -> None:
        document = self.db.get(DocumentModel, document_id)
        if document is None:
            raise LookupError("Document not found.")
        self.db.add(AuditEventModel(event_type=event_type, actor_id=actor_id, verification_id=document.verification_id, document_id=document_id, face_verification_id=result_id, provider=provider, status=status, created_at=datetime.now(UTC)))

    def add_result(self, result: FaceVerificationResult, actor_id: UUID) -> None:
        model = FaceVerificationModel(id=result.id, verification_id=result.verification_id, document_id=result.document_id, status=result.status.value, outcome=result.outcome.value, similarity_score=result.similarity_score, confidence=result.confidence, provider=result.provider, provider_version=result.provider_version, summary=result.summary, failure_reason=result.failure_reason, document_face_quality=result.document_face_quality.value, presented_face_quality=result.presented_face_quality.value, face_count=result.face_count, created_at=datetime.fromisoformat(result.created_at), updated_at=datetime.fromisoformat(result.updated_at))
        model.evidence.extend(FaceVerificationEvidenceModel(id=uuid4(), face_verification_id=result.id, name=item.name, value=item.value, explanation=item.explanation) for item in result.evidence)
        self.db.add(model)
        self.db.flush()
        self.add_audit("FACE_VERIFICATION_COMPLETED", actor_id, result.document_id, result.status.value, result.id, result.provider, result.outcome.value)

    def get_latest_for_owner(self, document_id: UUID, owner_id: UUID) -> FaceVerificationResult | None:
        model = self.db.scalar(select(FaceVerificationModel).join(DocumentModel).join(VerificationModel).where(FaceVerificationModel.document_id == document_id, VerificationModel.owner_id == owner_id).options(joinedload(FaceVerificationModel.evidence)).order_by(FaceVerificationModel.created_at.desc()))
        return None if model is None else _result(model)

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

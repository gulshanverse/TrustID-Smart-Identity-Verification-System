from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, DocumentModel, User, VerificationModel
from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType
from app.services.document_service import AuditEvent, VerificationRecord


class DocumentRepository(Protocol):
    def create_verification(self, owner_id: UUID, email: str, display_name: str) -> VerificationRecord: ...
    def get_verification_for_owner(self, verification_id: UUID, owner_id: UUID) -> VerificationRecord | None: ...
    def add_document(self, record: DocumentRecord, actor_id: UUID) -> None: ...
    def list_documents(self, verification_id: UUID) -> list[DocumentRecord]: ...
    def get_document_for_owner(self, document_id: UUID, owner_id: UUID) -> DocumentRecord | None: ...
    def delete_document(self, document_id: UUID, actor_id: UUID) -> None: ...
    def list_audit_events(self) -> list[AuditEvent]: ...
    def commit(self) -> None: ...
    def rollback(self) -> None: ...


def _iso(value: datetime) -> str:
    return value.astimezone(UTC).isoformat() if value.tzinfo else value.replace(tzinfo=UTC).isoformat()


def _record(model: DocumentModel) -> DocumentRecord:
    return DocumentRecord(UUID(str(model.id)), UUID(str(model.verification_id)), DocumentType(model.document_type), model.original_filename, model.storage_key, model.mime_type, model.file_size, model.checksum_sha256, DocumentLifecycle(model.status), _iso(model.created_at), _iso(model.updated_at))


class SqlAlchemyDocumentRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def create_verification(self, owner_id: UUID, email: str, display_name: str) -> VerificationRecord:
        # The current auth service is intentionally in-process. Keep the existing users
        # table consistent so the verification foreign key remains valid during development.
        if self.db.get(User, owner_id) is None:
            self.db.add(User(id=owner_id, email=email, display_name=display_name, password_hash="managed-by-auth-service", is_active=True))
            self.db.flush()
        now = datetime.now(UTC)
        model = VerificationModel(id=uuid4(), owner_id=owner_id, status="PENDING", created_at=now)
        self.db.add(model)
        self.db.flush()
        self.db.add(AuditEventModel(event_type="VERIFICATION_CREATED", actor_id=owner_id, verification_id=model.id, document_id=None, status="CREATED", created_at=now))
        self.db.commit()
        return VerificationRecord(model.id, model.owner_id, _iso(now))

    def get_verification_for_owner(self, verification_id: UUID, owner_id: UUID) -> VerificationRecord | None:
        model = self.db.scalar(select(VerificationModel).where(VerificationModel.id == verification_id, VerificationModel.owner_id == owner_id))
        return None if model is None else VerificationRecord(model.id, model.owner_id, _iso(model.created_at))

    def add_document(self, record: DocumentRecord, actor_id: UUID) -> None:
        model = DocumentModel(id=record.id, verification_id=record.verification_id, document_type=record.document_type.value, original_filename=record.original_filename, storage_key=record.storage_key, mime_type=record.mime_type, file_size=record.file_size, checksum_sha256=record.checksum_sha256, status=record.status.value, created_at=datetime.fromisoformat(record.created_at), updated_at=datetime.fromisoformat(record.updated_at))
        self.db.add(model)
        self.db.add(AuditEventModel(event_type="DOCUMENT_UPLOADED", actor_id=actor_id, verification_id=record.verification_id, document_id=record.id, status=record.status.value, created_at=datetime.fromisoformat(record.created_at)))

    def list_documents(self, verification_id: UUID) -> list[DocumentRecord]:
        models = self.db.scalars(select(DocumentModel).where(DocumentModel.verification_id == verification_id, DocumentModel.status != DocumentLifecycle.DELETED.value).order_by(DocumentModel.created_at)).all()
        return [_record(model) for model in models]

    def get_document_for_owner(self, document_id: UUID, owner_id: UUID) -> DocumentRecord | None:
        model = self.db.scalar(select(DocumentModel).join(VerificationModel).where(DocumentModel.id == document_id, VerificationModel.owner_id == owner_id, DocumentModel.status != DocumentLifecycle.DELETED.value))
        return None if model is None else _record(model)

    def delete_document(self, document_id: UUID, actor_id: UUID) -> None:
        model = self.db.get(DocumentModel, document_id)
        if model is None:
            raise LookupError("Document not found.")
        now = datetime.now(UTC)
        model.status = DocumentLifecycle.DELETED.value
        model.updated_at = now
        self.db.add(AuditEventModel(event_type="DOCUMENT_DELETED", actor_id=actor_id, verification_id=model.verification_id, document_id=model.id, status="DELETED", created_at=now))

    def list_audit_events(self) -> list[AuditEvent]:
        models = self.db.scalars(select(AuditEventModel).order_by(AuditEventModel.created_at)).all()
        return [AuditEvent(model.event_type, model.actor_id, model.verification_id, model.document_id, model.status, _iso(model.created_at)) for model in models]

    def commit(self) -> None:
        self.db.commit()

    def rollback(self) -> None:
        self.db.rollback()

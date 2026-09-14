from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID, uuid4

from app.domain.documents import (
    DocumentLifecycle,
    DocumentRecord,
    DocumentType,
    ObjectStorage,
    new_document_id,
    storage_key,
    validate_document_bytes,
)


@dataclass(frozen=True)
class VerificationRecord:
    id: UUID
    owner_id: UUID
    created_at: str


@dataclass(frozen=True)
class AuditEvent:
    event_type: str
    actor_id: UUID
    verification_id: UUID
    document_id: UUID | None
    status: str
    created_at: str


class DocumentService:
    def __init__(self, storage: ObjectStorage) -> None:
        self.storage = storage
        self.verifications: dict[UUID, VerificationRecord] = {}
        self.documents: dict[UUID, DocumentRecord] = {}
        self.audit_events: list[AuditEvent] = []

    def create_verification(self, actor_id: UUID) -> VerificationRecord:
        record = VerificationRecord(uuid4(), actor_id, datetime.now(UTC).isoformat())
        self.verifications[record.id] = record
        self.audit_events.append(AuditEvent("VERIFICATION_CREATED", actor_id, record.id, None, "CREATED", record.created_at))
        return record

    def ensure_access(self, verification_id: UUID, actor_id: UUID) -> VerificationRecord:
        record = self.verifications.get(verification_id)
        if record is None or record.owner_id != actor_id:
            raise LookupError("Verification not found.")
        return record

    def upload(self, verification_id: UUID, actor_id: UUID, filename: str | None, mime_type: str | None, content: bytes, document_type: DocumentType) -> DocumentRecord:
        self.ensure_access(verification_id, actor_id)
        display_name, actual_mime = validate_document_bytes(filename, mime_type, content)
        document_id = new_document_id()
        key = storage_key(verification_id, document_id, actual_mime)
        stored = self.storage.put(key, content, actual_mime)
        now = datetime.now(UTC).isoformat()
        record = DocumentRecord(document_id, verification_id, document_type, display_name, stored.key, actual_mime, stored.size, stored.checksum, DocumentLifecycle.READY_FOR_ANALYSIS, now, now)
        try:
            self.documents[document_id] = record
        except RuntimeError:
            self.storage.delete(key)
            raise RuntimeError("Document metadata could not be saved.")
        self.audit_events.append(AuditEvent("DOCUMENT_UPLOADED", actor_id, verification_id, document_id, record.status.value, now))
        return record

    def list_documents(self, verification_id: UUID, actor_id: UUID) -> list[DocumentRecord]:
        self.ensure_access(verification_id, actor_id)
        return [document for document in self.documents.values() if document.verification_id == verification_id and document.status != DocumentLifecycle.DELETED]

    def get_document(self, document_id: UUID, actor_id: UUID) -> DocumentRecord:
        record = self.documents.get(document_id)
        if record is None or record.status == DocumentLifecycle.DELETED:
            raise LookupError("Document not found.")
        self.ensure_access(record.verification_id, actor_id)
        return record

    def delete_document(self, document_id: UUID, actor_id: UUID) -> None:
        record = self.get_document(document_id, actor_id)
        self.storage.delete(record.storage_key)
        now = datetime.now(UTC).isoformat()
        self.documents[document_id] = DocumentRecord(**{**record.__dict__, "status": DocumentLifecycle.DELETED, "updated_at": now})
        self.audit_events.append(AuditEvent("DOCUMENT_DELETED", actor_id, record.verification_id, document_id, "DELETED", now))

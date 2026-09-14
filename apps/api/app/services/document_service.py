from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Protocol
from uuid import UUID

from app.domain.documents import (
    DocumentLifecycle,
    DocumentRecord,
    DocumentType,
    ObjectStorage,
    new_document_id,
    storage_key,
    validate_document_bytes,
)

logger = logging.getLogger("trustid.documents")


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


class DocumentService:
    def __init__(self, storage: ObjectStorage, repository: DocumentRepository) -> None:
        self.storage = storage
        self.repository = repository

    def create_verification(self, actor_id: UUID, email: str, display_name: str) -> VerificationRecord:
        return self.repository.create_verification(actor_id, email, display_name)

    def ensure_access(self, verification_id: UUID, actor_id: UUID) -> VerificationRecord:
        record = self.repository.get_verification_for_owner(verification_id, actor_id)
        if record is None:
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
            self.repository.add_document(record, actor_id)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            try:
                self.storage.delete(key)
            except Exception:  # noqa: BLE001
                logger.warning("document_storage_cleanup_failed")
            raise RuntimeError("Document metadata could not be saved.") from exc
        return record

    def list_documents(self, verification_id: UUID, actor_id: UUID) -> list[DocumentRecord]:
        self.ensure_access(verification_id, actor_id)
        return self.repository.list_documents(verification_id)

    def get_document(self, document_id: UUID, actor_id: UUID) -> DocumentRecord:
        record = self.repository.get_document_for_owner(document_id, actor_id)
        if record is None:
            raise LookupError("Document not found.")
        return record

    def delete_document(self, document_id: UUID, actor_id: UUID) -> None:
        record = self.get_document(document_id, actor_id)
        self.storage.delete(record.storage_key)
        try:
            self.repository.delete_document(document_id, actor_id)
            self.repository.commit()
        except Exception as exc:
            self.repository.rollback()
            raise RuntimeError("Document metadata could not be deleted.") from exc

    def audit_events(self) -> list[AuditEvent]:
        return self.repository.list_audit_events()

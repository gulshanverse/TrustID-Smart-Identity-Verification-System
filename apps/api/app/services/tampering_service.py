from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType, ObjectStorage
from app.domain.ocr import OCRResult, OCRStatus
from app.domain.tampering import (
    TamperingProvider,
    TamperingResult,
    TamperingStatus,
    new_tampering_result_id,
)
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.forensics import inspect_document


class TamperingService:
    def __init__(self, storage: ObjectStorage, repository: SqlAlchemyTamperingRepository, provider: TamperingProvider) -> None:
        self.storage = storage
        self.repository = repository
        self.provider = provider

    def process(self, document_id: UUID, actor_id: UUID) -> TamperingResult:
        document = self.repository.get_document_for_owner(document_id, actor_id)
        if document is None:
            raise LookupError("Document not found or not ready for technical analysis.")
        self.repository.add_audit("TAMPERING_STARTED", actor_id, document_id, TamperingStatus.PROCESSING.value, None, self.provider.name)
        self.repository.commit()
        try:
            content = self.storage.get(document.storage_key)
            inspect_document(content, document.mime_type)
            typed_document = DocumentRecord(document.id, document.verification_id, DocumentType(document.document_type), document.original_filename, document.storage_key, document.mime_type, document.file_size, document.checksum_sha256, DocumentLifecycle(document.status), document.created_at.isoformat(), document.updated_at.isoformat())
            latest_ocr = self.repository.get_latest_ocr(document_id, actor_id)
            ocr_context = None if latest_ocr is None else OCRResult(UUID(int=0), document_id, OCRStatus.COMPLETED, "", "", 0.0, latest_ocr.provider, latest_ocr.provider_version, (), "", "")
            score, confidence, summary, findings = self.provider.analyze(typed_document, content, ocr_context)
            now = datetime.now(UTC).isoformat()
            result = TamperingResult(new_tampering_result_id(), document_id, TamperingStatus.COMPLETED, score, confidence, self.provider.name, self.provider.version, summary, findings, now, now)
            self.repository.add_result(result, actor_id)
            self.repository.commit()
            return result
        except Exception as exc:
            self.repository.rollback()
            try:
                self.repository.add_audit("TAMPERING_FAILED", actor_id, document_id, TamperingStatus.FAILED.value, None, self.provider.name)
                self.repository.commit()
            except Exception:  # noqa: BLE001
                self.repository.rollback()
            raise RuntimeError("Technical tampering analysis could not be completed.") from exc

    def get_latest(self, document_id: UUID, actor_id: UUID) -> TamperingResult:
        result = self.repository.get_latest_for_owner(document_id, actor_id)
        if result is None:
            raise LookupError("Tampering analysis result not found.")
        return result

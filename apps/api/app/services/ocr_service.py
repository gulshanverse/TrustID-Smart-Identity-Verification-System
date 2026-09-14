from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType, ObjectStorage
from app.domain.ocr import OCRProvider, OCRResult, OCRStatus, new_ocr_result_id
from app.repositories.ocr_repository import SqlAlchemyOCRRepository


class OCRService:
    def __init__(self, storage: ObjectStorage, repository: SqlAlchemyOCRRepository, provider: OCRProvider) -> None:
        self.storage = storage
        self.repository = repository
        self.provider = provider

    def process(self, document_id: UUID, actor_id: UUID) -> OCRResult:
        document = self.repository.get_ready_document_for_owner(document_id, actor_id)
        if document is None:
            raise LookupError("Document not found or not ready for OCR.")
        self.repository.add_audit("OCR_STARTED", actor_id, document_id, OCRStatus.PROCESSING.value, None, self.provider.name)
        self.repository.commit()
        try:
            content = self.storage.get(document.storage_key)
            typed_document = DocumentRecord(document.id, document.verification_id, DocumentType(document.document_type), document.original_filename, document.storage_key, document.mime_type, document.file_size, document.checksum_sha256, DocumentLifecycle(document.status), document.created_at.isoformat(), document.updated_at.isoformat())
            raw_text, fields, confidence, language = self.provider.process(typed_document, content)
            now = datetime.now(UTC).isoformat()
            result = OCRResult(new_ocr_result_id(), document_id, OCRStatus.COMPLETED, raw_text, language, confidence, self.provider.name, self.provider.version, fields, now, now)
            self.repository.add_result(result, actor_id)
            self.repository.mark_ocr_complete(document_id)
            self.repository.commit()
            return result
        except Exception as exc:
            self.repository.rollback()
            try:
                self.repository.add_audit("OCR_FAILED", actor_id, document_id, OCRStatus.FAILED.value, None, self.provider.name)
                self.repository.commit()
            except Exception:  # noqa: BLE001
                self.repository.rollback()
            raise RuntimeError("OCR processing could not be completed.") from exc

    def get_latest(self, document_id: UUID, actor_id: UUID) -> OCRResult:
        result = self.repository.get_latest_for_owner(document_id, actor_id)
        if result is None:
            raise LookupError("OCR result not found.")
        return result

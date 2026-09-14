from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType, ObjectStorage
from app.domain.face import (
    DemoDocumentFaceExtractor,
    FaceEvidence,
    FaceQuality,
    FaceScenario,
    FaceVerificationProvider,
    FaceVerificationResult,
    FaceVerificationStatus,
    new_face_result_id,
)
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.services.forensics import inspect_document


class FaceVerificationService:
    def __init__(self, storage: ObjectStorage, repository: SqlAlchemyFaceRepository, provider: FaceVerificationProvider) -> None:
        self.storage = storage
        self.repository = repository
        self.provider = provider
        self.extractor = DemoDocumentFaceExtractor()

    def process(self, document_id: UUID, actor_id: UUID, presented_content: bytes, presented_mime: str, scenario: FaceScenario) -> FaceVerificationResult:
        document = self.repository.get_document_for_owner(document_id, actor_id)
        if document is None:
            raise LookupError("Document not found or not ready for face verification.")
        self.repository.add_audit("FACE_VERIFICATION_STARTED", actor_id, document_id, FaceVerificationStatus.PROCESSING.value, None, self.provider.name)
        self.repository.commit()
        try:
            inspect_document(presented_content, presented_mime)
            document_content = self.storage.get(document.storage_key)
            inspect_document(document_content, document.mime_type)
            typed_document = DocumentRecord(document.id, document.verification_id, DocumentType(document.document_type), document.original_filename, document.storage_key, document.mime_type, document.file_size, document.checksum_sha256, DocumentLifecycle(document.status), document.created_at.isoformat(), document.updated_at.isoformat())
            document_quality, document_explanation = self.extractor.extract(typed_document, document_content)
            if document_quality != FaceQuality.READY:
                raise ValueError(document_explanation)
            outcome, similarity, confidence, summary, failure_reason, presented_quality, face_count = self.provider.compare(document_content, presented_content, scenario)
            evidence: tuple[FaceEvidence, ...] = (FaceEvidence("document_face", "AVAILABLE", document_explanation), FaceEvidence("presented_face", "AVAILABLE" if presented_quality == FaceQuality.READY else presented_quality.value, "Presented face is processed server-side and not retained."), FaceEvidence("face_count", str(face_count if face_count is not None else "unknown"), "Demo fixture face-count signal."), FaceEvidence("threshold", str(self.provider.threshold if hasattr(self.provider, "threshold") else "provider-defined"), "Configured provider comparison threshold; not an official standard."))
            if failure_reason:
                evidence = evidence + (FaceEvidence("quality", presented_quality.value, failure_reason),)
            now = datetime.now(UTC).isoformat()
            result = FaceVerificationResult(new_face_result_id(), document.verification_id, document_id, FaceVerificationStatus.COMPLETED, outcome, similarity, confidence, self.provider.name, self.provider.version, summary, failure_reason, document_quality, presented_quality, face_count, evidence, now, now)
            self.repository.add_result(result, actor_id)
            self.repository.commit()
            return result
        except Exception as exc:
            self.repository.rollback()
            try:
                self.repository.add_audit("FACE_VERIFICATION_FAILED", actor_id, document_id, FaceVerificationStatus.FAILED.value, None, self.provider.name)
                self.repository.commit()
            except Exception:  # noqa: BLE001
                self.repository.rollback()
            raise RuntimeError("Face verification could not be completed.") from exc

    def get_latest(self, document_id: UUID, actor_id: UUID) -> FaceVerificationResult:
        result = self.repository.get_latest_for_owner(document_id, actor_id)
        if result is None:
            raise LookupError("Face verification result not found.")
        return result

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, VerificationModel
from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType
from app.domain.face import FaceVerificationResult
from app.domain.ocr import OCRResult
from app.domain.risk import RiskAssessmentResult, assess_risk
from app.domain.tampering import TamperingResult
from app.domain.validation import (
    DemoDocumentValidationProvider,
    DocumentValidationResult,
    new_validation_result_id,
)
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.repositories.intelligence_repository import SqlAlchemyIntelligenceRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository


@dataclass(frozen=True)
class VerificationAnalysisResult:
    verification_id: UUID
    document_id: UUID
    ocr: OCRResult
    validation: DocumentValidationResult
    tampering: TamperingResult
    face: FaceVerificationResult
    risk: RiskAssessmentResult


class VerificationAnalysisService:
    def __init__(self, db: Session, actor_id: UUID) -> None:
        self.db = db
        self.actor_id = actor_id
        self.intelligence = SqlAlchemyIntelligenceRepository(db)
        self.ocr = SqlAlchemyOCRRepository(db)
        self.tampering = SqlAlchemyTamperingRepository(db)
        self.face = SqlAlchemyFaceRepository(db)
        self.validation_provider = DemoDocumentValidationProvider()

    def _mark_failed(self, verification: VerificationModel, document_id: UUID | None) -> None:
        verification.status = "FAILED"
        self.db.add(AuditEventModel(event_type="VERIFICATION_ANALYSIS_FAILED", actor_id=self.actor_id, verification_id=verification.id, document_id=document_id, status="FAILED", created_at=datetime.now(UTC)))
        self.db.commit()

    def analyze(self, verification_id: UUID) -> VerificationAnalysisResult:
        document = self.intelligence.get_document_for_verification_owner(verification_id, self.actor_id)
        verification = self.db.scalar(select(VerificationModel).where(
            VerificationModel.id == verification_id, VerificationModel.owner_id == self.actor_id,
        ))
        if document is None or verification is None:
            raise LookupError("Verification not found or has no active document.")

        ocr = self.ocr.get_latest_for_owner(document.id, self.actor_id)
        tampering = self.tampering.get_latest_for_owner(document.id, self.actor_id)
        face = self.face.get_latest_for_owner(document.id, self.actor_id)
        if ocr is None or ocr.status.value != "COMPLETED":
            self._mark_failed(verification, document.id)
            raise RuntimeError("Verification analysis is unavailable because OCR has not completed.")
        if tampering is None:
            self._mark_failed(verification, document.id)
            raise RuntimeError("Verification analysis is unavailable because tampering analysis has not completed.")
        if face is None:
            self._mark_failed(verification, document.id)
            raise RuntimeError("Verification analysis is unavailable because face verification has not completed.")

        # A retry after a completed run returns the latest persisted result instead of
        # creating a second validation/risk record or inflating analytics totals.
        existing_validation = self.intelligence.latest_validation(document.id)
        existing_risk = self.intelligence.latest_risk(verification_id, self.actor_id)
        if existing_validation is not None and existing_risk is not None:
            return VerificationAnalysisResult(verification_id, document.id, ocr, existing_validation, tampering, face, existing_risk)

        now = datetime.now(UTC)
        verification.status = "PROCESSING"
        self.db.add(AuditEventModel(event_type="VERIFICATION_ANALYSIS_STARTED", actor_id=self.actor_id, verification_id=verification_id, document_id=document.id, status="PROCESSING", created_at=now))
        self.db.commit()
        try:
            typed_document = DocumentRecord(
                document.id, document.verification_id, DocumentType(document.document_type),
                document.original_filename, document.storage_key, document.mime_type,
                document.file_size, document.checksum_sha256, DocumentLifecycle(document.status),
                document.created_at.isoformat(), document.updated_at.isoformat(),
            )
            status, summary, findings = self.validation_provider.validate(typed_document, ocr)
            created = datetime.now(UTC).isoformat()
            validation = DocumentValidationResult(new_validation_result_id(), document.id, status, self.validation_provider.name, self.validation_provider.version, summary, findings, created, created)
            self.intelligence.add_validation(validation, self.actor_id)
            self.intelligence.commit()
            risk = assess_risk(verification_id, validation, tampering, face, ocr.overall_confidence)
            self.intelligence.add_risk(risk, self.actor_id)
            verification.status = "COMPLETED"
            self.db.add(AuditEventModel(event_type="VERIFICATION_ANALYSIS_COMPLETED", actor_id=self.actor_id, verification_id=verification_id, document_id=document.id, risk_assessment_id=risk.id, status="COMPLETED", created_at=datetime.now(UTC)))
            self.intelligence.commit()
            return VerificationAnalysisResult(verification_id, document.id, ocr, validation, tampering, face, risk)
        except Exception as exc:
            self.intelligence.rollback()
            verification = self.db.scalar(select(VerificationModel).where(VerificationModel.id == verification_id, VerificationModel.owner_id == self.actor_id))
            if verification is not None:
                verification.status = "FAILED"
            self.db.add(AuditEventModel(event_type="VERIFICATION_ANALYSIS_FAILED", actor_id=self.actor_id, verification_id=verification_id, document_id=document.id, status="FAILED", created_at=datetime.now(UTC)))
            self.intelligence.commit()
            raise RuntimeError("Verification analysis could not be completed.") from exc

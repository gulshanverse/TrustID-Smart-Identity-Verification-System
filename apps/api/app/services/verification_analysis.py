from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.models import AuditEventModel, VerificationModel
from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType
from app.domain.evidence import CorrelationResult, correlate
from app.domain.face import FaceVerificationResult
from app.domain.ocr import OCRResult
from app.domain.risk import RiskAssessmentResult, assess_risk
from app.domain.tampering import TamperingResult
from app.domain.unavailable import unavailable_face, unavailable_ocr, unavailable_tampering
from app.domain.validation import (
    DemoDocumentValidationProvider,
    DocumentValidationResult,
    new_validation_result_id,
)
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.repositories.intelligence_repository import SqlAlchemyIntelligenceRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository

logger = logging.getLogger("trustid.verification.analysis")


@dataclass(frozen=True)
class VerificationAnalysisResult:
    verification_id: UUID
    document_id: UUID
    ocr: OCRResult
    validation: DocumentValidationResult
    tampering: TamperingResult
    face: FaceVerificationResult
    risk: RiskAssessmentResult
    correlation: CorrelationResult


class _AnalysisClaimLost(RuntimeError):
    """The worker no longer owns the PROCESSING claim."""


class VerificationAnalysisService:
    def __init__(self, db: Session, actor_id: UUID) -> None:
        self.db = db
        self.actor_id = actor_id
        self.intelligence = SqlAlchemyIntelligenceRepository(db)
        self.ocr = SqlAlchemyOCRRepository(db)
        self.tampering = SqlAlchemyTamperingRepository(db)
        self.face = SqlAlchemyFaceRepository(db)
        self.validation_provider = DemoDocumentValidationProvider()

    def recover_stale_processing(self, verification_id: UUID) -> None:
        """Move one stale PROCESSING attempt to FAILED, if it is still stale.

        The conditional update is the recovery claim. A worker that completed or
        otherwise changed the row first cannot be overwritten by this operation.
        """
        threshold = datetime.now(UTC) - timedelta(
            seconds=get_settings().analysis_processing_timeout_seconds
        )
        result = self.db.execute(
            update(VerificationModel)
            .where(
                VerificationModel.id == verification_id,
                VerificationModel.owner_id == self.actor_id,
                VerificationModel.status == "PROCESSING",
                VerificationModel.processing_started_at.is_not(None),
                VerificationModel.processing_started_at < threshold,
            )
            .values(status="FAILED", processing_started_at=None)
        )
        if getattr(result, "rowcount", 0) != 1:
            self.db.rollback()
            raise RuntimeError("Verification analysis is not stale or is no longer available.")
        self.db.add(
            AuditEventModel(
                event_type="VERIFICATION_PROCESSING_RECOVERED",
                actor_id=self.actor_id,
                verification_id=verification_id,
                status="FAILED",
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()

    def _mark_failed_if_owned(
        self, verification_id: UUID, document_id: UUID, claim_started_at: datetime
    ) -> bool:
        """Commit a controlled failure transition only while the worker owns the claim."""
        failed = self.db.execute(
            update(VerificationModel)
            .where(
                VerificationModel.id == verification_id,
                VerificationModel.owner_id == self.actor_id,
                VerificationModel.status == "PROCESSING",
                VerificationModel.processing_started_at == claim_started_at,
            )
            .values(status="FAILED", processing_started_at=None)
        )
        if getattr(failed, "rowcount", 0) != 1:
            self.db.rollback()
            return False
        self.db.add(
            AuditEventModel(
                event_type="VERIFICATION_ANALYSIS_FAILED",
                actor_id=self.actor_id,
                verification_id=verification_id,
                document_id=document_id,
                status="FAILED",
                created_at=datetime.now(UTC),
            )
        )
        self.db.commit()
        return True

    def analyze(self, verification_id: UUID) -> VerificationAnalysisResult:
        started = time.perf_counter()
        document = self.intelligence.get_document_for_verification_owner(verification_id, self.actor_id)
        verification = self.db.scalar(
            select(VerificationModel).where(
                VerificationModel.id == verification_id,
                VerificationModel.owner_id == self.actor_id,
            )
        )
        if document is None or verification is None:
            raise LookupError("Verification not found or has no active document.")

        ocr = self.ocr.get_latest_for_owner(document.id, self.actor_id)
        tampering = self.tampering.get_latest_for_owner(document.id, self.actor_id)
        face = self.face.get_latest_for_owner(document.id, self.actor_id)
        if ocr is None:
            ocr = unavailable_ocr(verification_id, document.id)
        if tampering is None:
            tampering = unavailable_tampering(verification_id, document.id)
        if face is None:
            face = unavailable_face(verification_id, document.id)

        existing_validation = self.intelligence.latest_validation(document.id)
        existing_risk = self.intelligence.latest_risk(verification_id, self.actor_id)
        if existing_validation is not None and existing_risk is not None:
            logger.info(
                "verification_analysis_idempotent verification_id=%s outcome=COMPLETED duration_ms=%.2f",
                verification_id,
                (time.perf_counter() - started) * 1000,
            )
            return VerificationAnalysisResult(
                verification_id,
                document.id,
                ocr,
                existing_validation,
                tampering,
                face,
                existing_risk,
                correlate(verification_id, ocr, existing_validation, tampering, face, existing_risk),
            )

        claim_started_at = datetime.now(UTC)
        claim = self.db.execute(
            update(VerificationModel)
            .where(
                VerificationModel.id == verification_id,
                VerificationModel.owner_id == self.actor_id,
                VerificationModel.status.in_(["PENDING", "FAILED"]),
            )
            .values(status="PROCESSING", processing_started_at=claim_started_at)
        )
        if getattr(claim, "rowcount", 0) != 1:
            current = self.db.scalar(
                select(VerificationModel).where(
                    VerificationModel.id == verification_id,
                    VerificationModel.owner_id == self.actor_id,
                )
            )
            self.db.rollback()
            if current is not None and current.status == "PROCESSING":
                raise RuntimeError("Verification analysis is already in progress.")
            raise RuntimeError("Verification is not available for analysis in its current state.")

        self.db.add(
            AuditEventModel(
                event_type="VERIFICATION_ANALYSIS_STARTED",
                actor_id=self.actor_id,
                verification_id=verification_id,
                document_id=document.id,
                status="PROCESSING",
                created_at=claim_started_at,
            )
        )
        self.db.commit()

        try:
            # Provider/model work deliberately happens after the claim commit and
            # before the short persistence transaction below.
            typed_document = DocumentRecord(
                document.id,
                document.verification_id,
                DocumentType(document.document_type),
                document.original_filename,
                document.storage_key,
                document.mime_type,
                document.file_size,
                document.checksum_sha256,
                DocumentLifecycle(document.status),
                document.created_at.isoformat(),
                document.updated_at.isoformat(),
            )
            status, summary, findings = self.validation_provider.validate(typed_document, ocr)
            created = datetime.now(UTC).isoformat()
            validation = DocumentValidationResult(
                new_validation_result_id(),
                document.id,
                status,
                self.validation_provider.name,
                self.validation_provider.version,
                summary,
                findings,
                created,
                created,
            )
            self.intelligence.add_validation(validation, self.actor_id)
            risk = assess_risk(verification_id, validation, tampering, face, ocr.overall_confidence)
            correlation = correlate(verification_id, ocr, validation, tampering, face, risk)

            # One coherent persistence transaction: no derived row is committed
            # until validation, risk, correlation, terminal state, and audit rows
            # are all ready.
            self.intelligence.add_risk(risk, self.actor_id)
            completed = self.db.execute(
                update(VerificationModel)
                .where(
                    VerificationModel.id == verification_id,
                    VerificationModel.owner_id == self.actor_id,
                    VerificationModel.status == "PROCESSING",
                    VerificationModel.processing_started_at == claim_started_at,
                )
                .values(status="COMPLETED", processing_started_at=None)
            )
            if getattr(completed, "rowcount", 0) != 1:
                raise _AnalysisClaimLost("Analysis claim was no longer owned by this worker.")
            completed_at = datetime.now(UTC)
            self.db.add(
                AuditEventModel(
                    event_type="VERIFICATION_ANALYSIS_COMPLETED",
                    actor_id=self.actor_id,
                    verification_id=verification_id,
                    document_id=document.id,
                    risk_assessment_id=risk.id,
                    status="COMPLETED",
                    created_at=completed_at,
                )
            )
            self.db.add(
                AuditEventModel(
                    event_type="VERIFICATION_CORRELATION_COMPLETED",
                    actor_id=self.actor_id,
                    verification_id=verification_id,
                    document_id=document.id,
                    risk_assessment_id=risk.id,
                    status="COMPLETED",
                    provider="deterministic-correlation-engine",
                    created_at=completed_at,
                )
            )
            self.db.commit()
            logger.info(
                "verification_analysis_completed verification_id=%s status=COMPLETED risk_level=%s duration_ms=%.2f providers=%s",
                verification_id,
                risk.risk_level.value,
                (time.perf_counter() - started) * 1000,
                f"{ocr.provider},{self.validation_provider.name},{tampering.provider},{face.provider}",
            )
            return VerificationAnalysisResult(
                verification_id, document.id, ocr, validation, tampering, face, risk, correlation
            )
        except Exception as exc:
            self.db.rollback()
            owned_failure = False if isinstance(exc, _AnalysisClaimLost) else self._mark_failed_if_owned(
                verification_id, document.id, claim_started_at
            )
            logger.warning(
                "verification_analysis_failed verification_id=%s status=%s error_type=%s duration_ms=%.2f",
                verification_id,
                "FAILED" if owned_failure else "CLAIM_LOST",
                type(exc).__name__,
                (time.perf_counter() - started) * 1000,
            )
            raise RuntimeError("Verification analysis could not be completed.") from exc

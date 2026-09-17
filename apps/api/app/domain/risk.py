from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.face import FaceOutcome, FaceVerificationResult
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import DocumentValidationResult, ValidationStatus


class RiskLevel(StrEnum):
    LOW = "LOW"
    REVIEW = "REVIEW"
    HIGH = "HIGH"


class RiskAssessmentStatus(StrEnum):
    COMPLETED = "COMPLETED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"


class RiskSeverity(StrEnum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    HIGH = "HIGH"


@dataclass(frozen=True)
class RiskFactor:
    name: str
    source_module: str
    severity: RiskSeverity
    contribution: int
    explanation: str
    evidence_reference: str | None = None


@dataclass(frozen=True)
class RiskAssessmentResult:
    id: UUID
    verification_id: UUID
    status: RiskAssessmentStatus
    risk_score: int
    risk_level: RiskLevel
    recommendation: str
    confidence: float | None
    summary: str
    assessment_version: str
    factors: tuple[RiskFactor, ...]
    created_at: str
    updated_at: str


def _level(score: int) -> RiskLevel:
    if score <= 29:
        return RiskLevel.LOW
    if score <= 69:
        return RiskLevel.REVIEW
    return RiskLevel.HIGH


def assess_risk(verification_id: UUID, validation: DocumentValidationResult, tampering: TamperingResult, face: FaceVerificationResult, ocr_confidence: float) -> RiskAssessmentResult:
    factors: list[RiskFactor] = []
    validation_contribution = {ValidationStatus.PASSED: 0, ValidationStatus.REVIEW: 15, ValidationStatus.FAILED: 30, ValidationStatus.UNAVAILABLE: 20}[validation.status]
    factors.append(RiskFactor("Document validation", "document_validation", RiskSeverity.INFO if validation_contribution == 0 else RiskSeverity.REVIEW if validation_contribution < 30 else RiskSeverity.HIGH, validation_contribution, validation.summary, str(validation.id)))
    ocr_unavailable = ocr_confidence <= 0
    ocr_contribution = 10 if ocr_unavailable or ocr_confidence < 0.8 else 0
    ocr_explanation = "OCR capability/evidence is unavailable; officer review is required." if ocr_unavailable else "Structured OCR confidence is within the configured demo range." if ocr_contribution == 0 else "Structured OCR confidence is below the configured review threshold."
    factors.append(RiskFactor("OCR confidence", "ocr", RiskSeverity.INFO if ocr_contribution == 0 else RiskSeverity.REVIEW, ocr_contribution, ocr_explanation))
    tampering_contribution = 0 if tampering.status == TamperingStatus.COMPLETED and tampering.technical_signal_score == 0 else min(25, round(tampering.technical_signal_score * 25)) if tampering.status == TamperingStatus.COMPLETED else 20
    tampering_explanation = "Tampering capability/evidence is unavailable; officer review is required." if tampering.status != TamperingStatus.COMPLETED else "No suspicious technical tampering signal was detected." if tampering_contribution == 0 else "Technical document inconsistency detected; officer review is recommended."
    factors.append(RiskFactor("Technical document signals", "tampering", RiskSeverity.INFO if tampering_contribution == 0 else RiskSeverity.REVIEW if tampering_contribution < 18 else RiskSeverity.HIGH, tampering_contribution, tampering_explanation, str(tampering.id)))
    face_mapping = {FaceOutcome.MATCH: (0, RiskSeverity.INFO, "Face comparison matched within configured demo/provider criteria."), FaceOutcome.REVIEW: (12, RiskSeverity.REVIEW, "Face comparison is inconclusive and requires officer review."), FaceOutcome.NO_MATCH: (25, RiskSeverity.HIGH, "Presented face comparison did not meet the configured threshold; this is not proof of fraud."), FaceOutcome.NOT_AVAILABLE: (10, RiskSeverity.REVIEW, "Face comparison was unavailable or failed quality conditions.")}
    face_contribution, face_severity, face_explanation = face_mapping[face.outcome]
    factors.append(RiskFactor("Face verification", "face_verification", face_severity, face_contribution, face_explanation, str(face.id)))
    factors.append(RiskFactor("External verification", "external_verification", RiskSeverity.INFO, 0, "External verification unavailable; no government or third-party database was queried."))
    score = min(100, sum(factor.contribution for factor in factors))
    level = _level(score)
    recommendation = "No elevated prototype signal; officer review remains required." if level == RiskLevel.LOW else "Officer review required before any decision." if level == RiskLevel.REVIEW else "Elevated prototype signals require enhanced officer review."
    validation_confidence = ocr_confidence if validation.status == ValidationStatus.PASSED else 0.5
    face_confidence = face.confidence if face.confidence is not None else 0.5
    confidence = min(validation_confidence, face_confidence)
    now = datetime.now(UTC).isoformat()
    return RiskAssessmentResult(uuid4(), verification_id, RiskAssessmentStatus.COMPLETED, score, level, recommendation, confidence, "Prototype risk assessment is deterministic decision support, not a fraud or identity decision.", "phase9-v1", tuple(factors), now, now)

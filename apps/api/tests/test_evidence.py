from uuid import uuid4

from app.domain.evidence import EvidenceStatus, correlate
from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationResult, FaceVerificationStatus
from app.domain.ocr import OCREvidence, OCRField, OCRResult, OCRStatus
from app.domain.risk import (
    RiskAssessmentResult,
    RiskAssessmentStatus,
    RiskFactor,
    RiskLevel,
    RiskSeverity,
)
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import DocumentValidationResult, ValidationStatus


def _ocr(verification_id):
    document_id = uuid4()
    return OCRResult(uuid4(), document_id, OCRStatus.COMPLETED, "", "en", 0.97, "demo", "1.0", (OCRField("passport_number", "X1234567", "X1234567", 0.97, "X1234567", OCREvidence(page=1)),), "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00", field_consistency=({"field": "passport_number", "visual_value": "X1234567", "mrz_value": "X1234568", "status": "MISMATCH"},))


def _validation(document_id):
    return DocumentValidationResult(uuid4(), document_id, ValidationStatus.PASSED, "demo", "1.0", "Validation passed.", (), "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")


def _tampering(document_id):
    return TamperingResult(uuid4(), document_id, TamperingStatus.COMPLETED, 0.0, 0.96, "demo", "1.0", "Clean.", (), "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")


def _face(verification_id, outcome=FaceOutcome.NO_MATCH):
    return FaceVerificationResult(uuid4(), verification_id, uuid4(), FaceVerificationStatus.COMPLETED, outcome, 0.21, 0.80, "SFace", "1.0", "No match.", None, FaceQuality.READY, FaceQuality.READY, 1, (), "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")


def _risk(verification_id):
    return RiskAssessmentResult(uuid4(), verification_id, RiskAssessmentStatus.COMPLETED, 25, RiskLevel.REVIEW, "Review.", 0.8, "Deterministic.", "test-v1", (RiskFactor("Face verification", "face_verification", RiskSeverity.HIGH, 25, "No match.", "face"),), "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")


def test_correlation_generates_field_and_face_findings_with_provenance():
    verification_id = uuid4()
    ocr = _ocr(verification_id)
    result = correlate(verification_id, ocr, _validation(ocr.document_id), _tampering(ocr.document_id), _face(verification_id), _risk(verification_id))
    assert result.evidence
    assert any(item.reason_code == "MRZ_OCR_PASSPORT_NUMBER_MISMATCH" for item in result.evidence)
    assert any(item.code == "FACE_NO_MATCH" and item.severity.value == "HIGH" for item in result.findings)
    assert any(item.code == "MRZ_OCR_PASSPORT_NUMBER_MISMATCH" for item in result.findings)
    assert all(item.provenance.module and item.provenance.provider and item.provenance.version for item in result.evidence)
    assert all(item.status in {EvidenceStatus.FAIL, EvidenceStatus.REVIEW} for item in result.findings)


def test_correlation_is_deterministically_ordered():
    verification_id = uuid4()
    ocr = _ocr(verification_id)
    first = correlate(verification_id, ocr, _validation(ocr.document_id), _tampering(ocr.document_id), _face(verification_id), _risk(verification_id))
    second = correlate(verification_id, ocr, _validation(ocr.document_id), _tampering(ocr.document_id), _face(verification_id), _risk(verification_id))
    assert [item.code for item in first.findings] == [item.code for item in second.findings]
    assert [item.evidence_id for item in first.evidence] == [item.evidence_id for item in second.evidence]

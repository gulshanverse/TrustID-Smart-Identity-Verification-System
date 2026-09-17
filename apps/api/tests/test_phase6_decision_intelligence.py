from datetime import UTC, datetime
from uuid import uuid4

from app.domain.decision_intelligence import DecisionIntelligenceService
from app.domain.evidence import CorrelationResult
from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationResult, FaceVerificationStatus
from app.domain.ocr import OCRResult, OCRStatus
from app.domain.risk import RiskAssessmentResult, RiskAssessmentStatus, RiskLevel
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import DocumentValidationResult, ValidationStatus


def now() -> str:
    return datetime.now(UTC).isoformat()


def test_decision_intelligence_preserves_authoritative_risk_and_missing_semantics():
    verification_id = uuid4()
    document_id = uuid4()
    ocr = OCRResult(
        uuid4(), document_id, OCRStatus.COMPLETED, "", "en", 0.9, "test", "1", (), now(), now()
    )
    validation = DocumentValidationResult(
        uuid4(),
        document_id,
        ValidationStatus.PASSED,
        "rules",
        "phase5-rules-v1",
        "passed",
        (),
        now(),
        now(),
    )
    tampering = TamperingResult(
        uuid4(),
        document_id,
        TamperingStatus.COMPLETED,
        0.0,
        0.9,
        "test",
        "1",
        "clear",
        (),
        now(),
        now(),
    )
    face = FaceVerificationResult(
        uuid4(),
        verification_id,
        document_id,
        FaceVerificationStatus.COMPLETED,
        FaceOutcome.MATCH,
        0.95,
        0.9,
        "test",
        "1",
        "match",
        None,
        FaceQuality.READY,
        FaceQuality.READY,
        1,
        (),
        now(),
        now(),
    )
    risk = RiskAssessmentResult(
        uuid4(),
        verification_id,
        RiskAssessmentStatus.COMPLETED,
        12,
        RiskLevel.LOW,
        "review",
        None,
        "authoritative",
        "phase9-v1",
        (),
        now(),
        now(),
    )
    result = DecisionIntelligenceService().build(
        verification_id,
        ocr,
        validation,
        tampering,
        face,
        risk,
        CorrelationResult((), (), "summary"),
    )
    assert result.risk_context.score == 12
    assert result.risk_context.assessment_version == "phase9-v1"
    assert result.missing_information[0].status == "NOT_AVAILABLE"
    assert any(
        item.code == "EXTERNAL_VERIFICATION_NOT_AVAILABLE" for item in result.missing_information
    )


def test_no_match_is_high_priority_but_not_fraud():
    verification_id = uuid4()
    document_id = uuid4()
    ocr = OCRResult(
        uuid4(), document_id, OCRStatus.COMPLETED, "", "en", 0.9, "test", "1", (), now(), now()
    )
    validation = DocumentValidationResult(
        uuid4(),
        document_id,
        ValidationStatus.PASSED,
        "rules",
        "phase5-rules-v1",
        "passed",
        (),
        now(),
        now(),
    )
    tampering = TamperingResult(
        uuid4(),
        document_id,
        TamperingStatus.COMPLETED,
        0.0,
        0.9,
        "test",
        "1",
        "clear",
        (),
        now(),
        now(),
    )
    face = FaceVerificationResult(
        uuid4(),
        verification_id,
        document_id,
        FaceVerificationStatus.COMPLETED,
        FaceOutcome.MATCH,
        0.95,
        0.9,
        "test",
        "1",
        "match",
        None,
        FaceQuality.READY,
        FaceQuality.READY,
        1,
        (),
        now(),
        now(),
    )
    risk = RiskAssessmentResult(
        uuid4(),
        verification_id,
        RiskAssessmentStatus.COMPLETED,
        12,
        RiskLevel.LOW,
        "review",
        None,
        "authoritative",
        "phase9-v1",
        (),
        now(),
        now(),
    )
    external = ExternalVerificationResult(
        ExternalStatus.NO_MATCH, "authorized-test", "1", "no matching record", "ref", now()
    )
    result = DecisionIntelligenceService().build(
        verification_id,
        ocr,
        validation,
        tampering,
        face,
        risk,
        CorrelationResult((), (), "summary"),
        external,
    )
    assert result.review_priorities[0].code == "EXTERNAL_NO_MATCH"
    assert all(
        "fraud" not in item.explanation.lower() or "not" in item.explanation.lower()
        for item in result.review_priorities
    )
    assert all(item.contribution == 0 for item in result.risk_context.factors)

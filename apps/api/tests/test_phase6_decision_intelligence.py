from datetime import UTC, datetime
from uuid import uuid4

from app.domain.decision_intelligence import DecisionIntelligenceService
from app.domain.evidence import CorrelationResult
from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationResult, FaceVerificationStatus
from app.domain.ocr import OCRResult, OCRStatus
from app.domain.risk import RiskAssessmentResult, RiskAssessmentStatus, RiskLevel
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.unavailable import unavailable_face
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


def _decision_inputs():
    verification_id = uuid4()
    document_id = uuid4()
    timestamp = "2026-01-01T00:00:00+00:00"
    ocr = OCRResult(uuid4(), document_id, OCRStatus.COMPLETED, "", "en", 0.9, "ocr", "1", (), timestamp, timestamp)
    validation = DocumentValidationResult(uuid4(), document_id, ValidationStatus.FAILED, "rules", "phase5-rules-v1", "validation failed", (), timestamp, timestamp)
    tampering = TamperingResult(uuid4(), document_id, TamperingStatus.COMPLETED, 0.5, 0.9, "tampering", "1", "signal", (), timestamp, timestamp)
    face = FaceVerificationResult(uuid4(), verification_id, document_id, FaceVerificationStatus.COMPLETED, FaceOutcome.NO_MATCH, 0.2, 0.2, "face", "1", "no match", None, FaceQuality.READY, FaceQuality.READY, 1, (), timestamp, timestamp)
    risk = RiskAssessmentResult(uuid4(), verification_id, RiskAssessmentStatus.COMPLETED, 55, RiskLevel.REVIEW, "review", None, "summary", "risk-v1", (), timestamp, timestamp)
    correlation = __import__("app.domain.evidence", fromlist=["correlate"]).correlate(verification_id, ocr, validation, tampering, face, risk)
    return verification_id, ocr, validation, tampering, face, risk, correlation


def test_same_source_state_has_same_fingerprint_but_generated_at_is_metadata():
    inputs = _decision_inputs()
    first = DecisionIntelligenceService().build(*inputs)
    second = DecisionIntelligenceService().build(*inputs)
    assert first.analysis_fingerprint == second.analysis_fingerprint
    assert first.generated_at != second.generated_at


def test_signals_are_not_contradictions_and_priorities_link_source_evidence():
    result = DecisionIntelligenceService().build(*_decision_inputs())
    contradiction_codes = {item.code for item in result.contradictions}
    assert "FACE_NO_MATCH" not in contradiction_codes
    assert "TAMPERING_SIGNAL" not in contradiction_codes
    priorities = {item.code: item for item in result.review_priorities}
    assert priorities["FACE_NO_MATCH"].evidence_ids
    assert priorities["FORENSIC_SIGNAL"].evidence_ids
    assert priorities["DOCUMENT_VALIDATION_FAILED"].evidence_ids
    assert all("proof of fraud" not in item.explanation.lower() for item in result.review_priorities)


def test_snapshot_excludes_generated_at_and_contains_safe_context():
    result = DecisionIntelligenceService().build(*_decision_inputs())
    snapshot = result.snapshot()
    assert snapshot["analysis_fingerprint"] == result.analysis_fingerprint
    assert "generated_at" not in snapshot
    assert "raw_payload" not in str(snapshot).lower()
    assert "embedding" not in str(snapshot).lower()


def test_unavailable_face_remains_unavailable_through_decision_intelligence():
    verification_id, ocr, validation, tampering, _face, risk, _correlation = _decision_inputs()
    face = unavailable_face(verification_id, ocr.document_id)
    correlation = __import__("app.domain.evidence", fromlist=["correlate"]).correlate(verification_id, ocr, validation, tampering, face, risk)
    face_evidence = next(item for item in correlation.evidence if item.source_module == "FACE")
    assert face.status == FaceVerificationStatus.NOT_AVAILABLE
    assert face.outcome == FaceOutcome.NOT_AVAILABLE
    assert face_evidence.status.value == "NOT_AVAILABLE"
    assert not any(item.code == "FACE_NO_MATCH" for item in correlation.findings)
    result = DecisionIntelligenceService().build(verification_id, ocr, validation, tampering, face, risk, correlation)
    assert any(item.code == "FACE_VERIFICATION_NOT_AVAILABLE" for item in result.missing_information)
    assert not any(item.code == "FACE_NO_MATCH" for item in result.contradictions)
    assert "fraud" not in str(result.snapshot()).lower()

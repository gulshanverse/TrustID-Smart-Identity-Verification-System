from datetime import UTC, datetime
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEventModel,
    Base,
    FaceVerificationModel,
    OCRResultModel,
    RiskAssessmentModel,
    TamperingResultModel,
    VerificationModel,
)
from app.domain.documents import (
    DocumentLifecycle,
    DocumentRecord,
    DocumentType,
    InMemoryObjectStorage,
)
from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationResult, FaceVerificationStatus
from app.domain.ocr import OCRField, OCRResult, OCRStatus
from app.domain.risk import RiskLevel, assess_risk
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import (
    DemoDocumentValidationProvider,
    DocumentValidationResult,
    ValidationFinding,
    ValidationSeverity,
    ValidationStatus,
)
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.document_service import DocumentService
from app.services.face_service import FaceVerificationService
from app.services.ocr_service import OCRService
from app.services.tampering_service import TamperingService
from app.services.verification_analysis import VerificationAnalysisService


def now() -> str:
    return datetime.now(UTC).isoformat()


def validation(status: ValidationStatus) -> DocumentValidationResult:
    return DocumentValidationResult(uuid4(), uuid4(), status, "demo", "1", "validation", (ValidationFinding("rule", ValidationSeverity.REVIEW, status == ValidationStatus.PASSED, "rule explanation"),), now(), now())


def ocr(confidence: float = 0.97) -> OCRResult:
    return OCRResult(uuid4(), uuid4(), OCRStatus.COMPLETED, "", "en", confidence, "demo", "1", (OCRField("full_name", "DEMO", "DEMO", confidence, "DEMO"),), now(), now())


def tampering(score: float) -> TamperingResult:
    return TamperingResult(uuid4(), uuid4(), TamperingStatus.COMPLETED, score, 0.9, "demo", "1", "technical signals", (), now(), now())


def face(outcome: FaceOutcome) -> FaceVerificationResult:
    return FaceVerificationResult(uuid4(), uuid4(), uuid4(), FaceVerificationStatus.COMPLETED, outcome, 0.94 if outcome == FaceOutcome.MATCH else 0.31, 0.91, "demo", "1", "face result", None, FaceQuality.READY, FaceQuality.READY, 1, (), now(), now())


def test_risk_threshold_boundaries_are_explicit_and_reproducible() -> None:
    verification_id = uuid4()
    low = assess_risk(verification_id, validation(ValidationStatus.PASSED), tampering(0.16), face(FaceOutcome.MATCH), 0.97)
    review = assess_risk(verification_id, validation(ValidationStatus.PASSED), tampering(0.20), face(FaceOutcome.MATCH), 0.97)
    at_69 = assess_risk(verification_id, validation(ValidationStatus.FAILED), tampering(0.68), face(FaceOutcome.REVIEW), 0.7)
    at_70 = assess_risk(verification_id, validation(ValidationStatus.FAILED), tampering(0.72), face(FaceOutcome.REVIEW), 0.7)
    assert (low.risk_score, low.risk_level) == (4, RiskLevel.LOW)
    assert (review.risk_score, review.risk_level) == (5, RiskLevel.LOW)
    assert (at_69.risk_score, at_69.risk_level) == (69, RiskLevel.REVIEW)
    assert (at_70.risk_score, at_70.risk_level) == (70, RiskLevel.HIGH)
    repeat = assess_risk(verification_id, validation(ValidationStatus.FAILED), tampering(0.72), face(FaceOutcome.REVIEW), 0.7)
    assert [(factor.name, factor.contribution) for factor in at_70.factors] == [(factor.name, factor.contribution) for factor in repeat.factors]
    assert at_70.risk_score == sum(factor.contribution for factor in at_70.factors)


def test_validation_provider_detects_expiry_and_required_fields() -> None:
    document = DocumentRecord(uuid4(), uuid4(), DocumentType.PASSPORT, "demo.pdf", "key", "application/pdf", 1, "x", DocumentLifecycle.READY_FOR_ANALYSIS, now(), now())
    fields = (OCRField("full_name", "DEMO", "DEMO", 0.97, "DEMO"), OCRField("passport_number", "BAD", "BAD", 0.97, "BAD"), OCRField("nationality", "DEMO", "DEMO", 0.97, "DEMO"), OCRField("date_of_birth", "1990-01-01", "1990-01-01", 0.97, "1990-01-01"), OCRField("expiry_date", "2020-01-01", "2020-01-01", 0.97, "2020-01-01"))
    result = DemoDocumentValidationProvider().validate(document, OCRResult(uuid4(), document.id, OCRStatus.COMPLETED, "", "en", 0.97, "demo", "1", fields, now(), now()))
    assert result[0] == ValidationStatus.FAILED
    assert any(item.name == "validity" and not item.passed for item in result[2])


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def test_verification_orchestration_persists_risk_and_audit_events(db: Session) -> None:
    actor = uuid4()
    storage = InMemoryObjectStorage()
    documents = DocumentService(storage, SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"phase9-{actor}@example.test", "Officer")
    content = "%PDF-1.7\nTRUSTID-DEMO-OCR: FICTIONAL SAMPLE — NOT A REAL IDENTITY DOCUMENT\nTRUSTID-TAMPERING:CLEAN\nTRUSTID-FACE:DOCUMENT\nTrustID simulated passport fixture\n".encode()
    document = documents.upload(verification.id, actor, "demo.pdf", "application/pdf", content, DocumentType.PASSPORT)
    OCRService(storage, SqlAlchemyOCRRepository(db), __import__("app.domain.ocr", fromlist=["DemoOCRProvider"]).DemoOCRProvider()).process(document.id, actor)
    TamperingService(storage, SqlAlchemyTamperingRepository(db), __import__("app.domain.tampering", fromlist=["DemoTamperingProvider"]).DemoTamperingProvider()).process(document.id, actor)
    FaceVerificationService(storage, SqlAlchemyFaceRepository(db), __import__("app.domain.face", fromlist=["DemoFaceVerificationProvider"]).DemoFaceVerificationProvider()).process(document.id, actor, b"\xff\xd8\xffTRUSTID-FACE:MATCH", "image/jpeg", __import__("app.domain.face", fromlist=["FaceScenario"]).FaceScenario.MATCH)
    result = VerificationAnalysisService(db, actor).analyze(verification.id)
    assert result.risk.risk_level == RiskLevel.LOW
    assert result.risk.risk_score == sum(factor.contribution for factor in result.risk.factors)
    stored = db.scalar(select(RiskAssessmentModel).where(RiskAssessmentModel.id == result.risk.id))
    assert stored is not None
    assert db.scalar(select(OCRResultModel).where(OCRResultModel.document_id == document.id)) is not None
    assert db.scalar(select(TamperingResultModel).where(TamperingResultModel.document_id == document.id)) is not None
    assert db.scalar(select(FaceVerificationModel).where(FaceVerificationModel.document_id == document.id)) is not None
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.verification_id == verification.id)).all()
    event_types = {event.event_type for event in events}
    assert {"OCR_COMPLETED", "TAMPERING_COMPLETED", "FACE_VERIFICATION_COMPLETED", "DOCUMENT_VALIDATION_COMPLETED", "RISK_ASSESSMENT_COMPLETED", "VERIFICATION_ANALYSIS_COMPLETED"} <= event_types
    assert [event.event_type for event in events][-4:] == ["DOCUMENT_VALIDATION_COMPLETED", "RISK_ASSESSMENT_COMPLETED", "VERIFICATION_ANALYSIS_COMPLETED", "VERIFICATION_ANALYSIS_COMPLETED"] or events[-1].event_type == "VERIFICATION_ANALYSIS_COMPLETED"


def test_repeated_analysis_is_idempotent_and_marks_lifecycle_complete(db: Session) -> None:
    actor = uuid4()
    storage = InMemoryObjectStorage()
    documents = DocumentService(storage, SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"repeat-{actor}@example.test", "Officer")
    document = documents.upload(verification.id, actor, "demo.pdf", "application/pdf", b"%PDF-1.7\nTRUSTID-DEMO-OCR:demo\nTRUSTID-TAMPERING:CLEAN\nTRUSTID-FACE:DOCUMENT", DocumentType.PASSPORT)
    OCRService(storage, SqlAlchemyOCRRepository(db), __import__("app.domain.ocr", fromlist=["DemoOCRProvider"]).DemoOCRProvider()).process(document.id, actor)
    TamperingService(storage, SqlAlchemyTamperingRepository(db), __import__("app.domain.tampering", fromlist=["DemoTamperingProvider"]).DemoTamperingProvider()).process(document.id, actor)
    FaceVerificationService(storage, SqlAlchemyFaceRepository(db), __import__("app.domain.face", fromlist=["DemoFaceVerificationProvider"]).DemoFaceVerificationProvider()).process(document.id, actor, b"\xff\xd8\xffTRUSTID-FACE:MATCH", "image/jpeg", __import__("app.domain.face", fromlist=["FaceScenario"]).FaceScenario.MATCH)
    first = VerificationAnalysisService(db, actor).analyze(verification.id)
    second = VerificationAnalysisService(db, actor).analyze(verification.id)
    assert first.risk.id == second.risk.id
    assert db.scalar(select(VerificationModel).where(VerificationModel.id == verification.id)).status == "COMPLETED"
    assert db.scalars(select(RiskAssessmentModel).where(RiskAssessmentModel.verification_id == verification.id)).all().__len__() == 1


def test_orchestration_does_not_fabricate_missing_modules(db: Session) -> None:
    actor = uuid4()
    documents = DocumentService(InMemoryObjectStorage(), SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"phase9-missing-{actor}@example.test", "Officer")
    with pytest.raises(LookupError):
        VerificationAnalysisService(db, actor).analyze(verification.id)

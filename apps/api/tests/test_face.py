import logging
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, Base, FaceVerificationModel
from app.domain.documents import DocumentType, InMemoryObjectStorage, ObjectStorage, StoredObject
from app.domain.face import (
    DemoFaceVerificationProvider,
    FaceOutcome,
    FaceScenario,
    FaceVerificationStatus,
)
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.face_repository import SqlAlchemyFaceRepository
from app.services.document_service import DocumentService
from app.services.face_service import FaceVerificationService

DOCUMENT = b"%PDF-1.7\nTRUSTID-FACE:DOCUMENT"
DEMO_FACE_FIXTURE = b"\xff\xd8\xff" + "TRUSTID-FACE:MATCH\nDEMO / SIMULATED\nFICTIONAL SAMPLE — NOT A REAL PERSON\n".encode()


def presented(scenario: FaceScenario) -> bytes:
    return DEMO_FACE_FIXTURE if scenario == FaceScenario.MATCH else b"\xff\xd8\xff" + f"TRUSTID-FACE:{scenario.value}".encode()


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def prepared(db: Session, storage: ObjectStorage | None = None):
    actor = uuid4()
    object_storage = storage or InMemoryObjectStorage()
    documents = DocumentService(object_storage, SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"officer-{actor}@example.test", "Officer")
    document = documents.upload(verification.id, actor, "demo.pdf", "application/pdf", DOCUMENT, DocumentType.PASSPORT)
    return actor, object_storage, document


def service(db: Session, storage: ObjectStorage, scenario: FaceScenario = FaceScenario.MATCH) -> FaceVerificationService:
    return FaceVerificationService(storage, SqlAlchemyFaceRepository(db), DemoFaceVerificationProvider())


def test_demo_provider_supports_all_deterministic_scenarios() -> None:
    for scenario in FaceScenario:
        first = DemoFaceVerificationProvider().compare(DOCUMENT, presented(scenario), scenario)
        second = DemoFaceVerificationProvider().compare(DOCUMENT, presented(scenario), scenario)
        assert first == second
        assert DemoFaceVerificationProvider.name == "DEMO / SIMULATED"
        assert first[0] in {FaceOutcome.MATCH, FaceOutcome.MISMATCH, FaceOutcome.REVIEW, FaceOutcome.UNAVAILABLE}


def test_fictional_demo_face_fixture_is_deterministic_and_contains_no_real_pii() -> None:
    assert presented(FaceScenario.MATCH) == DEMO_FACE_FIXTURE
    assert b"TRUSTID-FACE:MATCH" in DEMO_FACE_FIXTURE
    assert b"FICTIONAL SAMPLE" in DEMO_FACE_FIXTURE
    assert b"@" not in DEMO_FACE_FIXTURE
    assert b"password" not in DEMO_FACE_FIXTURE.lower()
    assert DemoFaceVerificationProvider().compare(DOCUMENT, DEMO_FACE_FIXTURE, FaceScenario.MATCH)[0] == FaceOutcome.MATCH


def test_match_result_persists_without_biometric_material(db: Session) -> None:
    actor, storage, document = prepared(db)
    result = service(db, storage).process(document.id, actor, presented(FaceScenario.MATCH), "image/jpeg", FaceScenario.MATCH)
    latest = service(db, storage).get_latest(document.id, actor)
    assert result.status == FaceVerificationStatus.COMPLETED
    assert result.outcome == FaceOutcome.MATCH
    assert result.similarity_score == 0.94
    assert latest.id == result.id
    assert db.scalar(select(FaceVerificationModel).where(FaceVerificationModel.id == result.id)).id == result.id
    assert not hasattr(latest, "embedding")


def test_mismatch_review_and_quality_results_remain_non_decisional(db: Session) -> None:
    actor, storage, document = prepared(db)
    for scenario, outcome in ((FaceScenario.MISMATCH, FaceOutcome.MISMATCH), (FaceScenario.REVIEW, FaceOutcome.REVIEW), (FaceScenario.NO_FACE, FaceOutcome.UNAVAILABLE), (FaceScenario.MULTIPLE_FACES, FaceOutcome.UNAVAILABLE), (FaceScenario.LOW_QUALITY, FaceOutcome.UNAVAILABLE)):
        result = service(db, storage).process(document.id, actor, presented(scenario), "image/jpeg", scenario)
        assert result.outcome == outcome
        assert "fraud" not in result.summary.lower()


def test_unauthorized_and_invalid_state_are_rejected(db: Session) -> None:
    actor, storage, document = prepared(db)
    with pytest.raises(LookupError):
        service(db, storage).process(document.id, uuid4(), presented(FaceScenario.MATCH), "image/jpeg", FaceScenario.MATCH)
    db.get(__import__("app.db.models", fromlist=["DocumentModel"]).DocumentModel, document.id).status = "DELETED"
    db.commit()
    with pytest.raises(LookupError):
        service(db, storage).process(document.id, actor, presented(FaceScenario.MATCH), "image/jpeg", FaceScenario.MATCH)


def test_malformed_unsupported_and_oversized_presented_images_are_rejected(db: Session) -> None:
    actor, storage, document = prepared(db)
    with pytest.raises(RuntimeError):
        service(db, storage).process(document.id, actor, b"not an image", "image/jpeg", FaceScenario.MATCH)
    with pytest.raises(RuntimeError):
        service(db, storage).process(document.id, actor, presented(FaceScenario.MATCH), "image/bmp", FaceScenario.MATCH)
    with pytest.raises(RuntimeError):
        service(db, storage).process(document.id, actor, b"\xff\xd8\xff" + b"x" * (5 * 1024 * 1024), "image/jpeg", FaceScenario.MATCH)


def test_provider_and_storage_failure_are_safe_and_audited(db: Session) -> None:
    actor, _, document = prepared(db)

    class BrokenStorage(ObjectStorage):
        def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
            raise NotImplementedError
        def delete(self, key: str) -> None:
            return None
        def get(self, key: str) -> bytes:
            raise RuntimeError("storage unavailable")

    with pytest.raises(RuntimeError, match="could not be completed"):
        service(db, BrokenStorage()).process(document.id, actor, presented(FaceScenario.MATCH), "image/jpeg", FaceScenario.MATCH)
    assert db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()[-1].event_type == "FACE_VERIFICATION_FAILED"


def test_arbitrary_fixtures_cannot_become_demo_matches(db: Session) -> None:
    actor, storage, document = prepared(db)
    with pytest.raises(RuntimeError):
        service(db, storage).process(document.id, actor, b"\xff\xd8\xff ordinary photo", "image/jpeg", FaceScenario.MATCH)


def test_sensitive_face_data_is_not_logged_and_reprocessing_is_historical(db: Session, caplog: pytest.LogCaptureFixture) -> None:
    actor, storage, document = prepared(db)
    with caplog.at_level(logging.INFO):
        first = service(db, storage).process(document.id, actor, presented(FaceScenario.MATCH), "image/jpeg", FaceScenario.MATCH)
        second = service(db, storage).process(document.id, actor, presented(FaceScenario.REVIEW), "image/jpeg", FaceScenario.REVIEW)
    assert b"TRUSTID-FACE".decode() not in caplog.text
    assert first.id != second.id
    assert len(db.scalars(select(FaceVerificationModel).where(FaceVerificationModel.document_id == document.id)).all()) == 2

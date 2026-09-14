import logging
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, Base, DocumentModel
from app.domain.documents import DocumentType, InMemoryObjectStorage, ObjectStorage, StoredObject
from app.domain.ocr import DemoOCRProvider
from app.domain.tampering import DemoTamperingProvider, TamperingScenario, TamperingStatus
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.repositories.tampering_repository import SqlAlchemyTamperingRepository
from app.services.document_service import DocumentService
from app.services.ocr_service import OCRService
from app.services.tampering_service import TamperingService


def fixture_bytes(scenario: TamperingScenario, ocr: bool = False) -> bytes:
    marker = f"TRUSTID-TAMPERING:{scenario.value}".encode()
    return b"%PDF-1.7\n" + (b"TRUSTID-DEMO-OCR: fictional\n" if ocr else b"") + marker


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def prepared(db: Session, scenario: TamperingScenario = TamperingScenario.CLEAN, storage: ObjectStorage | None = None, ocr: bool = False):
    actor = uuid4()
    object_storage = storage or InMemoryObjectStorage()
    documents = DocumentService(object_storage, SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"officer-{actor}@example.test", "Officer")
    document = documents.upload(verification.id, actor, "demo.pdf", "application/pdf", fixture_bytes(scenario, ocr), DocumentType.PASSPORT)
    return actor, object_storage, document


def test_all_demo_scenarios_are_deterministic_and_explicitly_labeled(db: Session) -> None:
    for scenario in TamperingScenario:
        _, storage, document = prepared(db, scenario)
        provider = DemoTamperingProvider(scenario)
        first = provider.analyze(document, storage.get(document.storage_key), None)
        second = provider.analyze(document, storage.get(document.storage_key), None)
        assert first == second
        assert provider.name == "DEMO / SIMULATED"
        if scenario == TamperingScenario.CLEAN:
            assert first[3] == ()
        else:
            assert first[3][0].evidence and len(first[3][0].evidence) == 2


def test_result_findings_evidence_and_audit_persist(db: Session) -> None:
    actor, storage, document = prepared(db, TamperingScenario.TEXT_MANIPULATION, ocr=True)
    OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider()).process(document.id, actor)
    service = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider(TamperingScenario.TEXT_MANIPULATION))
    result = service.process(document.id, actor)
    recreated = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).get_latest(document.id, actor)
    assert result.status == TamperingStatus.COMPLETED
    assert recreated.id == result.id
    assert recreated.findings[0].related_ocr_field == "passport_number"
    assert len(recreated.findings[0].evidence) == 2
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()
    assert [event.event_type for event in events][-2:] == ["TAMPERING_STARTED", "TAMPERING_COMPLETED"]
    assert events[-1].tampering_result_id == result.id


def test_unauthorized_execution_and_read_are_rejected(db: Session) -> None:
    actor, storage, document = prepared(db)
    service = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider())
    with pytest.raises(LookupError):
        service.process(document.id, uuid4())
    service.process(document.id, actor)
    with pytest.raises(LookupError):
        service.get_latest(document.id, uuid4())


def test_invalid_document_state_is_rejected(db: Session) -> None:
    actor, storage, document = prepared(db)
    db.get(DocumentModel, document.id).status = "DELETED"
    db.commit()
    with pytest.raises(LookupError):
        TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).process(document.id, actor)


def test_storage_and_provider_failures_are_safe_and_audited(db: Session) -> None:
    actor, _, document = prepared(db)

    class BrokenStorage(ObjectStorage):
        def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
            raise NotImplementedError
        def delete(self, key: str) -> None:
            return None
        def get(self, key: str) -> bytes:
            raise RuntimeError("storage unavailable")

    with pytest.raises(RuntimeError, match="could not be completed"):
        TamperingService(BrokenStorage(), SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).process(document.id, actor)
    assert db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()[-1].event_type == "TAMPERING_FAILED"


def test_malformed_and_unsupported_documents_fail_before_provider(db: Session) -> None:
    actor, storage, document = prepared(db)
    storage.objects[document.storage_key] = b"not a pdf"
    with pytest.raises(RuntimeError):
        TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).process(document.id, actor)
    model = db.get(DocumentModel, document.id)
    model.mime_type = "application/x-unknown"
    model.status = "READY_FOR_ANALYSIS"
    db.commit()
    with pytest.raises(RuntimeError):
        TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).process(document.id, actor)


def test_arbitrary_document_is_not_fabricated_into_a_finding(db: Session) -> None:
    actor, storage, document = prepared(db)
    storage.objects[document.storage_key] = b"%PDF-1.7 ordinary content"
    with pytest.raises(RuntimeError):
        TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider(TamperingScenario.PHOTO_INCONSISTENCY)).process(document.id, actor)


def test_raw_sensitive_data_is_not_logged(db: Session, caplog: pytest.LogCaptureFixture) -> None:
    actor, storage, document = prepared(db, TamperingScenario.TEXT_MANIPULATION)
    with caplog.at_level(logging.INFO):
        TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider(TamperingScenario.TEXT_MANIPULATION)).process(document.id, actor)
    assert "passport" not in caplog.text.lower()


def test_clean_result_is_technical_not_authenticity_decision(db: Session) -> None:
    actor, storage, document = prepared(db)
    result = TamperingService(storage, SqlAlchemyTamperingRepository(db), DemoTamperingProvider()).process(document.id, actor)
    assert result.summary == "No suspicious technical tampering signals detected."
    assert "genuine" not in result.summary.lower()
    assert result.technical_signal_score == 0.0

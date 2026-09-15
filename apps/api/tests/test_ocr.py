import logging
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, Base
from app.domain.documents import DocumentType, InMemoryObjectStorage, ObjectStorage, StoredObject
from app.domain.ocr import DemoOCRProvider, OCRProvider, OCRStatus
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.repositories.ocr_repository import SqlAlchemyOCRRepository
from app.services.document_service import DocumentService
from app.services.ocr_service import OCRService

DEMO_PDF = b"%PDF-1.7\nTRUSTID-DEMO-OCR: fictional fixture"
FRONTEND_DEMO_FIXTURE = "%PDF-1.7\nTRUSTID-DEMO-OCR: FICTIONAL SAMPLE — NOT A REAL IDENTITY DOCUMENT\nTRUSTID-TAMPERING:CLEAN\nTRUSTID-FACE:DOCUMENT\nTrustID simulated passport fixture\n".encode()


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
    document_service = DocumentService(object_storage, SqlAlchemyDocumentRepository(db))
    verification = document_service.create_verification(actor, "officer@example.test", "Officer")
    document = document_service.upload(verification.id, actor, "demo.pdf", "application/pdf", DEMO_PDF, DocumentType.PASSPORT)
    return actor, object_storage, document


def test_demo_provider_is_deterministic_and_explicitly_simulated(db: Session) -> None:
    _, storage, document = prepared(db)
    first = DemoOCRProvider().process(document, storage.get(document.storage_key))
    second = DemoOCRProvider().process(document, storage.get(document.storage_key))
    assert first == second
    assert DemoOCRProvider.name == "DEMO / SIMULATED"
    assert first[2] == 0.97
    assert {field.name for field in first[1]} == {"full_name", "passport_number", "nationality", "date_of_birth", "expiry_date", "gender"}


def test_ocr_result_fields_evidence_and_relationship_persist(db: Session) -> None:
    actor, storage, document = prepared(db)
    service = OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider())
    result = service.process(document.id, actor)
    recreated = OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider()).get_latest(document.id, actor)
    assert result.status == OCRStatus.COMPLETED
    assert recreated.id == result.id
    assert recreated.fields[0].evidence is not None
    assert recreated.document_id == document.id
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()
    assert [event.event_type for event in events][-2:] == ["OCR_STARTED", "OCR_COMPLETED"]
    assert events[-1].ocr_result_id == result.id
    assert events[-1].provider == "DEMO / SIMULATED"


def test_unauthorized_ocr_execution_and_read_are_rejected(db: Session) -> None:
    actor, storage, document = prepared(db)
    service = OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider())
    with pytest.raises(LookupError):
        service.process(document.id, uuid4())
    service.process(document.id, actor)
    with pytest.raises(LookupError):
        service.get_latest(document.id, uuid4())


def test_provider_failure_is_safe_and_audited(db: Session) -> None:
    actor, storage, document = prepared(db)

    class BrokenProvider(OCRProvider):
        name = "BROKEN / TEST"
        version = "1"

        def process(self, document, content):
            raise ValueError("provider failed")

    with pytest.raises(RuntimeError, match="could not be completed") as failure:
        OCRService(storage, SqlAlchemyOCRRepository(db), BrokenProvider()).process(document.id, actor)
    assert isinstance(failure.value.__cause__, ValueError)
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.document_id == document.id)).all()
    assert events[-1].event_type == "OCR_FAILED"


def test_storage_failure_is_safe(db: Session) -> None:
    actor, _, document = prepared(db)

    class BrokenStorage(ObjectStorage):
        def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
            raise NotImplementedError

        def delete(self, key: str) -> None:
            return None

        def get(self, key: str) -> bytes:
            raise RuntimeError("storage unavailable")

    with pytest.raises(RuntimeError, match="could not be completed"):
        OCRService(BrokenStorage(), SqlAlchemyOCRRepository(db), DemoOCRProvider()).process(document.id, actor)


def test_arbitrary_uploaded_document_is_not_fabricated_as_demo_ocr(db: Session) -> None:
    actor, storage, document = prepared(db, InMemoryObjectStorage())
    storage.objects[document.storage_key] = b"%PDF-1.7\nordinary content"
    with pytest.raises(RuntimeError):
        OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider()).process(document.id, actor)


def test_raw_ocr_text_is_not_logged(db: Session, caplog: pytest.LogCaptureFixture) -> None:
    actor, storage, document = prepared(db)
    with caplog.at_level(logging.INFO):
        OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider()).process(document.id, actor)
    assert "FICTIONAL DEMO APPLICANT" not in caplog.text
    assert "DEMO-P123456" not in caplog.text


def test_demo_fixture_output_is_explicitly_fictional_and_contains_no_real_pii(db: Session) -> None:
    _, storage, document = prepared(db)
    raw_text, fields, _, _ = DemoOCRProvider().process(document, storage.get(document.storage_key))

    assert "FICTIONAL" in raw_text
    assert all("@" not in field.value for field in fields)
    assert all("password" not in field.value.lower() for field in fields)
    assert "FICTIONAL DEMO APPLICANT" in raw_text


def test_frontend_demo_fixture_passes_document_validation_and_all_demo_markers(db: Session) -> None:
    actor = uuid4()
    storage = InMemoryObjectStorage()
    document_service = DocumentService(storage, SqlAlchemyDocumentRepository(db))
    verification = document_service.create_verification(actor, "fixture@example.test", "Fixture Officer")
    document = document_service.upload(verification.id, actor, "trustid-fictional-demo-passport.pdf", "application/pdf", FRONTEND_DEMO_FIXTURE, DocumentType.PASSPORT)

    ocr = OCRService(storage, SqlAlchemyOCRRepository(db), DemoOCRProvider()).process(document.id, actor)
    assert ocr.status == OCRStatus.COMPLETED
    assert b"TRUSTID-TAMPERING:CLEAN" in storage.get(document.storage_key)
    assert b"TRUSTID-FACE:DOCUMENT" in storage.get(document.storage_key)

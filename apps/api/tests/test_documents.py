from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import Base
from app.domain.documents import (
    MAX_DOCUMENT_SIZE_BYTES,
    DocumentType,
    InMemoryObjectStorage,
    storage_key,
    validate_document_bytes,
)
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.services.document_service import DocumentService

PDF = b"%PDF-1.7\nminimal"


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def service(db: Session, storage: InMemoryObjectStorage | None = None) -> DocumentService:
    return DocumentService(storage or InMemoryObjectStorage(), SqlAlchemyDocumentRepository(db))


def test_validation_rejects_extension_spoofing_and_empty_files() -> None:
    with pytest.raises(ValueError, match="malformed"):
        validate_document_bytes("../../passport.pdf", "application/pdf", b"not a pdf")
    with pytest.raises(ValueError, match="empty"):
        validate_document_bytes("passport.pdf", "application/pdf", b"")


def test_validation_rejects_oversized_files() -> None:
    with pytest.raises(ValueError, match="10 MB"):
        validate_document_bytes("passport.pdf", "application/pdf", b"%PDF-" + b"x" * MAX_DOCUMENT_SIZE_BYTES)


def test_storage_key_is_server_generated() -> None:
    key = storage_key(uuid4(), uuid4(), "application/pdf")
    assert key.startswith("verifications/")
    assert ".." not in key
    assert key.endswith(".pdf")


def test_metadata_relationship_and_audit_survive_service_recreation(db: Session) -> None:
    actor = uuid4()
    storage = InMemoryObjectStorage()
    first = service(db, storage)
    verification = first.create_verification(actor, "officer@example.test", "Officer")
    document = first.upload(verification.id, actor, "../../passport.pdf", "application/pdf", PDF, DocumentType.PASSPORT)

    recreated = service(db, storage)
    assert recreated.ensure_access(verification.id, actor).id == verification.id
    assert recreated.list_documents(verification.id, actor)[0].id == document.id
    assert recreated.get_document(document.id, actor).verification_id == verification.id
    assert [event.event_type for event in recreated.audit_events()] == ["VERIFICATION_CREATED", "DOCUMENT_UPLOADED"]


def test_unauthorized_verification_and_document_access_is_rejected(db: Session) -> None:
    actor = uuid4()
    other = uuid4()
    current = service(db)
    verification = current.create_verification(actor, "officer@example.test", "Officer")
    document = current.upload(verification.id, actor, "passport.pdf", "application/pdf", PDF, DocumentType.PASSPORT)
    with pytest.raises(LookupError):
        current.list_documents(verification.id, other)
    with pytest.raises(LookupError):
        current.get_document(document.id, other)
    with pytest.raises(LookupError):
        current.delete_document(document.id, other)


class FailingCommitRepository(SqlAlchemyDocumentRepository):
    def __init__(self, db: Session) -> None:
        super().__init__(db)
        self.fail_commit = False

    def commit(self) -> None:
        if self.fail_commit:
            raise RuntimeError("database unavailable")
        super().commit()


def test_database_failure_cleans_up_object(db: Session) -> None:
    storage = InMemoryObjectStorage()
    repo = FailingCommitRepository(db)
    current = DocumentService(storage, repo)
    verification = current.create_verification(uuid4(), "officer@example.test", "Officer")
    repo.fail_commit = True
    with pytest.raises(RuntimeError, match="metadata"):
        current.upload(verification.id, verification.owner_id, "passport.pdf", "application/pdf", PDF, DocumentType.PASSPORT)
    assert storage.objects == {}

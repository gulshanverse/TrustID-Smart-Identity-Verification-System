from uuid import uuid4

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.api.dependencies import reconcile_persistent_identity
from app.db.models import Base, User, VerificationModel
from app.domain.auth import Role
from app.domain.documents import (
    MAX_DOCUMENT_SIZE_BYTES,
    DocumentType,
    InMemoryObjectStorage,
    storage_key,
    validate_document_bytes,
)
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.services.auth_service import AuthUser
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


def test_new_user_creates_persistent_user_and_verification(db: Session) -> None:
    owner_id = uuid4()
    verification = service(db).create_verification(owner_id, " Demo.Officer@TrustID.Local ", "Demo Officer")

    user = db.get(User, owner_id)
    assert user is not None
    assert user.email == "demo.officer@trustid.local"
    assert verification.owner_id == owner_id


def test_existing_owner_id_is_reused_without_duplicate_user(db: Session) -> None:
    owner_id = uuid4()
    current = service(db)
    first = current.create_verification(owner_id, "demo.officer@trustid.local", "Demo Officer")
    second = current.create_verification(owner_id, "demo.officer@trustid.local", "Demo Officer")

    assert first.owner_id == second.owner_id == owner_id
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_existing_email_with_new_auth_id_reuses_persistent_user(db: Session) -> None:
    current = service(db)
    first = current.create_verification(uuid4(), "demo.officer@trustid.local", "Demo Officer")
    second = current.create_verification(uuid4(), " DEMO.OFFICER@trustid.local ", "Demo Officer after restart")

    assert second.owner_id == first.owner_id
    assert db.scalar(select(func.count()).select_from(User)) == 1


def test_restart_identity_can_access_existing_verification(db: Session) -> None:
    current = service(db)
    first = current.create_verification(uuid4(), "demo.officer@trustid.local", "Demo Officer")
    restarted_user = AuthUser(uuid4(), "DEMO.OFFICER@TRUSTID.LOCAL", "Demo Officer", "managed", {Role.OFFICER})

    reconcile_persistent_identity(restarted_user, db)

    assert restarted_user.id == first.owner_id
    assert current.ensure_access(first.id, restarted_user.id).id == first.id


def test_multiple_demo_accounts_remain_distinct_and_restart_safe(db: Session) -> None:
    current = service(db)
    officer = current.create_verification(uuid4(), "demo.officer@trustid.local", "Demo Officer")
    auditor = current.create_verification(uuid4(), "demo.auditor@trustid.local", "Demo Auditor")
    restarted_auditor = AuthUser(uuid4(), "demo.auditor@trustid.local", "Demo Auditor", "managed", {Role.AUDITOR})
    reconcile_persistent_identity(restarted_auditor, db)

    assert officer.owner_id != auditor.owner_id
    assert restarted_auditor.id == auditor.owner_id
    assert current.ensure_access(auditor.id, restarted_auditor.id).id == auditor.id
    assert db.scalar(select(func.count()).select_from(User)) == 2


def test_verification_rows_keep_persistent_owner_foreign_key(db: Session) -> None:
    current = service(db)
    persistent_id = current.create_verification(uuid4(), "demo.officer@trustid.local", "Demo Officer").owner_id
    restarted = current.create_verification(uuid4(), "demo.officer@trustid.local", "Demo Officer")

    rows = db.scalars(select(VerificationModel).where(VerificationModel.owner_id == persistent_id)).all()
    assert len(rows) == 2
    assert restarted.owner_id == persistent_id

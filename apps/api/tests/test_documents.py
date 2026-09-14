from uuid import uuid4

import pytest

from app.domain.documents import (
    MAX_DOCUMENT_SIZE_BYTES,
    DocumentType,
    InMemoryObjectStorage,
    storage_key,
    validate_document_bytes,
)
from app.services.document_service import DocumentService

PDF = b"%PDF-1.7\nminimal"


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


def test_authorized_upload_persists_metadata_and_audit_event() -> None:
    actor = uuid4()
    service = DocumentService(InMemoryObjectStorage())
    verification = service.create_verification(actor)
    document = service.upload(verification.id, actor, "../../passport.pdf", "application/pdf", PDF, DocumentType.PASSPORT)
    assert document.status.value == "READY_FOR_ANALYSIS"
    assert document.original_filename == "passport.pdf"
    assert document.verification_id == verification.id
    assert service.audit_events[-1].event_type == "DOCUMENT_UPLOADED"


def test_unauthorized_access_is_rejected() -> None:
    service = DocumentService(InMemoryObjectStorage())
    verification = service.create_verification(uuid4())
    with pytest.raises(LookupError):
        service.upload(verification.id, uuid4(), "passport.pdf", "application/pdf", PDF, DocumentType.PASSPORT)

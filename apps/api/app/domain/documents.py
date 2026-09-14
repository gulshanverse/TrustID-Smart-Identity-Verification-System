from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import PurePath
from uuid import UUID, uuid4

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024


class DocumentType(StrEnum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    PERMIT = "PERMIT"


class DocumentLifecycle(StrEnum):
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"
    FAILED = "FAILED"
    DELETED = "DELETED"


ALLOWED_DOCUMENT_TYPES: dict[str, str] = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}

MAGIC_SIGNATURES: dict[str, tuple[bytes, ...]] = {
    "application/pdf": (b"%PDF-",),
    "image/jpeg": (b"\xff\xd8\xff",),
    "image/png": (b"\x89PNG\r\n\x1a\n",),
    "image/webp": (b"RIFF",),
}


@dataclass(frozen=True)
class StoredObject:
    key: str
    size: int
    checksum: str


@dataclass(frozen=True)
class DocumentRecord:
    id: UUID
    verification_id: UUID
    document_type: DocumentType
    original_filename: str
    storage_key: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    status: DocumentLifecycle
    created_at: str
    updated_at: str


def safe_filename(filename: str | None) -> str:
    """Return display-only filename; it is never used to construct storage keys."""
    name = (filename or "document").replace("\\", "/").split("/")[-1]
    name = "".join(char for char in name if char.isprintable() and char not in {"\x00", "\n", "\r"})
    return name[:180] or "document"


def validate_document_bytes(filename: str | None, declared_mime: str | None, content: bytes) -> tuple[str, str]:
    if not content:
        raise ValueError("The selected file is empty.")
    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise ValueError("The document exceeds the 10 MB maximum size.")
    display_name = safe_filename(filename)
    suffix = PurePath(display_name.lower()).suffix
    expected_mime = ALLOWED_DOCUMENT_TYPES.get(suffix)
    if expected_mime is None:
        raise ValueError("Unsupported document type. Use PDF, JPG, PNG, or WebP.")
    if declared_mime and declared_mime != expected_mime:
        raise ValueError("The file type does not match its declared content type.")
    signatures = MAGIC_SIGNATURES[expected_mime]
    if not any(content.startswith(signature) for signature in signatures):
        raise ValueError("The file content is malformed or does not match its extension.")
    if expected_mime == "image/webp" and (len(content) < 12 or content[8:12] != b"WEBP"):
        raise ValueError("The WebP file content is malformed.")
    return display_name, expected_mime


def storage_key(verification_id: UUID, document_id: UUID, mime_type: str) -> str:
    extension = {"application/pdf": "pdf", "image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}[mime_type]
    return f"verifications/{verification_id}/documents/{document_id}.{extension}"


class ObjectStorage:
    def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
        raise NotImplementedError

    def delete(self, key: str) -> None:
        raise NotImplementedError


class S3ObjectStorage(ObjectStorage):
    """MinIO/S3-compatible storage adapter; credentials never leave the API."""

    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str) -> None:
        self.bucket = bucket
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("Object storage client is not installed.") from exc
        self.client = boto3.client("s3", endpoint_url=endpoint, aws_access_key_id=access_key, aws_secret_access_key=secret_key)

    def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
        import hashlib
        checksum = hashlib.sha256(content).hexdigest()
        self.client.put_object(Bucket=self.bucket, Key=key, Body=BytesIO(content), ContentType=mime_type, ServerSideEncryption="AES256")
        return StoredObject(key=key, size=len(content), checksum=checksum)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


class InMemoryObjectStorage(ObjectStorage):
    """Test-only fake that preserves real put/delete semantics without public files."""

    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}

    def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
        import hashlib
        self.objects[key] = content
        return StoredObject(key=key, size=len(content), checksum=hashlib.sha256(content).hexdigest())

    def delete(self, key: str) -> None:
        self.objects.pop(key, None)


def new_document_id() -> UUID:
    return uuid4()

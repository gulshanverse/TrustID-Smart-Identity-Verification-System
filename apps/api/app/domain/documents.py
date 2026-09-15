from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO
from pathlib import PurePath
from typing import cast
from uuid import UUID, uuid4

from botocore.config import Config

MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
logger = logging.getLogger("trustid.storage")


def safe_error_message(exc: BaseException) -> str:
    message = str(exc)
    message = re.sub(r"https?://[^\s'\"]+", "<url>", message)
    message = re.sub(r"(?i)(access[_-]?key|secret[_-]?key|token|password|authorization|cookie|database[_-]?url|redis[_-]?url)[=:][^\s,;]+", r"\1=<redacted>", message)
    message = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", "<email>", message)
    return message[:240] or "storage operation failed"


def safe_exception_message(exc: BaseException) -> str:
    messages: list[str] = []
    current: BaseException | None = exc
    seen: set[int] = set()
    while current is not None and id(current) not in seen and len(messages) < 3:
        seen.add(id(current))
        messages.append(f"{type(current).__name__}: {safe_error_message(current)}")
        current = current.__cause__ or current.__context__
    return " | ".join(messages)


class DocumentType(StrEnum):
    PASSPORT = "PASSPORT"
    VISA = "VISA"
    NATIONAL_ID = "NATIONAL_ID"
    DRIVING_LICENSE = "DRIVING_LICENSE"
    PERMIT = "PERMIT"


class DocumentLifecycle(StrEnum):
    READY_FOR_ANALYSIS = "READY_FOR_ANALYSIS"
    OCR_COMPLETE = "OCR_COMPLETE"
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

    def get(self, key: str) -> bytes:
        raise NotImplementedError


class S3ObjectStorage(ObjectStorage):
    """MinIO/S3-compatible storage adapter; credentials never leave the API."""

    def __init__(self, endpoint: str, bucket: str, access_key: str, secret_key: str, region: str = "us-east-1") -> None:
        self.bucket = bucket
        try:
            import boto3
        except ImportError as exc:  # pragma: no cover - deployment dependency
            raise RuntimeError("Object storage client is not installed.") from exc
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint,
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=Config(s3={"addressing_style": "path"}),
        )

    def _log_storage_error(self, operation: str, key: str, exc: Exception) -> None:
        logger.warning(
            "s3_storage_operation_failed operation=%s storage_key=%s error_type=%s error_message=%s",
            operation,
            key,
            type(exc).__name__,
            safe_exception_message(exc),
        )

    def put(self, key: str, content: bytes, mime_type: str) -> StoredObject:
        import hashlib
        checksum = hashlib.sha256(content).hexdigest()
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=BytesIO(content), ContentType=mime_type)
        except Exception as exc:
            self._log_storage_error("put", key, exc)
            raise
        return StoredObject(key=key, size=len(content), checksum=checksum)

    def delete(self, key: str) -> None:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            self._log_storage_error("delete", key, exc)
            raise

    def get(self, key: str) -> bytes:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
        except Exception as exc:
            self._log_storage_error("get", key, exc)
            raise
        return cast(bytes, response["Body"].read())


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

    def get(self, key: str) -> bytes:
        if key not in self.objects:
            raise FileNotFoundError("Stored document not found.")
        return self.objects[key]


def new_document_id() -> UUID:
    return uuid4()

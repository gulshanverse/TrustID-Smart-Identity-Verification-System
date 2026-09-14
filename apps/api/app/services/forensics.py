from __future__ import annotations

from dataclasses import dataclass

from app.domain.documents import MAGIC_SIGNATURES, MAX_DOCUMENT_SIZE_BYTES


@dataclass(frozen=True)
class DocumentProfile:
    mime_type: str
    size: int
    format_name: str
    is_image: bool
    width: int | None = None
    height: int | None = None


def inspect_document(content: bytes, declared_mime: str) -> DocumentProfile:
    if not content or len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise ValueError("The document exceeds the permitted analysis size.")
    if declared_mime not in MAGIC_SIGNATURES:
        raise ValueError("Unsupported document format.")
    if not any(content.startswith(signature) for signature in MAGIC_SIGNATURES[declared_mime]):
        raise ValueError("The document format is malformed.")
    if declared_mime == "image/webp" and (len(content) < 12 or content[8:12] != b"WEBP"):
        raise ValueError("The WebP document is malformed.")
    formats = {"application/pdf": "PDF", "image/jpeg": "JPEG", "image/png": "PNG", "image/webp": "WebP"}
    return DocumentProfile(declared_mime, len(content), formats[declared_mime], declared_mime.startswith("image/"))

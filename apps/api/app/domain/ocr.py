from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.documents import DocumentRecord, DocumentType


class OCRStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class OCREvidence:
    page: int | None = None
    text: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    line_index: int | None = None


@dataclass(frozen=True)
class OCRField:
    name: str
    value: str
    normalized_value: str
    confidence: float
    source_text: str
    evidence: OCREvidence | None = None


@dataclass(frozen=True)
class OCRResult:
    id: UUID
    document_id: UUID
    status: OCRStatus
    raw_text: str
    language: str
    overall_confidence: float
    provider: str
    provider_version: str
    fields: tuple[OCRField, ...]
    created_at: str
    updated_at: str


class OCRProvider:
    name = "provider"
    version = "unknown"

    def process(self, document: DocumentRecord, content: bytes) -> tuple[str, tuple[OCRField, ...], float, str]:
        raise NotImplementedError


class DemoOCRProvider(OCRProvider):
    name = "DEMO / SIMULATED"
    version = "1.0"

    def process(self, document: DocumentRecord, content: bytes) -> tuple[str, tuple[OCRField, ...], float, str]:
        if b"TRUSTID-DEMO-OCR:" not in content:
            raise ValueError("The demo OCR provider only processes explicitly marked demo fixtures.")
        if document.document_type == DocumentType.PASSPORT:
            values: Sequence[tuple[str, str]] = (
                ("full_name", "ARUN MEHTA"), ("passport_number", "DEMO-P123456"),
                ("nationality", "DEMO REPUBLIC"), ("date_of_birth", "1998-04-12"),
                ("expiry_date", "2030-04-11"), ("gender", "X"),
            )
        elif document.document_type == DocumentType.VISA:
            values = (("visa_number", "DEMO-V123456"), ("visa_type", "VISITOR"), ("entry_validity", "2026-12-31"), ("stay_duration", "30 days"))
        else:
            values = (("document_type", document.document_type.replace("_", " ").title()), ("reference", "DEMO-REFERENCE"))
        raw_text = "\n".join(f"{name}: {value}" for name, value in values)
        fields = tuple(OCRField(name, value, value, 0.97, value, OCREvidence(page=1, text=value, line_index=index)) for index, (name, value) in enumerate(values))
        return raw_text, fields, 0.97, "en"


def new_ocr_result_id() -> UUID:
    return uuid4()

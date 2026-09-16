from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any
from uuid import UUID, uuid4

from app.domain.document_quality import (
    DocumentQuality,
    QualityStatus,
    assess_image_quality,
    assess_pdf_quality,
)
from app.domain.documents import DocumentRecord, DocumentType
from app.domain.mrz import MRZResult, compare_fields, parse_td3


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
    quality: DocumentQuality = field(default_factory=lambda: DocumentQuality(QualityStatus.REVIEW, 0, {}, ("Quality was not assessed.",)))
    mrz: MRZResult = field(default_factory=lambda: parse_td3(""))
    field_consistency: tuple[dict[str, str | None], ...] = ()


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
            values: Sequence[tuple[str, str]] = (("full_name", "FICTIONAL DEMO APPLICANT"), ("passport_number", "DEMO-P123456"), ("nationality", "DEMO REPUBLIC"), ("date_of_birth", "1998-04-12"), ("expiry_date", "2030-04-11"), ("gender", "X"))
        elif document.document_type == DocumentType.VISA:
            values = (("visa_number", "DEMO-V123456"), ("visa_type", "VISITOR"), ("entry_validity", "2026-12-31"), ("stay_duration", "30 days"))
        else:
            values = (("document_type", document.document_type.replace("_", " ").title()), ("reference", "DEMO-REFERENCE"))
        raw_text = "\n".join(f"{name}: {value}" for name, value in values)
        fields = tuple(OCRField(name, value, value, 0.97, value, OCREvidence(page=1, text=value, line_index=index)) for index, (name, value) in enumerate(values))
        return raw_text, fields, 0.97, "en"


class ProductionOCRProvider(OCRProvider):
    name = "REAL AI / PRODUCTION"
    version = "tesseract-local-1"
    timeout_seconds = 15

    def process(self, document: DocumentRecord, content: bytes) -> tuple[str, tuple[OCRField, ...], float, str]:
        try:
            import pytesseract
            from PIL import Image
        except ImportError as exc:
            raise RuntimeError("Production OCR dependencies are not installed.") from exc
        try:
            if document.mime_type == "application/pdf":
                from pdf2image import convert_from_bytes

                pages = convert_from_bytes(content, dpi=220, first_page=1, last_page=5, thread_count=1, timeout=self.timeout_seconds)
                outputs = [self._ocr_image(pytesseract, page) for page in pages]
            else:
                with Image.open(__import__("io").BytesIO(content)) as image:
                    outputs = [self._ocr_image(pytesseract, image)]
            raw_text = "\n".join(item[0] for item in outputs)
            confidences = [item[1] for item in outputs if item[1] is not None]
        except Exception as exc:
            raise RuntimeError(f"Local OCR engine failed: {type(exc).__name__}.") from exc
        fields = list(_extract_conservative_fields(raw_text, document.document_type))
        mrz = parse_td3(raw_text) if document.document_type == DocumentType.PASSPORT else parse_td3("")
        if mrz.detected:
            mrz_mapping = {"document_number": "passport_number", "date_of_birth": "date_of_birth", "expiry_date": "expiry_date", "sex": "gender"}
            existing = {item.name for item in fields}
            mrz_name = " ".join(value for key in ("surname", "given_names") if (value := mrz.fields.get(key)))
            if mrz_name and "full_name" not in existing:
                fields.append(OCRField("full_name", mrz_name, mrz_name.upper(), 0.95 if mrz.valid else 0.6, "MRZ"))
            for mrz_name, field_name in mrz_mapping.items():
                value = mrz.fields.get(mrz_name)
                if value and field_name not in existing:
                    fields.append(OCRField(field_name, value, value.upper(), 0.95 if mrz.valid else 0.6, "MRZ"))
        confidence = 0.0 if not raw_text.strip() else sum(confidences) / len(confidences) if confidences else 0.0
        return raw_text, tuple(fields), confidence, "eng"

    def _ocr_image(self, pytesseract: Any, image: Any) -> tuple[str, float | None]:
        text = pytesseract.image_to_string(image, config="--psm 6", timeout=self.timeout_seconds)
        if not hasattr(pytesseract, "image_to_data"):
            return text, None
        data = pytesseract.image_to_data(image, config="--psm 6", timeout=self.timeout_seconds, output_type=pytesseract.Output.DICT)
        values = [float(value) for value, token in zip(data.get("conf", []), data.get("text", []), strict=False) if token.strip() and float(value) >= 0]
        return text, None if not values else sum(values) / len(values) / 100


def _extract_conservative_fields(raw_text: str, document_type: str) -> tuple[OCRField, ...]:
    import re

    patterns = {"passport_number": r"(?im)\b(?:passport|document)\s*(?:number|no|#)\s*[:\-]?\s*([A-Z0-9<]{5,})", "date_of_birth": r"(?im)\b(?:date\s*of\s*birth|dob)\s*[:\-]?\s*([0-9]{4}[-/]?[0-9]{2}[-/]?[0-9]{2})", "expiry_date": r"(?im)\b(?:expiry|expiration)\s*(?:date)?\s*[:\-]?\s*([0-9]{4}[-/]?[0-9]{2}[-/]?[0-9]{2})", "nationality": r"(?im)\bnationality\s*[:\-]?\s*([A-Z][A-Z ]{2,})", "gender": r"(?im)\b(?:sex|gender)\s*[:\-]?\s*([XMF])"}
    output: list[OCRField] = []
    for name, pattern in patterns.items():
        match = re.search(pattern, raw_text)
        if match:
            value = match.group(1).strip()
            output.append(OCRField(name, value, value.upper(), 0.5, match.group(0)))
    return tuple(output)


def intelligence_for(document: DocumentRecord, content: bytes, raw_text: str, fields: tuple[OCRField, ...]) -> tuple[DocumentQuality, MRZResult, tuple[dict[str, str | None], ...]]:
    quality = assess_pdf_quality(content) if document.mime_type == "application/pdf" else assess_image_quality(content)
    mrz = parse_td3(raw_text) if document.document_type == DocumentType.PASSPORT else parse_td3("")
    visual: dict[str, str | None] = {item.name: item.normalized_value for item in fields}
    return quality, mrz, tuple(compare_fields(visual, mrz)) if mrz.detected else ()


def new_ocr_result_id() -> UUID:
    return uuid4()

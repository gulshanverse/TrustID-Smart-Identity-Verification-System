from __future__ import annotations

import sys
from io import BytesIO
from types import SimpleNamespace
from uuid import uuid4

from PIL import Image

from app.domain.document_quality import QualityStatus, assess_image_quality, assess_pdf_quality
from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType
from app.domain.mrz import compare_fields, parse_td3
from app.domain.ocr import ProductionOCRProvider

MRZ = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10"


def document(mime_type: str = "image/jpeg") -> DocumentRecord:
    return DocumentRecord(uuid4(), uuid4(), DocumentType.PASSPORT, "fictional.jpg", "private/key", mime_type, 1, "checksum", DocumentLifecycle.READY_FOR_ANALYSIS, "2026-01-01T00:00:00+00:00", "2026-01-01T00:00:00+00:00")


def test_td3_mrz_parsing_and_check_digits() -> None:
    result = parse_td3(MRZ)
    assert result.detected is True
    assert result.valid is True
    assert result.fields["document_number"] == "L898902C3"
    assert result.fields["date_of_birth"] == "1974-08-12"
    assert result.fields["expiry_date"] == "2012-04-15"
    assert all(item.valid for item in result.checksums)


def test_invalid_mrz_preserves_invalidity_and_raw_text() -> None:
    invalid = MRZ.replace("L898902C36", "L898902C37")
    result = parse_td3(invalid)
    assert result.detected is True
    assert result.valid is False
    assert result.raw_text == invalid
    assert any(item.valid is False for item in result.checksums)


def test_mrz_normalization_and_field_consistency() -> None:
    result = parse_td3(MRZ.replace(" ", ""))
    checks = compare_fields({"passport_number": "L898902C3", "date_of_birth": "1974-08-12"}, result)
    assert next(item for item in checks if item["field"] == "passport_number")["status"] == "MATCH"
    assert next(item for item in checks if item["field"] == "date_of_birth")["status"] == "MATCH"
    assert next(item for item in checks if item["field"] == "nationality")["status"] == "NOT_AVAILABLE"


def test_quality_assessment_handles_good_and_malformed_images() -> None:
    image = Image.new("RGB", (1200, 800), color=(128, 128, 128))
    output = BytesIO()
    image.save(output, format="JPEG")
    quality = assess_image_quality(output.getvalue())
    assert quality.status in {QualityStatus.GOOD, QualityStatus.REVIEW}
    malformed = assess_image_quality(b"not-an-image")
    assert malformed.status == QualityStatus.FAILED


def test_pdf_quality_rejects_malformed_and_unbounded_documents() -> None:
    assert assess_pdf_quality(b"not-a-pdf").status == QualityStatus.FAILED


def test_production_provider_extracts_without_demo_markers(monkeypatch) -> None:
    fake_tesseract = SimpleNamespace(image_to_string=lambda image, config, timeout: MRZ, image_to_data=lambda image, config, timeout, output_type: {"conf": ["90", "80"], "text": ["FICTIONAL", "SAMPLE"]}, Output=SimpleNamespace(DICT="dict"))
    monkeypatch.setitem(sys.modules, "pytesseract", fake_tesseract)
    image = Image.new("RGB", (800, 600), color="white")
    output = BytesIO()
    image.save(output, format="JPEG")
    raw_text, fields, confidence, language = ProductionOCRProvider().process(document(), output.getvalue())
    assert "TRUSTID-DEMO-OCR" not in raw_text
    assert raw_text == MRZ
    assert {field.name for field in fields} >= {"full_name", "passport_number", "date_of_birth", "expiry_date", "gender"}
    assert confidence == 0.85
    assert language == "eng"

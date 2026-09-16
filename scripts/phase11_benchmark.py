from __future__ import annotations

import argparse
import json
import resource
import re
import shutil
import sys
import time
from uuid import uuid4
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))
MRZ = "P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<<<<<\nL898902C36UTO7408122F1204159ZE184226B<<<<<10"


def make_pdf(path: Path, pages: int = 1) -> None:
    pdf = BytesIO()
    writer = canvas.Canvas(pdf, pagesize=(1200, 800))
    for page in range(pages):
        writer.setFont("Helvetica", 24)
        writer.drawString(70, 740, "FICTIONAL SAMPLE - NOT A REAL IDENTITY")
        writer.drawString(70, 700, "AARAV TESTER / PASSPORT T0000001 / UTO")
        writer.drawString(70, 650, "01 JAN 1995 / M / 01 JAN 2035")
        writer.drawString(70, 90, MRZ.splitlines()[0])
        writer.drawString(70, 55, MRZ.splitlines()[1])
        writer.showPage()
    writer.save()
    path.write_bytes(pdf.getvalue())


def make_image(path: Path, *, variant: str) -> None:
    image = Image.new("RGB", (1600, 1000), "white")
    from PIL import ImageDraw, ImageFont

    draw = ImageDraw.Draw(image)
    font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
    mrz_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 30)
    draw.text((80, 80), "FICTIONAL SAMPLE - NOT A REAL IDENTITY", fill="black", font=font)
    draw.text((80, 150), "AARAV TESTER", fill="black", font=font)
    draw.text((80, 210), "PASSPORT NO: T0000001", fill="black", font=font)
    draw.text((80, 270), "NATIONALITY: UTO", fill="black", font=font)
    draw.text((80, 330), "DATE OF BIRTH: 1995-01-01", fill="black", font=font)
    draw.text((80, 390), "SEX: M", fill="black", font=font)
    draw.text((80, 450), "EXPIRY DATE: 2035-01-01", fill="black", font=font)
    draw.text((80, 800), MRZ.splitlines()[0], fill="black", font=mrz_font)
    draw.text((80, 850), MRZ.splitlines()[1], fill="black", font=mrz_font)
    if variant == "low_resolution":
        image = image.resize((500, 312))
    elif variant == "rotated":
        image = image.rotate(3, expand=True, fillcolor="white")
    elif variant == "low_contrast":
        image = ImageEnhance.Contrast(image).enhance(0.35)
    elif variant == "overexposed":
        image = ImageEnhance.Brightness(image).enhance(2.2)
    elif variant == "underexposed":
        image = ImageEnhance.Brightness(image).enhance(0.25)
    elif variant == "blurred":
        image = image.filter(ImageFilter.GaussianBlur(3))
    elif variant == "compressed":
        output = BytesIO()
        image.save(output, format="JPEG", quality=20)
        path.write_bytes(output.getvalue())
        return
    image.save(path, format="PNG")


def build_corpus(directory: Path) -> list[Path]:
    directory.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    variants = ["clean", "low_resolution", "rotated", "low_contrast", "overexposed", "underexposed", "blurred", "compressed"]
    for index, variant in enumerate(variants, 1):
        path = directory / f"TEST-{index:02d}-{variant}.png"
        make_image(path, variant=variant)
        paths.append(path)
    mismatch = directory / "TEST-09-mismatch.png"
    make_image(mismatch, variant="clean")
    mismatch.write_bytes(mismatch.read_bytes().replace(b"T0000001", b"T0000002"))
    paths.append(mismatch)
    paths.append(directory / "TEST-10-valid-mrz.txt")
    paths[-1].write_text(MRZ)
    paths.append(directory / "TEST-11-invalid-mrz.txt")
    paths[-1].write_text(MRZ.replace("L898902C36", "L898902C37"))
    paths.append(directory / "TEST-12-malformed-mrz.txt")
    paths[-1].write_text("P<UTOINVALID\nNOT-A-TD3-MRZ")
    paths.append(directory / "TEST-13-no-mrz.png")
    make_image(paths[-1], variant="clean")
    paths[-1].write_bytes(paths[-1].read_bytes().replace(b"P<UTOERIKSSON<<ANNA<MARIA<<<<<<<<<<<<<<<", b"NO-MRZ-DATA"))
    for name, pages in (("TEST-14-text.pdf", 1), ("TEST-15-multipage.pdf", 3)):
        path = directory / name
        make_pdf(path, pages)
        paths.append(path)
    (directory / "TEST-16-malformed.pdf").write_bytes(b"%PDF-1.7\nmalformed")
    paths.append(directory / "TEST-16-malformed.pdf")
    large = directory / "TEST-17-pathological.png"
    Image.new("RGB", (3000, 3000), "white").save(large, format="PNG")
    paths.append(large)
    return paths


def _document(path: Path):
    from app.domain.documents import DocumentLifecycle, DocumentRecord, DocumentType

    mime = {".pdf": "application/pdf", ".png": "image/png", ".jpg": "image/jpeg", ".txt": "text/plain"}[path.suffix]
    now = "2026-01-01T00:00:00+00:00"
    return DocumentRecord(uuid4(), uuid4(), DocumentType.PASSPORT, path.name, str(path), mime, path.stat().st_size, "synthetic", DocumentLifecycle.READY_FOR_ANALYSIS, now, now)


def _field_accuracy(fields) -> dict[str, object]:
    expected = {"passport_number": "T0000001", "nationality": "UTO", "date_of_birth": "1995-01-01", "gender": "M", "expiry_date": "2035-01-01"}
    actual = {field.name: field.normalized_value for field in fields}
    results = {name: actual.get(name) == value for name, value in expected.items()}
    return {"fields": results, "available": sum(results.values()), "total": len(results), "accuracy": sum(results.values()) / len(results)}


def _edit_distance(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, 1):
        current = [row]
        for column, right_char in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[column] + 1, previous[column - 1] + (left_char != right_char)))
        previous = current
    return previous[-1]


def _ocr_error_metrics(raw_text: str) -> dict[str, float | None]:
    expected = "FICTIONAL SAMPLE NOT A REAL IDENTITY AARAV TESTER PASSPORT NO T0000001 NATIONALITY UTO DATE OF BIRTH 1995 01 01 SEX M EXPIRY DATE 2035 01 01"
    actual = re.sub(r"[^A-Z0-9 ]", "", raw_text.upper())
    expected_words, actual_words = expected.split(), actual.split()
    return {"cer": _edit_distance(actual.replace(" ", ""), expected.replace(" ", "")) / len(expected.replace(" ", "")), "wer": _edit_distance(actual_words, expected_words) / len(expected_words)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="docs/phase-1.1-corpus")
    parser.add_argument("--keep", action="store_true")
    args = parser.parse_args()
    directory = ROOT / args.output
    if directory.exists():
        shutil.rmtree(directory)
    paths = build_corpus(directory)
    from app.domain.document_quality import assess_image_quality, assess_pdf_quality
    from app.domain.mrz import parse_td3
    from app.domain.ocr import ProductionOCRProvider

    records: list[dict[str, object]] = []
    for path in paths:
        content = path.read_bytes()
        started = time.perf_counter()
        if path.suffix == ".pdf":
            quality = assess_pdf_quality(content)
        elif path.suffix in {".png", ".jpg"}:
            quality = assess_image_quality(content)
        else:
            quality = None
        mrz = parse_td3(content.decode(errors="ignore")) if path.suffix == ".txt" else parse_td3("")
        record: dict[str, object] = {"fixture": path.name, "format": path.suffix.lstrip("."), "bytes": len(content), "quality": None if quality is None else quality.as_dict(), "mrz_detected": mrz.detected, "mrz_valid": mrz.valid, "processing_ms": None, "peak_rss_kb": None, "ocr_available": shutil.which("tesseract") is not None, "ocr_success": False, "ocr_text": None, "structured_fields": [], "field_accuracy": None, "ocr_confidence": None, "error": None}
        if path.suffix != ".txt" and shutil.which("tesseract") is not None:
            try:
                raw_text, fields, confidence, language = ProductionOCRProvider().process(_document(path), content)
                ocr_mrz = parse_td3(raw_text)
                record.update({"ocr_success": True, "ocr_text": raw_text, "structured_fields": [{"name": field.name, "value": field.value, "confidence": field.confidence} for field in fields], "field_accuracy": _field_accuracy(fields), "ocr_error_metrics": _ocr_error_metrics(raw_text), "ocr_confidence": confidence, "ocr_language": language, "mrz_detected": ocr_mrz.detected, "mrz_valid": ocr_mrz.valid, "mrz_checksum_results": [item.__dict__ for item in ocr_mrz.checksums]})
            except Exception as exc:
                record["error"] = type(exc).__name__
        record["processing_ms"] = round((time.perf_counter() - started) * 1000, 2)
        record["peak_rss_kb"] = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        records.append(record)
    output = directory / "benchmark.json"
    output.write_text(json.dumps({"tesseract": shutil.which("tesseract"), "max_rss_kb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss, "records": records}, indent=2))
    print(output)
    if not args.keep:
        print("Corpus retained for reproducibility; remove it manually after review.")


if __name__ == "__main__":
    main()

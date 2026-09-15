from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from io import BytesIO

from PIL import Image, ImageStat, UnidentifiedImageError


class QualityStatus(StrEnum):
    GOOD = "GOOD"
    REVIEW = "REVIEW"
    FAILED = "FAILED"


@dataclass(frozen=True)
class DocumentQuality:
    status: QualityStatus
    score: int
    signals: dict[str, str | float | int]
    reasons: tuple[str, ...]

    def as_dict(self) -> dict[str, object]:
        return {"status": self.status.value, "score": self.score, "signals": self.signals, "reasons": list(self.reasons)}


def assess_image_quality(content: bytes, *, max_pixels: int = 25_000_000) -> DocumentQuality:
    try:
        with Image.open(BytesIO(content)) as image:
            width, height = image.size
            if width * height > max_pixels:
                return DocumentQuality(QualityStatus.FAILED, 0, {"width": width, "height": height}, ("Image exceeds the safe pixel limit.",))
            gray = image.convert("L")
            brightness = float(ImageStat.Stat(gray).mean[0])
            contrast = float(ImageStat.Stat(gray).rms[0] - brightness)
            resolution_score = min(100.0, (width * height) / 2_000_000 * 100)
            score = int(max(0, min(100, resolution_score * 0.45 + min(100, contrast * 2) * 0.35 + (100 - abs(brightness - 128) / 1.28) * 0.2)))
            reasons: list[str] = []
            if min(width, height) < 600:
                reasons.append("Image resolution may be insufficient for reliable OCR.")
            if brightness < 35:
                reasons.append("Image is severely underexposed.")
            if brightness > 235:
                reasons.append("Image may be overexposed or affected by glare.")
            if contrast < 18:
                reasons.append("Image contrast is low.")
            status = QualityStatus.GOOD if score >= 65 and not reasons else QualityStatus.REVIEW if score >= 35 else QualityStatus.FAILED
            return DocumentQuality(status, score, {"width": width, "height": height, "brightness": round(brightness, 2), "contrast": round(contrast, 2)}, tuple(reasons))
    except (UnidentifiedImageError, OSError) as exc:
        return DocumentQuality(QualityStatus.FAILED, 0, {}, (f"Image could not be decoded: {type(exc).__name__}.",))


def assess_pdf_quality(content: bytes, *, max_pages: int = 5) -> DocumentQuality:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(content), strict=False)
        page_count = len(reader.pages)
        if page_count == 0:
            return DocumentQuality(QualityStatus.FAILED, 0, {"page_count": 0}, ("PDF has no pages.",))
        if page_count > max_pages:
            return DocumentQuality(QualityStatus.FAILED, 0, {"page_count": page_count}, (f"PDF exceeds the {max_pages}-page processing limit.",))
        text_length = sum(len((page.extract_text() or "").strip()) for page in reader.pages)
        score = 85 if text_length else 60
        reason = () if text_length else ("PDF has no extractable text; rendered OCR may still be attempted.",)
        return DocumentQuality(QualityStatus.GOOD if text_length else QualityStatus.REVIEW, score, {"page_count": page_count, "extractable_text_length": text_length}, reason)
    except Exception as exc:  # noqa: BLE001
        return DocumentQuality(QualityStatus.FAILED, 0, {}, (f"PDF could not be safely read: {type(exc).__name__}.",))

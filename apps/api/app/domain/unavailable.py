from __future__ import annotations

from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationResult, FaceVerificationStatus
from app.domain.ocr import OCRResult, OCRStatus
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import DocumentValidationResult, ValidationStatus


def unavailable_id(verification_id: UUID, module: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trustid:unavailable:{verification_id}:{module}")


def unavailable_ocr(verification_id: UUID, document_id: UUID) -> OCRResult:
    return OCRResult(unavailable_id(verification_id, "ocr"), document_id, OCRStatus.FAILED, "", "", 0.0, "UNAVAILABLE", "none", (), "", "")


def unavailable_validation(verification_id: UUID, document_id: UUID) -> DocumentValidationResult:
    return DocumentValidationResult(unavailable_id(verification_id, "validation"), document_id, ValidationStatus.UNAVAILABLE, "UNAVAILABLE", "none", "Document validation is unavailable.", (), "", "")


def unavailable_tampering(verification_id: UUID, document_id: UUID) -> TamperingResult:
    return TamperingResult(unavailable_id(verification_id, "tampering"), document_id, TamperingStatus.NOT_AVAILABLE, 0.0, 0.0, "UNAVAILABLE", "none", "Tampering analysis is NOT_AVAILABLE.", (), "", "")


def unavailable_face(verification_id: UUID, document_id: UUID) -> FaceVerificationResult:
    return FaceVerificationResult(unavailable_id(verification_id, "face"), verification_id, document_id, FaceVerificationStatus.FAILED, FaceOutcome.NOT_AVAILABLE, None, None, "UNAVAILABLE", "none", "Face verification is NOT_AVAILABLE.", None, FaceQuality.LOW_QUALITY, FaceQuality.LOW_QUALITY, None, (), "", "")

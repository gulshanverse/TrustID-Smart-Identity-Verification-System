from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.documents import DocumentRecord


class FaceVerificationStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class FaceOutcome(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    REVIEW = "REVIEW"
    UNAVAILABLE = "UNAVAILABLE"


class FaceQuality(StrEnum):
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    LOW_QUALITY = "LOW_QUALITY"
    UNSUPPORTED_IMAGE = "UNSUPPORTED_IMAGE"
    READY = "READY"


class FaceScenario(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    REVIEW = "REVIEW"
    NO_FACE = "NO_FACE"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    LOW_QUALITY = "LOW_QUALITY"


@dataclass(frozen=True)
class FaceEvidence:
    name: str
    value: str
    explanation: str


@dataclass(frozen=True)
class FaceVerificationResult:
    id: UUID
    verification_id: UUID
    document_id: UUID
    status: FaceVerificationStatus
    outcome: FaceOutcome
    similarity_score: float | None
    confidence: float | None
    provider: str
    provider_version: str
    summary: str
    failure_reason: str | None
    document_face_quality: FaceQuality
    presented_face_quality: FaceQuality
    face_count: int | None
    evidence: tuple[FaceEvidence, ...]
    created_at: str
    updated_at: str


class DocumentFaceExtractor:
    def extract(self, document: DocumentRecord, content: bytes) -> tuple[FaceQuality, str]:
        raise NotImplementedError


class DemoDocumentFaceExtractor(DocumentFaceExtractor):
    def extract(self, document: DocumentRecord, content: bytes) -> tuple[FaceQuality, str]:
        if b"TRUSTID-FACE:DOCUMENT" not in content:
            return FaceQuality.LOW_QUALITY, "Document face fixture is not available."
        return FaceQuality.READY, "Document face available from deterministic fixture."


class FaceVerificationProvider:
    name = "provider"
    version = "unknown"

    def compare(self, document_face: bytes, presented_face: bytes, scenario: FaceScenario) -> tuple[FaceOutcome, float | None, float | None, str, str | None, FaceQuality, int | None]:
        raise NotImplementedError


class DemoFaceVerificationProvider(FaceVerificationProvider):
    name = "DEMO / SIMULATED"
    version = "1.0"
    threshold = 0.80

    def compare(self, document_face: bytes, presented_face: bytes, scenario: FaceScenario) -> tuple[FaceOutcome, float | None, float | None, str, str | None, FaceQuality, int | None]:
        marker = f"TRUSTID-FACE:{scenario.value}".encode()
        if marker not in presented_face or b"TRUSTID-FACE:DOCUMENT" not in document_face:
            raise ValueError("The demo face provider only processes explicitly marked fixtures.")
        values = {
            FaceScenario.MATCH: (FaceOutcome.MATCH, 0.94, 0.91, "The presented face is sufficiently consistent with the document face under the configured comparison threshold.", None, FaceQuality.READY, 1),
            FaceScenario.MISMATCH: (FaceOutcome.MISMATCH, 0.31, 0.94, "The compared faces did not meet the configured similarity threshold. Officer review is recommended.", None, FaceQuality.READY, 1),
            FaceScenario.REVIEW: (FaceOutcome.REVIEW, 0.68, 0.62, "The comparison was inconclusive or did not meet the conditions for a reliable automated result.", "Comparison requires human review.", FaceQuality.READY, 1),
            FaceScenario.NO_FACE: (FaceOutcome.UNAVAILABLE, None, None, "Face verification could not be completed.", "No usable face was detected.", FaceQuality.NO_FACE, 0),
            FaceScenario.MULTIPLE_FACES: (FaceOutcome.UNAVAILABLE, None, None, "Face verification could not be completed.", "Multiple faces were detected. Please provide a clear single-person image.", FaceQuality.MULTIPLE_FACES, 2),
            FaceScenario.LOW_QUALITY: (FaceOutcome.UNAVAILABLE, None, None, "Face verification could not be completed.", "The presented image does not meet the minimum quality requirements.", FaceQuality.LOW_QUALITY, 1),
        }
        return values[scenario]


def new_face_result_id() -> UUID:
    return uuid4()

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import Any
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
    threshold = 0.80

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


class ProductionFaceVerificationProvider(FaceVerificationProvider):
    """Offline OpenCV Haar detection + SFace ONNX embedding comparison.

    The model file is deliberately supplied by deployment configuration; production
    never downloads weights and never falls back to the demo provider.
    """

    name = "REAL AI / PRODUCTION"
    version = "OpenCV SFace 2021-12 + Haar detector / algorithm v1"
    algorithm = "SFace cosine similarity with normalized 112x112 face crops"
    model_version = "face_recognition_sface_2021dec.onnx"
    threshold = 0.363
    review_threshold = 0.30
    min_face_pixels = 80 * 80

    def __init__(self, model_path: str | Path) -> None:
        self.model_path = Path(model_path)
        if not self.model_path.is_file():
            raise RuntimeError("The configured production face model is unavailable.")
        try:
            cv2: Any = __import__("cv2")
        except ImportError as exc:  # pragma: no cover - environment-specific
            raise RuntimeError("The production face runtime is not installed.") from exc
        self._cv2 = cv2
        cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
        self._detector = cv2.CascadeClassifier(str(cascade_path))
        if self._detector.empty():
            raise RuntimeError("The production face detector is unavailable.")
        try:
            self._recognizer = cv2.face
        except Exception as exc:
            raise RuntimeError("The OpenCV face-recognition module is unavailable.") from exc
        try:
            self._recognizer = cv2.FaceRecognizerSF_create(str(self.model_path), "")
        except Exception as exc:
            raise RuntimeError("The configured production face model could not be loaded.") from exc

    def _decode(self, content: bytes) -> Any:
        np: Any = __import__("numpy")
        image = self._cv2.imdecode(np.frombuffer(content, dtype=np.uint8), self._cv2.IMREAD_COLOR)
        if image is None or image.size == 0:
            raise ValueError("The image could not be decoded.")
        height, width = image.shape[:2]
        if width < 160 or height < 160 or width * height > 25_000_000:
            raise ValueError("The image dimensions are not suitable for face verification.")
        return image

    def _faces(self, image: Any) -> list[tuple[int, int, int, int]]:
        gray = self._cv2.cvtColor(image, self._cv2.COLOR_BGR2GRAY)
        faces = self._detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(40, 40))
        return [(int(face[0]), int(face[1]), int(face[2]), int(face[3])) for face in faces]

    def _quality(self, image: Any, face: tuple[int, int, int, int]) -> tuple[FaceQuality, str]:
        x, y, width, height = face
        crop = image[y:y + height, x:x + width]
        gray = self._cv2.cvtColor(crop, self._cv2.COLOR_BGR2GRAY)
        sharpness = float(self._cv2.Laplacian(gray, self._cv2.CV_64F).var())
        brightness = float(gray.mean())
        contrast = float(gray.std())
        if width * height < self.min_face_pixels:
            return FaceQuality.LOW_QUALITY, "Face region is too small."
        if sharpness < 20:
            return FaceQuality.LOW_QUALITY, "Face region is too blurry."
        if brightness < 35 or brightness > 225 or contrast < 18:
            return FaceQuality.LOW_QUALITY, "Face exposure or contrast is insufficient."
        return FaceQuality.READY, "Face size, sharpness, brightness, and contrast passed the quality gate."

    def _embedding(self, image: Any, face: tuple[int, int, int, int]) -> Any:
        x, y, width, height = face
        crop = image[y:y + height, x:x + width]
        aligned = self._cv2.resize(crop, (112, 112), interpolation=self._cv2.INTER_AREA)
        embedding = self._recognizer.feature(aligned)
        np: Any = __import__("numpy")
        vector = np.asarray(embedding, dtype=np.float32).reshape(-1)
        norm = float(np.linalg.norm(vector))
        if norm == 0:
            raise RuntimeError("The face model returned an invalid embedding.")
        return vector / norm

    def _analyze(self, content: bytes) -> tuple[Any, FaceQuality, str, int]:
        image = self._decode(content)
        faces = self._faces(image)
        if not faces:
            return image, FaceQuality.NO_FACE, "No face was detected.", 0
        if len(faces) != 1:
            return image, FaceQuality.MULTIPLE_FACES, "Exactly one face is required; no face was selected.", len(faces)
        quality, explanation = self._quality(image, faces[0])
        return image, quality, explanation, 1

    def compare(self, document_face: bytes, presented_face: bytes, scenario: FaceScenario = FaceScenario.MATCH) -> tuple[FaceOutcome, float | None, float | None, str, str | None, FaceQuality, int | None]:
        del scenario
        document_image, document_quality, document_reason, _document_count = self._analyze(document_face)
        if document_quality != FaceQuality.READY:
            raise ValueError(f"Reference face unavailable: {document_reason}")
        presented_image, presented_quality, presented_reason, presented_count = self._analyze(presented_face)
        if presented_quality != FaceQuality.READY:
            outcome = FaceOutcome.REVIEW if presented_quality == FaceQuality.MULTIPLE_FACES else FaceOutcome.UNAVAILABLE
            return outcome, None, None, "Face verification could not produce a reliable comparison.", presented_reason, presented_quality, presented_count
        faces = self._faces(document_image)
        presented_faces = self._faces(presented_image)
        reference_embedding = self._embedding(document_image, faces[0])
        presented_embedding = self._embedding(presented_image, presented_faces[0])
        similarity = float(reference_embedding @ presented_embedding)
        if similarity >= self.threshold:
            outcome, summary = FaceOutcome.MATCH, "Biometric similarity meets the configured verification threshold; officer review remains required."
        elif similarity >= self.review_threshold:
            outcome, summary = FaceOutcome.REVIEW, "Biometric similarity is within the review band; officer assessment is required."
        else:
            outcome, summary = FaceOutcome.MISMATCH, "Biometric similarity is below the configured verification threshold."
        return outcome, similarity, similarity, summary, None, presented_quality, presented_count


def new_face_result_id() -> UUID:
    return uuid4()

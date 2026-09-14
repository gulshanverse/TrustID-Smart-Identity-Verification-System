from typing import Protocol

from app.domain.contracts import FaceResult


class OCRService(Protocol):
    def extract(self, document_id: str) -> dict[str, object]: ...


class DocumentValidationService(Protocol):
    def validate(self, fields: dict[str, object]) -> dict[str, object]: ...


class TamperingDetectionService(Protocol):
    def analyze(self, document_id: str) -> dict[str, object]: ...


class FaceVerificationService(Protocol):
    def verify(self, document_id: str, live_face_id: str | None) -> FaceResult: ...


class RiskAssessmentService(Protocol):
    def assess(self, signals: dict[str, object]) -> dict[str, object]: ...

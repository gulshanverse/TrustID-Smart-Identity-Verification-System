from uuid import UUID

from pydantic import BaseModel

from app.domain.face import FaceOutcome, FaceQuality, FaceVerificationStatus


class FaceEvidenceResponse(BaseModel):
    name: str
    value: str
    explanation: str


class FaceVerificationResponse(BaseModel):
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
    evidence: list[FaceEvidenceResponse]
    created_at: str
    updated_at: str

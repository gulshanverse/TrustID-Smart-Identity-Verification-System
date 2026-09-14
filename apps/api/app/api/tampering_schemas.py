from uuid import UUID

from pydantic import BaseModel

from app.domain.tampering import FindingSeverity, FindingType, TamperingScenario, TamperingStatus


class TamperingRequest(BaseModel):
    scenario: TamperingScenario = TamperingScenario.CLEAN


class TamperingEvidenceResponse(BaseModel):
    evidence_type: str
    page: int | None
    region: str | None
    description: str
    source_reference: str | None
    technical_signal: str
    confidence: float


class TamperingFindingResponse(BaseModel):
    id: UUID
    finding_type: FindingType
    severity: FindingSeverity
    confidence: float
    title: str
    description: str
    related_ocr_field: str | None
    evidence: list[TamperingEvidenceResponse]


class TamperingResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: TamperingStatus
    technical_signal_score: float
    overall_confidence: float
    provider: str
    provider_version: str
    summary: str
    findings: list[TamperingFindingResponse]
    created_at: str
    updated_at: str

from uuid import UUID

from pydantic import BaseModel


class DecisionEvidenceResponse(BaseModel):
    evidence_id: UUID
    category: str
    source: str
    status: str
    severity: str
    explanation: str
    provider: str
    version: str
    rule_id: str | None = None


class ContradictionResponse(BaseModel):
    code: str
    severity: str
    evidence_ids: list[UUID]
    explanation: str
    provenance: str


class ReviewPriorityResponse(BaseModel):
    priority: str
    code: str
    explanation: str
    evidence_ids: list[UUID]


class MissingInformationResponse(BaseModel):
    code: str
    status: str
    explanation: str


class RiskContextResponse(BaseModel):
    score: int
    band: str
    assessment_version: str
    factors: list[dict[str, object]]


class DecisionIntelligenceResponse(BaseModel):
    verification_id: UUID
    status: str
    version: str
    generated_at: str
    analysis_fingerprint: str
    evidence_summary: list[DecisionEvidenceResponse]
    contradictions: list[ContradictionResponse]
    review_priorities: list[ReviewPriorityResponse]
    missing_information: list[MissingInformationResponse]
    risk_context: RiskContextResponse
    provenance: list[str]

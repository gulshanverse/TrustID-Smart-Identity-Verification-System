from uuid import UUID

from pydantic import BaseModel

from app.domain.risk import RiskLevel, RiskSeverity
from app.domain.validation import ValidationSeverity, ValidationStatus


class ModuleStatusResponse(BaseModel):
    name: str
    status: str
    summary: str


class ValidationFindingResponse(BaseModel):
    name: str
    severity: ValidationSeverity
    passed: bool
    explanation: str
    reference: str | None
    rule_id: str | None = None
    rule_version: str | None = None
    field: str | None = None
    observed: str | None = None
    expected: str | None = None


class ValidationResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: ValidationStatus
    provider: str
    provider_version: str | None = None
    summary: str
    findings: list[ValidationFindingResponse]


class RiskFactorResponse(BaseModel):
    name: str
    source_module: str
    severity: RiskSeverity
    contribution: int
    explanation: str
    evidence_reference: str | None


class RiskResponse(BaseModel):
    id: UUID
    verification_id: UUID
    status: str
    risk_score: int
    risk_level: RiskLevel
    recommendation: str
    confidence: float | None
    summary: str
    assessment_version: str
    factors: list[RiskFactorResponse]


class EvidenceProvenanceResponse(BaseModel):
    module: str
    provider: str
    version: str
    rule: str | None


class EvidenceResponse(BaseModel):
    evidence_id: UUID
    source_module: str
    evidence_type: str
    status: str
    severity: str
    confidence: float | None
    score: float | None
    explanation: str
    reason_code: str
    provenance: EvidenceProvenanceResponse
    created_at: str


class VerificationFindingResponse(BaseModel):
    finding_id: UUID
    code: str
    status: str
    severity: str
    title: str
    explanation: str
    evidence_ids: list[UUID]
    provenance: EvidenceProvenanceResponse
    risk_contribution: int
    created_at: str


class VerificationAnalysisResponse(BaseModel):
    verification_id: UUID
    document_id: UUID
    status: str
    modules: list[ModuleStatusResponse]
    validation: ValidationResponse
    risk: RiskResponse
    correlation_summary: str
    evidence: list[EvidenceResponse]
    findings: list[VerificationFindingResponse]

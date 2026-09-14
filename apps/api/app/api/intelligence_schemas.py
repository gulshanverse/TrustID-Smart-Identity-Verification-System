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


class ValidationResponse(BaseModel):
    id: UUID
    document_id: UUID
    status: ValidationStatus
    provider: str
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


class VerificationAnalysisResponse(BaseModel):
    verification_id: UUID
    document_id: UUID
    status: str
    modules: list[ModuleStatusResponse]
    validation: ValidationResponse
    risk: RiskResponse

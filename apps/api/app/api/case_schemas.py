from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.cases import CasePriority, CaseStatus, OfficerDecision


class CaseCreateRequest(BaseModel):
    verification_id: UUID
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(default="Investigation case created from a verification result.", max_length=4000)
    priority: CasePriority = CasePriority.MEDIUM


class CaseUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=3, max_length=180)
    description: str | None = Field(default=None, max_length=4000)
    priority: CasePriority | None = None


class AssignmentRequest(BaseModel):
    assigned_to: UUID | None = None
    assigned_supervisor: UUID | None = None


class StatusRequest(BaseModel):
    status: CaseStatus


class DecisionRequest(BaseModel):
    decision: OfficerDecision
    reason: str = Field(default="", max_length=4000)


class EvidenceCreateRequest(BaseModel):
    evidence_type: str = Field(min_length=2, max_length=64)
    source_type: str = Field(min_length=2, max_length=64)
    source_id: UUID
    title: str = Field(min_length=2, max_length=180)
    summary: str = Field(min_length=2, max_length=2000)
    severity: str = Field(default="INFO", max_length=16)


class NoteCreateRequest(BaseModel):
    body: str = Field(min_length=2, max_length=8000)


class CaseResponse(BaseModel):
    id: UUID
    case_number: str
    verification_id: UUID
    title: str
    description: str
    status: CaseStatus
    priority: CasePriority
    assigned_to: UUID | None
    assigned_supervisor: UUID | None
    created_by: UUID
    resolved_by: UUID | None
    resolution: str | None
    resolution_reason: str | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None


class EvidenceResponse(BaseModel):
    id: UUID
    evidence_type: str
    source_type: str
    source_id: UUID
    title: str
    summary: str
    severity: str
    created_by: UUID
    created_at: datetime


class NoteResponse(BaseModel):
    id: UUID
    author_id: UUID
    body: str
    created_at: datetime
    updated_at: datetime


class TimelineResponse(BaseModel):
    id: UUID
    event_type: str
    actor_id: UUID
    status: str
    created_at: datetime


class CaseDetailResponse(BaseModel):
    case: CaseResponse
    evidence: list[EvidenceResponse]
    notes: list[NoteResponse]
    timeline: list[TimelineResponse]

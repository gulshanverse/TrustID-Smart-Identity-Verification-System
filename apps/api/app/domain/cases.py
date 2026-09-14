from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID, uuid4


class CaseStatus(StrEnum):
    OPEN = "OPEN"
    UNDER_REVIEW = "UNDER_REVIEW"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class CasePriority(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class OfficerDecision(StrEnum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    REJECT = "REJECT"


_ALLOWED_TRANSITIONS: dict[CaseStatus, frozenset[CaseStatus]] = {
    CaseStatus.OPEN: frozenset({CaseStatus.UNDER_REVIEW, CaseStatus.ESCALATED, CaseStatus.RESOLVED}),
    CaseStatus.UNDER_REVIEW: frozenset({CaseStatus.ESCALATED, CaseStatus.RESOLVED}),
    CaseStatus.ESCALATED: frozenset({CaseStatus.UNDER_REVIEW, CaseStatus.RESOLVED}),
    CaseStatus.RESOLVED: frozenset({CaseStatus.CLOSED}),
    CaseStatus.CLOSED: frozenset(),
}


def validate_transition(current: CaseStatus, target: CaseStatus) -> None:
    if target != current and target not in _ALLOWED_TRANSITIONS[current]:
        raise ValueError(f"Cannot move a {current.value} case to {target.value}.")


def require_decision_reason(decision: OfficerDecision, reason: str | None) -> str:
    cleaned = (reason or "").strip()
    if decision == OfficerDecision.REJECT and len(cleaned) < 3:
        raise ValueError("A reason is required when recording a rejected decision.")
    return cleaned


@dataclass(frozen=True)
class CaseRecord:
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
    created_at: str
    updated_at: str
    resolved_at: str | None
    closed_at: str | None


def new_case_id() -> UUID:
    return uuid4()

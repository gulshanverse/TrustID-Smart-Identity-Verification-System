from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.db.models import AuditEventModel, Base, CaseDecisionModel, CaseModel, CaseNoteModel
from app.domain.cases import (
    CasePriority,
    CaseStatus,
    OfficerDecision,
    require_decision_reason,
    validate_transition,
)
from app.domain.documents import InMemoryObjectStorage
from app.repositories.case_repository import SqlAlchemyCaseRepository
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.services.document_service import DocumentService


def test_lifecycle_rules_and_rejected_reason() -> None:
    validate_transition(CaseStatus.OPEN, CaseStatus.UNDER_REVIEW)
    with pytest.raises(ValueError): validate_transition(CaseStatus.CLOSED, CaseStatus.OPEN)
    with pytest.raises(ValueError): require_decision_reason(OfficerDecision.REJECT, "")
    assert require_decision_reason(OfficerDecision.REJECT, "Document inconsistency requires review")


@pytest.fixture
def db() -> Session:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    Base.metadata.drop_all(engine)


def create_case(db: Session):
    actor = uuid4()
    documents = DocumentService(InMemoryObjectStorage(), SqlAlchemyDocumentRepository(db))
    verification = documents.create_verification(actor, f"case-{actor}@example.test", "Officer")
    repo = SqlAlchemyCaseRepository(db)
    case = repo.create_case(verification.id, actor, "Routine verification review", "Demo case for officer workflow.", CasePriority.MEDIUM)
    model = repo.get(case.id, actor)
    assert model is not None
    return repo, actor, verification, case, model


def test_case_creation_links_verification_and_persists_audit(db: Session) -> None:
    _repo, _actor, verification, case, _model = create_case(db)
    assert case.verification_id == verification.id
    assert case.case_number.startswith("TRUST-")
    assert db.scalar(select(CaseModel).where(CaseModel.id == case.id)) is not None
    assert db.scalar(select(AuditEventModel).where(AuditEventModel.case_id == case.id, AuditEventModel.event_type == "CASE_CREATED")) is not None


def test_case_status_assignment_notes_decision_and_close_rules(db: Session) -> None:
    repo, actor, _, case, model = create_case(db)
    assigned = uuid4()
    repo.assign(model, actor, assigned, None)
    repo.change_status(model, actor, CaseStatus.UNDER_REVIEW)
    note_id = repo.add_note(model, actor, "Reviewed structured evidence and risk context.")
    assert db.get(CaseNoteModel, note_id) is not None
    decision = repo.decision(model, actor, OfficerDecision.REVIEW, "Additional officer review is required.")
    assert decision.decision == "REVIEW"
    repo.change_status(model, actor, CaseStatus.RESOLVED)
    repo.change_status(model, actor, CaseStatus.CLOSED)
    with pytest.raises(ValueError): repo.add_note(model, actor, "Cannot change closed case")
    events = db.scalars(select(AuditEventModel).where(AuditEventModel.case_id == case.id)).all()
    assert {event.event_type for event in events} >= {"CASE_CREATED", "CASE_ASSIGNED", "CASE_STATUS_CHANGED", "CASE_NOTE_ADDED", "CASE_DECISION_RECORDED", "CASE_RESOLVED", "CASE_CLOSED"}


@pytest.mark.parametrize(
    ("decision", "expected_status", "reason"),
    [(OfficerDecision.APPROVE, CaseStatus.RESOLVED, "Officer approved the completed verification."), (OfficerDecision.REVIEW, CaseStatus.UNDER_REVIEW, "Additional manual review is required."), (OfficerDecision.REJECT, CaseStatus.RESOLVED, "Verification evidence is inconsistent.")],
)
def test_each_officer_decision_has_distinct_persisted_semantics_and_audit(db: Session, decision: OfficerDecision, expected_status: CaseStatus, reason: str) -> None:
    repo, actor, _verification, case, model = create_case(db)
    item = repo.decision(model, actor, decision, reason)
    persisted = db.get(CaseModel, case.id)
    assert persisted is not None
    assert item.decision == decision.value
    assert persisted.status == expected_status.value
    assert persisted.resolution == decision.value
    assert persisted.resolution_reason == reason
    assert persisted.resolved_by == actor if decision != OfficerDecision.REVIEW else persisted.resolved_by is None
    assert db.scalar(select(CaseDecisionModel).where(CaseDecisionModel.id == item.id)) is not None
    audit = db.scalar(select(AuditEventModel).where(AuditEventModel.case_id == case.id, AuditEventModel.event_type == "CASE_DECISION_RECORDED"))
    assert audit is not None
    assert audit.actor_id == actor
    assert audit.status == decision.value


def test_duplicate_officer_decision_is_rejected_without_duplicate_audit(db: Session) -> None:
    repo, actor, _verification, case, model = create_case(db)
    repo.decision(model, actor, OfficerDecision.APPROVE, "Approved after officer review.")
    with pytest.raises(ValueError, match="already been recorded"):
        repo.decision(model, actor, OfficerDecision.REJECT, "A later rejection is not allowed.")
    assert len(db.scalars(select(CaseDecisionModel).where(CaseDecisionModel.case_id == case.id)).all()) == 1
    assert len(db.scalars(select(AuditEventModel).where(AuditEventModel.case_id == case.id, AuditEventModel.event_type == "CASE_DECISION_RECORDED")).all()) == 1


def test_case_owner_and_assignment_visibility_are_scoped(db: Session) -> None:
    repo, actor, _, case, _ = create_case(db)
    outsider = uuid4()
    assert repo.get(case.id, outsider) is None
    assert repo.list_cases(outsider) == []
    assert repo.get(case.id, actor) is not None


def test_evidence_requires_existing_reference(db: Session) -> None:
    repo, actor, _, _case, model = create_case(db)
    with pytest.raises(ValueError): repo.add_evidence(model, actor, "RISK_FACTOR", "risk_factor", uuid4(), "Missing source", "Reference does not exist.", "REVIEW")


def test_officer_decision_snapshot_is_immutable_after_analysis_regeneration(db: Session) -> None:
    repo, actor, _verification, _case, model = create_case(db)
    snapshot = {
        "decision_intelligence_version": "phase6-decision-intelligence-v1",
        "analysis_fingerprint": "fingerprint-at-decision-time",
        "risk": {"score": 42, "band": "REVIEW", "assessment_version": "risk-v1", "factors": []},
        "evidence_ids": [str(uuid4())],
        "correlation": [],
        "review_priorities": [{"code": "FACE_NO_MATCH", "priority": "HIGH", "evidence_ids": []}],
        "missing_information": [{"code": "LIVENESS_NOT_IMPLEMENTED", "status": "NOT_AVAILABLE"}],
        "provenance": ["Phase 3 evidence correlation"],
    }
    decision = repo.decision(model, actor, OfficerDecision.REVIEW, "The stored analysis requires additional review.", snapshot)
    persisted = db.get(CaseDecisionModel, decision.id)
    assert persisted is not None
    original = dict(persisted.decision_context or {})
    persisted.decision_context = {**original, "analysis_fingerprint": "regenerated-current-analysis"}
    db.flush()
    db.rollback()
    reloaded = db.get(CaseDecisionModel, decision.id)
    assert reloaded is not None
    assert reloaded.decision_context == original

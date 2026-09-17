from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.api.case_schemas import (
    AssignmentRequest,
    CaseCreateRequest,
    CaseDetailResponse,
    CaseResponse,
    CaseUpdateRequest,
    DecisionRequest,
    EvidenceCreateRequest,
    EvidenceResponse,
    NoteCreateRequest,
    NoteResponse,
    StatusRequest,
    TimelineResponse,
)
from app.api.dependencies import get_current_user
from app.api.v1.decision_intelligence import _build as build_decision_intelligence
from app.db.models import CaseModel
from app.db.session import get_db
from app.domain.auth import Permission, Role, permissions_for_roles
from app.domain.cases import CaseRecord, require_decision_reason
from app.domain.decision_intelligence import decision_snapshot
from app.domain.documents import safe_exception_message
from app.repositories.case_repository import SqlAlchemyCaseRepository
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/cases", tags=["cases"])
logger = logging.getLogger("trustid.cases.api")


def can(user: AuthUser, permission: Permission) -> bool:
    return permission in permissions_for_roles(user.roles)


def ensure(user: AuthUser, permission: Permission) -> None:
    if not can(user, permission): raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have permission to perform this case operation.")


def broad(user: AuthUser) -> bool:
    return bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)


def response(model: CaseRecord | CaseModel) -> CaseResponse:
    return CaseResponse.model_validate({field: getattr(model, field) for field in CaseResponse.model_fields})


def get_case(case_id: UUID, user: AuthUser, db: Session) -> CaseModel:
    model = SqlAlchemyCaseRepository(db).get(case_id, user.id, broad(user))
    if model is None: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Case not found.")
    return model


@router.post("", response_model=CaseResponse, status_code=status.HTTP_201_CREATED)
def create_case(payload: CaseCreateRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseResponse:
    ensure(user, Permission.CASE_WORK)
    try: return response(SqlAlchemyCaseRepository(db).create_case(payload.verification_id, user.id, payload.title, payload.description, payload.priority))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("", response_model=list[CaseResponse])
def list_cases(search: str | None = None, status_filter: str | None = Query(default=None, alias="status"), priority: str | None = None, risk_level: str | None = None, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[CaseResponse]:
    if not can(user, Permission.CASE_WORK) and not can(user, Permission.AUDIT): ensure(user, Permission.CASE_WORK)
    return [response(item) for item in SqlAlchemyCaseRepository(db).list_cases(user.id, status_filter, priority, risk_level, search, limit, offset, broad(user))]


@router.get("/{case_id}", response_model=CaseDetailResponse)
def get_case_detail(case_id: UUID, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseDetailResponse:
    if not can(user, Permission.CASE_WORK) and not can(user, Permission.AUDIT): ensure(user, Permission.CASE_WORK)
    repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    return CaseDetailResponse(case=response(model), evidence=[EvidenceResponse.model_validate(item, from_attributes=True) for item in repo.get_evidence(case_id)], notes=[NoteResponse.model_validate(item, from_attributes=True) for item in repo.get_notes(case_id)], timeline=[TimelineResponse.model_validate(item, from_attributes=True) for item in repo.get_timeline(case_id)])


@router.patch("/{case_id}", response_model=CaseResponse)
def update_case(case_id: UUID, payload: CaseUpdateRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseResponse:
    ensure(user, Permission.CASE_WORK); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try: return response(repo.update_case(model, user.id, payload.title, payload.description, payload.priority))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{case_id}/assign", response_model=CaseResponse)
def assign_case(case_id: UUID, payload: AssignmentRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseResponse:
    ensure(user, Permission.CASE_ASSIGN); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try: return response(repo.assign(model, user.id, payload.assigned_to, payload.assigned_supervisor))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{case_id}/status", response_model=CaseResponse)
def change_status(case_id: UUID, payload: StatusRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> CaseResponse:
    ensure(user, Permission.CASE_WORK if payload.status.value not in {"RESOLVED", "CLOSED"} else Permission.CASE_RESOLVE); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try: return response(repo.change_status(model, user.id, payload.status))
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.post("/{case_id}/decision", response_model=dict[str, object])
def record_decision(case_id: UUID, payload: DecisionRequest, request: Request, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, object]:
    ensure(user, Permission.CASE_DECIDE); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try:
        reason = require_decision_reason(payload.decision, payload.reason)
        context = decision_snapshot(build_decision_intelligence(model.verification_id, user, db))
        item = repo.decision(model, user.id, payload.decision, reason, context)
        return {"id": item.id, "decision": item.decision, "created_at": item.created_at, "case_status": model.status, "reason": item.reason}
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc
    except Exception as exc:
        db.rollback()
        logger.warning(
            "case_decision_failed operation=record_decision case_id=%s request_id=%s decision=%s error_type=%s error_message=%s",
            case_id,
            getattr(request.state, "request_id", "unavailable"),
            payload.decision.value,
            type(exc).__name__,
            safe_exception_message(exc),
        )
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="The officer decision could not be recorded.") from exc


@router.get("/{case_id}/evidence", response_model=list[EvidenceResponse])
def evidence(case_id: UUID, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[EvidenceResponse]:
    ensure(user, Permission.CASE_WORK); get_case(case_id, user, db); return [EvidenceResponse.model_validate(item, from_attributes=True) for item in SqlAlchemyCaseRepository(db).get_evidence(case_id)]


@router.post("/{case_id}/evidence", response_model=EvidenceResponse, status_code=status.HTTP_201_CREATED)
def add_evidence(case_id: UUID, payload: EvidenceCreateRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> EvidenceResponse:
    ensure(user, Permission.CASE_WORK); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try: return EvidenceResponse.model_validate(repo.add_evidence(model, user.id, payload.evidence_type, payload.source_type, payload.source_id, payload.title, payload.summary, payload.severity), from_attributes=True)
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("/{case_id}/notes", response_model=list[NoteResponse])
def notes(case_id: UUID, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[NoteResponse]:
    ensure(user, Permission.CASE_WORK); get_case(case_id, user, db); return [NoteResponse.model_validate(item, from_attributes=True) for item in SqlAlchemyCaseRepository(db).get_notes(case_id)]


@router.post("/{case_id}/notes", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
def add_note(case_id: UUID, payload: NoteCreateRequest, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> NoteResponse:
    ensure(user, Permission.CASE_WORK); repo = SqlAlchemyCaseRepository(db); model = get_case(case_id, user, db)
    try:
        note_id = repo.add_note(model, user.id, payload.body); item = db.get(__import__("app.db.models", fromlist=["CaseNoteModel"]).CaseNoteModel, note_id); return NoteResponse.model_validate(item, from_attributes=True)
    except ValueError as exc: raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from exc


@router.get("/{case_id}/timeline", response_model=list[TimelineResponse])
def timeline(case_id: UUID, user: AuthUser = Depends(get_current_user), db: Session = Depends(get_db)) -> list[TimelineResponse]:
    ensure(user, Permission.CASE_WORK); get_case(case_id, user, db); return [TimelineResponse.model_validate(item, from_attributes=True) for item in SqlAlchemyCaseRepository(db).get_timeline(case_id)]

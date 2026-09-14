from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.models import AuditEventModel
from app.db.session import get_db
from app.domain.auth import Permission
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/audit", tags=["audit"])


def _event(model: AuditEventModel) -> dict[str, object]:
    return {"id": model.id, "event_type": model.event_type, "actor_id": model.actor_id, "verification_id": model.verification_id, "case_id": model.case_id, "document_id": model.document_id, "provider": model.provider, "status": model.status, "created_at": model.created_at}


@router.get("/events")
def events(event_type: str | None = None, actor_id: UUID | None = None, verification_id: UUID | None = None, case_id: UUID | None = None, document_id: UUID | None = None, status: str | None = None, start: datetime | None = None, end: datetime | None = None, limit: int = Query(default=50, ge=1, le=100), offset: int = Query(default=0, ge=0), user: AuthUser = Depends(require_permission(Permission.AUDIT)), db: Session = Depends(get_db)) -> dict[str, object]:
    query = select(AuditEventModel)
    if event_type: query = query.where(AuditEventModel.event_type == event_type)
    if actor_id: query = query.where(AuditEventModel.actor_id == actor_id)
    if verification_id: query = query.where(AuditEventModel.verification_id == verification_id)
    if case_id: query = query.where(AuditEventModel.case_id == case_id)
    if document_id: query = query.where(AuditEventModel.document_id == document_id)
    if status: query = query.where(AuditEventModel.status == status)
    if start: query = query.where(AuditEventModel.created_at >= start.astimezone(UTC))
    if end: query = query.where(AuditEventModel.created_at < end.astimezone(UTC))
    total = db.scalar(select(__import__("sqlalchemy", fromlist=["func"]).func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(AuditEventModel.created_at.desc()).limit(limit).offset(offset)).all()
    return {"items": [_event(item) for item in rows], "total": total, "limit": limit, "offset": offset, "redaction": "Sensitive payloads are not stored or displayed."}


@router.get("/events/{event_id}")
def event_detail(event_id: UUID, user: AuthUser = Depends(require_permission(Permission.AUDIT)), db: Session = Depends(get_db)) -> dict[str, object]:
    model = db.get(AuditEventModel, event_id)
    if model is None: raise HTTPException(status_code=404, detail="Audit event not found.")
    return _event(model) | {"metadata": {"provider": model.provider, "status": model.status}, "redacted_fields": ["raw_text", "biometric_image", "embedding", "password", "secret"]}

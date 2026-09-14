from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.domain.auth import Permission, Role
from app.services.analytics_service import AnalyticsFilters, AnalyticsService
from app.services.auth_service import AuthUser

router = APIRouter(prefix="/analytics", tags=["analytics"])


def filters(days: int, start: datetime | None, end: datetime | None, risk_level: str | None, case_status: str | None, case_priority: str | None, document_type: str | None) -> AnalyticsFilters:
    if days not in {7, 30, 90}: days = 30
    if end is None: end = datetime.now(UTC)
    end = end.astimezone(UTC); start = start.astimezone(UTC) if start else end - timedelta(days=days)
    return AnalyticsFilters(start, end, risk_level, case_status, case_priority, document_type)


def get_filters(days: int = Query(default=30, ge=1, le=90), start: datetime | None = None, end: datetime | None = None, risk_level: str | None = None, case_status: str | None = None, case_priority: str | None = None, document_type: str | None = None) -> AnalyticsFilters:
    return filters(days, start, end, risk_level, case_status, case_priority, document_type)


@router.get("/overview")
def overview(query: AnalyticsFilters = Depends(get_filters), user: AuthUser = Depends(require_permission(Permission.ANALYTICS)), db: Session = Depends(get_db)) -> dict[str, object]:
    return AnalyticsService(db, user.id, bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)).overview(query)


@router.get("/verifications")
def verifications(query: AnalyticsFilters = Depends(get_filters), user: AuthUser = Depends(require_permission(Permission.ANALYTICS)), db: Session = Depends(get_db)) -> dict[str, object]:
    result = AnalyticsService(db, user.id, bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)).overview(query); return {"period": result["period"], "verification": result["verification"]}


@router.get("/risk")
def risk(query: AnalyticsFilters = Depends(get_filters), user: AuthUser = Depends(require_permission(Permission.ANALYTICS)), db: Session = Depends(get_db)) -> dict[str, object]:
    result = AnalyticsService(db, user.id, bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)).overview(query); return {"period": result["period"], "risk": result["risk"]}


@router.get("/cases")
def cases(query: AnalyticsFilters = Depends(get_filters), user: AuthUser = Depends(require_permission(Permission.ANALYTICS)), db: Session = Depends(get_db)) -> dict[str, object]:
    result = AnalyticsService(db, user.id, bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)).overview(query); return {"period": result["period"], "cases": result["cases"]}


@router.get("/trends")
def trends(query: AnalyticsFilters = Depends(get_filters), user: AuthUser = Depends(require_permission(Permission.ANALYTICS)), db: Session = Depends(get_db)) -> dict[str, object]:
    service = AnalyticsService(db, user.id, bool({Role.ADMIN, Role.SUPERVISOR, Role.AUDITOR} & user.roles)); return {"period": {"start": query.start.isoformat(), "end": query.end.isoformat(), "timezone": "UTC"}, "verifications_per_day": service.trends(query)}

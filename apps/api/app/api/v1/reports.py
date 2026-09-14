from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.db.session import get_db
from app.domain.auth import Permission
from app.services.auth_service import AuthUser
from app.services.report_service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


def pdf_response(content: bytes, report_id: UUID, report_type: str) -> StreamingResponse:
    return StreamingResponse(iter([content]), media_type="application/pdf", headers={"Content-Disposition": f'attachment; filename="trustid-{report_type.lower()}-report-{report_id}.pdf"'})


@router.post("/verification/{verification_id}")
def verification_report(verification_id: UUID, user: AuthUser = Depends(require_permission(Permission.REPORTS)), db: Session = Depends(get_db)) -> StreamingResponse:
    try: content, report_id = ReportService(db).verification_report(verification_id, user.id)
    except LookupError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return pdf_response(content, report_id, "verification")


@router.post("/case/{case_id}")
def case_report(case_id: UUID, user: AuthUser = Depends(require_permission(Permission.REPORTS)), db: Session = Depends(get_db)) -> StreamingResponse:
    try: content, report_id = ReportService(db).case_report(case_id, user.id)
    except LookupError as exc: raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    return pdf_response(content, report_id, "case")


@router.get("/recent")
def recent_reports(limit: int = Query(default=50, ge=1, le=100), user: AuthUser = Depends(require_permission(Permission.REPORTS)), db: Session = Depends(get_db)) -> list[dict[str, object]]:
    return [{"id": item.id, "report_type": item.report_type, "reference_type": item.reference_type, "reference_id": item.reference_id, "generated_by": item.generated_by, "report_version": item.report_version, "created_at": item.created_at} for item in ReportService(db).recent(user.id, limit)]

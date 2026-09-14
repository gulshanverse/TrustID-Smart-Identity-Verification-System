from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from app.db.models import (
    CaseModel,
    DocumentModel,
    DocumentValidationModel,
    FaceVerificationModel,
    OCRResultModel,
    RiskAssessmentModel,
    TamperingFindingModel,
    TamperingResultModel,
    VerificationModel,
)


@dataclass(frozen=True)
class AnalyticsFilters:
    start: datetime
    end: datetime
    risk_level: str | None = None
    case_status: str | None = None
    case_priority: str | None = None
    document_type: str | None = None


class AnalyticsService:
    """Derives operational metrics from authoritative persisted rows; all dates are UTC."""

    def __init__(self, db: Session, actor_id: UUID | None = None, global_access: bool = False) -> None:
        self.db = db
        self.actor_id = actor_id
        self.global_access = global_access

    def _scope(self, query: Any) -> Any:
        if self.actor_id is not None and not self.global_access:
            query = query.where(VerificationModel.owner_id == self.actor_id)
        return query

    def _verification_filter(self, query: Any, filters: AnalyticsFilters) -> Any:
        query = self._scope(query.where(VerificationModel.created_at >= filters.start, VerificationModel.created_at < filters.end))
        if filters.document_type:
            query = query.join(DocumentModel, DocumentModel.verification_id == VerificationModel.id).where(DocumentModel.document_type == filters.document_type)
        return query

    def overview(self, filters: AnalyticsFilters) -> dict[str, object]:
        total_query = self._verification_filter(select(func.count(distinct(VerificationModel.id))).select_from(VerificationModel), filters)
        total = self.db.scalar(total_query) or 0
        risk_subquery = select(RiskAssessmentModel.verification_id, func.max(RiskAssessmentModel.created_at).label("latest")).group_by(RiskAssessmentModel.verification_id).subquery()
        latest_risk = select(RiskAssessmentModel).join(risk_subquery, (RiskAssessmentModel.verification_id == risk_subquery.c.verification_id) & (RiskAssessmentModel.created_at == risk_subquery.c.latest)).subquery()
        risk_query = self._scope(select(latest_risk.c.risk_level, func.count()).select_from(latest_risk).join(VerificationModel, VerificationModel.id == latest_risk.c.verification_id).where(VerificationModel.created_at >= filters.start, VerificationModel.created_at < filters.end)).group_by(latest_risk.c.risk_level)
        risk_counts = {row[0]: row[1] for row in self.db.execute(risk_query)}
        if filters.risk_level: risk_counts = {filters.risk_level: risk_counts.get(filters.risk_level, 0)}
        case_query = self._scope(select(CaseModel.status, func.count()).join(VerificationModel, VerificationModel.id == CaseModel.verification_id).where(CaseModel.created_at >= filters.start, CaseModel.created_at < filters.end)).group_by(CaseModel.status)
        if filters.case_status: case_query = case_query.where(CaseModel.status == filters.case_status)
        if filters.case_priority: case_query = case_query.where(CaseModel.priority == filters.case_priority)
        case_counts = {row[0]: row[1] for row in self.db.execute(case_query)}
        avg_score = self.db.scalar(self._scope(select(func.avg(latest_risk.c.risk_score)).select_from(latest_risk).join(VerificationModel, VerificationModel.id == latest_risk.c.verification_id).where(VerificationModel.created_at >= filters.start, VerificationModel.created_at < filters.end)))
        completed = sum(risk_counts.values())
        return {"timezone": "UTC", "period": {"start": filters.start.isoformat(), "end": filters.end.isoformat()}, "verification": {"total": total, "completed": completed, "failed": 0, "pending": max(0, total - completed), "completion_rate": round(completed / total, 4) if total else None}, "risk": {"low": risk_counts.get("LOW", 0), "review": risk_counts.get("REVIEW", 0), "high": risk_counts.get("HIGH", 0), "average_score": round(float(avg_score), 2) if avg_score is not None else None, "distribution": risk_counts}, "cases": {"total": sum(case_counts.values()), "by_status": case_counts, "by_priority": self._case_priorities(filters), "high_risk": self._high_risk_cases(filters)}, "modules": self._modules(filters), "demo": False}

    def _case_priorities(self, filters: AnalyticsFilters) -> dict[str, int]:
        query = self._scope(select(CaseModel.priority, func.count()).join(VerificationModel, VerificationModel.id == CaseModel.verification_id).where(CaseModel.created_at >= filters.start, CaseModel.created_at < filters.end)).group_by(CaseModel.priority)
        return {row[0]: row[1] for row in self.db.execute(query)}

    def _high_risk_cases(self, filters: AnalyticsFilters) -> int:
        query = self._scope(select(func.count(distinct(CaseModel.id))).join(VerificationModel, VerificationModel.id == CaseModel.verification_id).join(RiskAssessmentModel, RiskAssessmentModel.verification_id == VerificationModel.id).where(CaseModel.created_at >= filters.start, CaseModel.created_at < filters.end, RiskAssessmentModel.risk_level == "HIGH"))
        return int(self.db.scalar(query) or 0)

    def _modules(self, filters: AnalyticsFilters) -> dict[str, object]:
        base_doc = self._scope(select(DocumentModel.id).join(VerificationModel).where(VerificationModel.created_at >= filters.start, VerificationModel.created_at < filters.end))
        ocr = self.db.execute(select(OCRResultModel.status, func.count(), func.avg(OCRResultModel.overall_confidence)).where(OCRResultModel.document_id.in_(base_doc)).group_by(OCRResultModel.status)).all()
        validation = self.db.execute(select(DocumentValidationModel.status, func.count()).where(DocumentValidationModel.document_id.in_(base_doc)).group_by(DocumentValidationModel.status)).all()
        tampering = self.db.execute(select(TamperingResultModel.status, func.count()).where(TamperingResultModel.document_id.in_(base_doc)).group_by(TamperingResultModel.status)).all()
        findings = self.db.execute(select(TamperingFindingModel.severity, func.count()).join(TamperingResultModel).where(TamperingResultModel.document_id.in_(base_doc)).group_by(TamperingFindingModel.severity)).all()
        faces = self.db.execute(select(FaceVerificationModel.outcome, func.count()).where(FaceVerificationModel.document_id.in_(base_doc)).group_by(FaceVerificationModel.outcome)).all()
        return {"ocr": {"by_status": {row[0]: row[1] for row in ocr}, "average_confidence": round(float(sum((row[2] or 0) for row in ocr) / len(ocr)), 4) if ocr else None}, "validation": {"by_status": {row[0]: row[1] for row in validation}}, "tampering": {"by_status": {row[0]: row[1] for row in tampering}, "finding_severity": {row[0]: row[1] for row in findings}}, "face": {"by_outcome": {row[0]: row[1] for row in faces}, "quality_failures": sum(count for outcome, count in faces if outcome in {"NO_FACE", "MULTIPLE_FACES", "LOW_QUALITY"})}}

    def trends(self, filters: AnalyticsFilters) -> list[dict[str, object]]:
        query = self._scope(select(func.date(VerificationModel.created_at).label("day"), func.count(distinct(VerificationModel.id))).where(VerificationModel.created_at >= filters.start, VerificationModel.created_at < filters.end)).group_by(func.date(VerificationModel.created_at)).order_by(func.date(VerificationModel.created_at))
        return [{"date": str(row[0]), "verifications": row[1]} for row in self.db.execute(query)]


def range_for(days: int, end: datetime | None = None) -> AnalyticsFilters:
    upper = (end or datetime.now(UTC)).astimezone(UTC)
    return AnalyticsFilters(upper - timedelta(days=days), upper)

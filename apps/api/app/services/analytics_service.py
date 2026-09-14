from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import distinct, exists, func, select
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
    """Derive metrics from persisted records using one consistent verification cohort.

    The cohort is the set of verifications created in the UTC period and matching every
    supplied filter. Risk counts use the latest assessment per verification; a verification
    is completed only when that latest assessment exists. Failed counts use the persisted
    verification lifecycle status, never a fabricated fallback value.
    """

    def __init__(self, db: Session, actor_id: UUID | None = None, global_access: bool = False) -> None:
        self.db = db
        self.actor_id = actor_id
        self.global_access = global_access

    def _scope(self, query: Any) -> Any:
        if self.actor_id is not None and not self.global_access:
            query = query.where(VerificationModel.owner_id == self.actor_id)
        return query

    def _cohort(self, filters: AnalyticsFilters) -> Any:
        query = select(VerificationModel.id).where(
            VerificationModel.created_at >= filters.start,
            VerificationModel.created_at < filters.end,
        )
        query = self._scope(query)
        if filters.document_type:
            query = query.where(exists(select(DocumentModel.id).where(
                DocumentModel.verification_id == VerificationModel.id,
                DocumentModel.document_type == filters.document_type,
                DocumentModel.status != "DELETED",
            )))
        if filters.case_status or filters.case_priority:
            case_conditions = [CaseModel.verification_id == VerificationModel.id]
            if filters.case_status:
                case_conditions.append(CaseModel.status == filters.case_status)
            if filters.case_priority:
                case_conditions.append(CaseModel.priority == filters.case_priority)
            query = query.where(exists(select(CaseModel.id).where(*case_conditions)))
        if filters.risk_level:
            latest_risk = self._latest_risk_subquery()
            query = query.where(exists(select(RiskAssessmentModel.id).join(
                latest_risk,
                (RiskAssessmentModel.verification_id == latest_risk.c.verification_id)
                & (RiskAssessmentModel.created_at == latest_risk.c.latest),
            ).where(
                RiskAssessmentModel.verification_id == VerificationModel.id,
                RiskAssessmentModel.risk_level == filters.risk_level,
            )))
        return query.distinct().subquery()

    @staticmethod
    def _latest_risk_subquery() -> Any:
        return select(
            RiskAssessmentModel.verification_id,
            func.max(RiskAssessmentModel.created_at).label("latest"),
        ).group_by(RiskAssessmentModel.verification_id).subquery()

    def _latest_risk(self, cohort: Any) -> Any:
        latest = self._latest_risk_subquery()
        return select(RiskAssessmentModel).join(
            latest,
            (RiskAssessmentModel.verification_id == latest.c.verification_id)
            & (RiskAssessmentModel.created_at == latest.c.latest),
        ).where(RiskAssessmentModel.verification_id.in_(select(cohort.c.id))).subquery()

    def overview(self, filters: AnalyticsFilters) -> dict[str, object]:
        cohort = self._cohort(filters)
        total = int(self.db.scalar(select(func.count()).select_from(cohort)) or 0)
        latest_risk = self._latest_risk(cohort)
        risk_rows = self.db.execute(select(latest_risk.c.risk_level, func.count()).group_by(latest_risk.c.risk_level)).all()
        risk_counts = {str(row[0]): int(row[1]) for row in risk_rows}
        completed = sum(risk_counts.values())
        failed = int(self.db.scalar(select(func.count()).select_from(VerificationModel).where(
            VerificationModel.id.in_(select(cohort.c.id)), VerificationModel.status == "FAILED",
        )) or 0)
        pending = max(0, total - completed - failed)
        avg_score = self.db.scalar(select(func.avg(latest_risk.c.risk_score)))
        case_base = select(CaseModel).where(CaseModel.verification_id.in_(select(cohort.c.id)))
        case_rows = self.db.execute(select(CaseModel.status, func.count()).where(CaseModel.verification_id.in_(select(cohort.c.id))).group_by(CaseModel.status)).all()
        priority_rows = self.db.execute(select(CaseModel.priority, func.count()).where(CaseModel.verification_id.in_(select(cohort.c.id))).group_by(CaseModel.priority)).all()
        high_risk = int(self.db.scalar(select(func.count(distinct(CaseModel.id))).where(
            CaseModel.verification_id.in_(select(cohort.c.id)),
            exists(select(latest_risk.c.verification_id).where(latest_risk.c.verification_id == CaseModel.verification_id, latest_risk.c.risk_level == "HIGH")),
        )) or 0)
        return {
            "timezone": "UTC",
            "period": {"start": filters.start.isoformat(), "end": filters.end.isoformat()},
            "filters": {"risk_level": filters.risk_level, "case_status": filters.case_status, "case_priority": filters.case_priority, "document_type": filters.document_type},
            "verification": {"total": total, "completed": completed, "failed": failed, "pending": pending, "completion_rate": round(completed / total, 4) if total else None},
            "risk": {"low": risk_counts.get("LOW", 0), "review": risk_counts.get("REVIEW", 0), "high": risk_counts.get("HIGH", 0), "average_score": round(float(avg_score), 2) if avg_score is not None else None, "distribution": risk_counts},
            "cases": {"total": int(self.db.scalar(select(func.count()).select_from(case_base.subquery())) or 0), "by_status": {str(row[0]): int(row[1]) for row in case_rows}, "by_priority": {str(row[0]): int(row[1]) for row in priority_rows}, "high_risk": high_risk},
            "modules": self._modules(cohort),
            "demo": False,
        }

    def _modules(self, cohort: Any) -> dict[str, object]:
        documents = select(DocumentModel.id).where(DocumentModel.verification_id.in_(select(cohort.c.id)), DocumentModel.status != "DELETED").subquery()
        ocr = self.db.execute(select(OCRResultModel.status, func.count(), func.avg(OCRResultModel.overall_confidence)).where(OCRResultModel.document_id.in_(select(documents.c.id))).group_by(OCRResultModel.status)).all()
        validation = self.db.execute(select(DocumentValidationModel.status, func.count()).where(DocumentValidationModel.document_id.in_(select(documents.c.id))).group_by(DocumentValidationModel.status)).all()
        tampering = self.db.execute(select(TamperingResultModel.status, func.count()).where(TamperingResultModel.document_id.in_(select(documents.c.id))).group_by(TamperingResultModel.status)).all()
        findings = self.db.execute(select(TamperingFindingModel.severity, func.count()).join(TamperingResultModel).where(TamperingResultModel.document_id.in_(select(documents.c.id))).group_by(TamperingFindingModel.severity)).all()
        faces = self.db.execute(select(FaceVerificationModel.outcome, func.count()).where(FaceVerificationModel.document_id.in_(select(documents.c.id))).group_by(FaceVerificationModel.outcome)).all()
        return {
            "ocr": {"by_status": {str(row[0]): int(row[1]) for row in ocr}, "average_confidence": round(sum(float(row[2] or 0) for row in ocr) / len(ocr), 4) if ocr else None},
            "validation": {"by_status": {str(row[0]): int(row[1]) for row in validation}},
            "tampering": {"by_status": {str(row[0]): int(row[1]) for row in tampering}, "finding_severity": {str(row[0]): int(row[1]) for row in findings}},
            "face": {"by_outcome": {str(row[0]): int(row[1]) for row in faces}, "quality_failures": sum(int(count) for outcome, count in faces if outcome in {"NO_FACE", "MULTIPLE_FACES", "LOW_QUALITY"})},
        }

    def trends(self, filters: AnalyticsFilters) -> list[dict[str, object]]:
        cohort = self._cohort(filters)
        query = select(func.date(VerificationModel.created_at).label("day"), func.count(distinct(VerificationModel.id))).where(VerificationModel.id.in_(select(cohort.c.id))).group_by(func.date(VerificationModel.created_at)).order_by(func.date(VerificationModel.created_at))
        return [{"date": str(row[0]), "verifications": int(row[1])} for row in self.db.execute(query)]


def range_for(days: int, end: datetime | None = None) -> AnalyticsFilters:
    upper = (end or datetime.now(UTC)).astimezone(UTC)
    return AnalyticsFilters(upper - timedelta(days=days), upper)


__all__ = ["AnalyticsFilters", "AnalyticsService", "range_for"]


# Keep this symbol referenced for static analyzers while allowing SQLAlchemy to infer the
# relationship joins in the aggregate queries above.
_ = Any

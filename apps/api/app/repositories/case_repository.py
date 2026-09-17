from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEventModel,
    CaseDecisionModel,
    CaseEvidenceModel,
    CaseModel,
    CaseNoteModel,
    DocumentModel,
    FaceVerificationModel,
    OCRResultModel,
    RiskAssessmentModel,
    TamperingFindingModel,
    TamperingResultModel,
    VerificationModel,
)
from app.domain.cases import CasePriority, CaseRecord, CaseStatus, OfficerDecision


def iso(value: datetime | None) -> str | None:
    return None if value is None else (value.astimezone(UTC) if value.tzinfo else value.replace(tzinfo=UTC)).isoformat()


def record(model: CaseModel) -> CaseRecord:
    return CaseRecord(model.id, model.case_number, model.verification_id, model.title, model.description, CaseStatus(model.status), CasePriority(model.priority), model.assigned_to, model.assigned_supervisor, model.created_by, model.resolved_by, model.resolution, model.resolution_reason, iso(model.created_at) or "", iso(model.updated_at) or "", iso(model.resolved_at), iso(model.closed_at))


class SqlAlchemyCaseRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def _case(self, case_id: UUID, actor_id: UUID, broad: bool = False) -> CaseModel | None:
        query = select(CaseModel).where(CaseModel.id == case_id)
        if not broad:
            query = query.join(VerificationModel).where(or_(VerificationModel.owner_id == actor_id, CaseModel.created_by == actor_id, CaseModel.assigned_to == actor_id, CaseModel.assigned_supervisor == actor_id))
        return self.db.scalar(query)

    def verification_for_owner(self, verification_id: UUID, actor_id: UUID) -> VerificationModel | None:
        return self.db.scalar(select(VerificationModel).where(VerificationModel.id == verification_id, VerificationModel.owner_id == actor_id))

    def create_case(self, verification_id: UUID, actor_id: UUID, title: str, description: str, priority: CasePriority) -> CaseRecord:
        if self.db.scalar(select(CaseModel).where(CaseModel.verification_id == verification_id)) is not None:
            raise ValueError("An investigation case already exists for this verification.")
        now = datetime.now(UTC)
        year = now.year
        count = self.db.scalar(select(func.count()).select_from(CaseModel).where(CaseModel.case_number.like(f"TRUST-{year}-%"))) or 0
        model = CaseModel(id=uuid4(), case_number=f"TRUST-{year}-{int(count) + 1:06d}", verification_id=verification_id, title=title.strip(), description=description.strip(), status=CaseStatus.OPEN.value, priority=priority.value, created_by=actor_id, created_at=now, updated_at=now)
        self.db.add(model); self.db.flush()
        self.db.add(AuditEventModel(event_type="CASE_CREATED", actor_id=actor_id, verification_id=verification_id, case_id=model.id, status=CaseStatus.OPEN.value, created_at=now))
        self._attach_analysis_evidence(model, actor_id)
        self.db.commit()
        return record(model)

    def _attach_analysis_evidence(self, case: CaseModel, actor_id: UUID) -> None:
        document = self.db.scalar(select(DocumentModel).where(DocumentModel.verification_id == case.verification_id).order_by(DocumentModel.created_at.desc()))
        if document is not None:
            self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="DOCUMENT", source_type="document", source_id=document.id, title="Verification document", summary="Document reference from the linked verification.", severity="INFO", created_by=actor_id))
            ocr = self.db.scalar(select(OCRResultModel).where(OCRResultModel.document_id == document.id).order_by(OCRResultModel.created_at.desc()))
            if ocr is not None:
                self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="OCR_RESULT", source_type="ocr_result", source_id=ocr.id, title="Structured OCR result", summary="Structured OCR output is available for investigation context.", severity="INFO", created_by=actor_id))
            tampering = self.db.scalar(select(TamperingResultModel).where(TamperingResultModel.document_id == document.id).order_by(TamperingResultModel.created_at.desc()))
            if tampering is not None:
                self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="TAMPERING_RESULT", source_type="tampering_result", source_id=tampering.id, title="Technical document analysis", summary=tampering.summary, severity="REVIEW" if tampering.technical_signal_score > 0 else "INFO", created_by=actor_id))
                finding = self.db.scalar(select(TamperingFindingModel).where(TamperingFindingModel.tampering_result_id == tampering.id).order_by(TamperingFindingModel.confidence.desc()))
                if finding is not None:
                    self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="TAMPERING_FINDING", source_type="tampering_finding", source_id=finding.id, title=finding.title, summary="Technical inconsistency detected; requires officer review.", severity=finding.severity, created_by=actor_id))
            face = self.db.scalar(select(FaceVerificationModel).where(FaceVerificationModel.verification_id == case.verification_id, FaceVerificationModel.document_id == document.id).order_by(FaceVerificationModel.created_at.desc()))
            if face is not None:
                self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="FACE_VERIFICATION", source_type="face_verification", source_id=face.id, title="Face comparison result", summary=face.summary, severity="REVIEW" if face.outcome != "MATCH" else "INFO", created_by=actor_id))
        risk = self.db.scalar(select(RiskAssessmentModel).where(RiskAssessmentModel.verification_id == case.verification_id).order_by(RiskAssessmentModel.created_at.desc()))
        if risk is not None:
            self.db.add(CaseEvidenceModel(id=uuid4(), case_id=case.id, evidence_type="RISK_ASSESSMENT", source_type="risk_assessment", source_id=risk.id, title=f"Risk assessment: {risk.risk_level}", summary=risk.recommendation, severity=risk.risk_level, created_by=actor_id))

    def get(self, case_id: UUID, actor_id: UUID, broad: bool = False) -> CaseModel | None:
        return self._case(case_id, actor_id, broad)

    def list_cases(self, actor_id: UUID, status: str | None = None, priority: str | None = None, risk_level: str | None = None, search: str | None = None, limit: int = 50, offset: int = 0, broad: bool = False) -> list[CaseRecord]:
        query = select(CaseModel).join(VerificationModel)
        if not broad: query = query.where(or_(VerificationModel.owner_id == actor_id, CaseModel.created_by == actor_id, CaseModel.assigned_to == actor_id, CaseModel.assigned_supervisor == actor_id))
        if status: query = query.where(CaseModel.status == status)
        if priority: query = query.where(CaseModel.priority == priority)
        if search: query = query.where(or_(CaseModel.case_number.ilike(f"%{search}%"), CaseModel.title.ilike(f"%{search}%")))
        if risk_level: query = query.join(RiskAssessmentModel, RiskAssessmentModel.verification_id == CaseModel.verification_id).where(RiskAssessmentModel.risk_level == risk_level)
        return [record(item) for item in self.db.scalars(query.order_by(CaseModel.updated_at.desc()).limit(limit).offset(offset)).all()]

    def update_case(self, model: CaseModel, actor_id: UUID, title: str | None = None, description: str | None = None, priority: CasePriority | None = None) -> CaseRecord:
        if model.status == CaseStatus.CLOSED.value: raise ValueError("Closed cases are immutable.")
        if title is not None: model.title = title.strip()
        if description is not None: model.description = description.strip()
        if priority is not None and priority.value != model.priority:
            model.priority = priority.value
            self.db.add(AuditEventModel(event_type="CASE_PRIORITY_CHANGED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status=model.priority, created_at=datetime.now(UTC)))
        model.updated_at = datetime.now(UTC); self.db.add(AuditEventModel(event_type="CASE_UPDATED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status=model.status, created_at=datetime.now(UTC))); self.db.commit(); return record(model)

    def assign(self, model: CaseModel, actor_id: UUID, assigned_to: UUID | None, supervisor: UUID | None) -> CaseRecord:
        if model.status == CaseStatus.CLOSED.value: raise ValueError("Closed cases cannot be assigned.")
        model.assigned_to, model.assigned_supervisor, model.updated_at = assigned_to, supervisor, datetime.now(UTC)
        self.db.add(AuditEventModel(event_type="CASE_ASSIGNED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status="ASSIGNED", created_at=datetime.now(UTC))); self.db.commit(); return record(model)

    def change_status(self, model: CaseModel, actor_id: UUID, target: CaseStatus) -> CaseRecord:
        from app.domain.cases import validate_transition
        validate_transition(CaseStatus(model.status), target)
        now = datetime.now(UTC); model.status = target.value; model.updated_at = now
        if target == CaseStatus.RESOLVED: model.resolved_at, model.resolved_by = now, actor_id
        if target == CaseStatus.CLOSED: model.closed_at = now
        event = "CASE_ESCALATED" if target == CaseStatus.ESCALATED else "CASE_RESOLVED" if target == CaseStatus.RESOLVED else "CASE_CLOSED" if target == CaseStatus.CLOSED else "CASE_STATUS_CHANGED"
        self.db.add(AuditEventModel(event_type=event, actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status=target.value, created_at=now)); self.db.commit(); return record(model)

    def add_note(self, model: CaseModel, actor_id: UUID, body: str) -> UUID:
        if model.status == CaseStatus.CLOSED.value: raise ValueError("Closed cases do not accept notes.")
        note = CaseNoteModel(id=uuid4(), case_id=model.id, author_id=actor_id, body=body.strip(), created_at=datetime.now(UTC), updated_at=datetime.now(UTC)); self.db.add(note); self.db.add(AuditEventModel(event_type="CASE_NOTE_ADDED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status="ADDED", created_at=datetime.now(UTC))); self.db.commit(); return note.id

    def get_notes(self, case_id: UUID) -> list[CaseNoteModel]: return list(self.db.scalars(select(CaseNoteModel).where(CaseNoteModel.case_id == case_id).order_by(CaseNoteModel.created_at)).all())
    def get_evidence(self, case_id: UUID) -> list[CaseEvidenceModel]: return list(self.db.scalars(select(CaseEvidenceModel).where(CaseEvidenceModel.case_id == case_id).order_by(CaseEvidenceModel.created_at)).all())
    def add_evidence(self, model: CaseModel, actor_id: UUID, evidence_type: str, source_type: str, source_id: UUID, title: str, summary: str, severity: str) -> CaseEvidenceModel:
        if model.status == CaseStatus.CLOSED.value: raise ValueError("Closed cases do not accept evidence.")
        valid = {"document": DocumentModel, "ocr_result": OCRResultModel, "tampering_result": TamperingResultModel, "tampering_finding": TamperingFindingModel, "face_verification": FaceVerificationModel, "risk_assessment": RiskAssessmentModel}
        entity = valid.get(source_type)
        if entity is None or self.db.get(entity, source_id) is None: raise ValueError("Evidence source does not exist.")
        item = CaseEvidenceModel(id=uuid4(), case_id=model.id, evidence_type=evidence_type, source_type=source_type, source_id=source_id, title=title.strip(), summary=summary.strip(), severity=severity, created_by=actor_id, created_at=datetime.now(UTC)); self.db.add(item); self.db.add(AuditEventModel(event_type="CASE_EVIDENCE_ADDED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status="ADDED", created_at=datetime.now(UTC))); self.db.commit(); return item

    def decision(self, model: CaseModel, actor_id: UUID, value: OfficerDecision, reason: str, decision_context: dict[str, object] | None = None) -> CaseDecisionModel:
        if model.status == CaseStatus.CLOSED.value:
            raise ValueError("Closed cases cannot receive decisions.")
        if self.db.scalar(select(CaseDecisionModel).where(CaseDecisionModel.case_id == model.id)) is not None:
            raise ValueError("A decision has already been recorded for this case.")
        now = datetime.now(UTC)
        item = CaseDecisionModel(id=uuid4(), case_id=model.id, decision=value.value, reason=reason, decision_context=decision_context, decided_by=actor_id, created_at=now)
        self.db.add(item)
        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise ValueError("A decision has already been recorded for this case.") from exc
        model.status = CaseStatus.UNDER_REVIEW.value if value == OfficerDecision.REVIEW else CaseStatus.RESOLVED.value
        model.resolution = value.value
        model.resolution_reason = reason
        model.updated_at = now
        if value != OfficerDecision.REVIEW:
            model.resolved_by = actor_id
            model.resolved_at = now
        self.db.add(AuditEventModel(event_type="CASE_DECISION_RECORDED", actor_id=actor_id, verification_id=model.verification_id, case_id=model.id, status=value.value, created_at=now))
        self.db.commit()
        return item

    def get_timeline(self, case_id: UUID) -> list[AuditEventModel]: return list(self.db.scalars(select(AuditEventModel).where(AuditEventModel.case_id == case_id).order_by(AuditEventModel.created_at)).all())

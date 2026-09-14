from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Any
from uuid import UUID, uuid4

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db.models import (
    AuditEventModel,
    CaseDecisionModel,
    CaseEvidenceModel,
    CaseModel,
    CaseNoteModel,
    DocumentModel,
    DocumentValidationModel,
    FaceVerificationModel,
    OCRResultModel,
    ReportModel,
    RiskAssessmentModel,
    TamperingResultModel,
    VerificationModel,
)

DISCLAIMER = "This report summarizes AI-assisted verification signals and human workflow records. It does not independently establish identity, fraud, criminality, immigration eligibility, or legal status."
VERSION = "phase11-v1"


def _safe(value: object | None) -> str:
    return "Unavailable" if value is None else str(value)


def _pdf(title: str, lines: list[str]) -> bytes:
    buffer = BytesIO(); document = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=42, leftMargin=42, topMargin=42, bottomMargin=42); styles = getSampleStyleSheet(); story = [Paragraph(title, styles["Title"]), Spacer(1, 12)]
    for line in lines: story.extend([Paragraph(line.replace("&", "&amp;"), styles["BodyText"]), Spacer(1, 6)])
    document.build(story); return buffer.getvalue()


class ReportService:
    def __init__(self, db: Session) -> None: self.db = db

    def _latest(self, model: Any, column: Any, value: UUID) -> Any:
        return self.db.scalar(select(model).where(column == value).order_by(model.created_at.desc()))

    def verification_report(self, verification_id: UUID, actor_id: UUID) -> tuple[bytes, UUID]:
        verification = self.db.scalar(select(VerificationModel).where(VerificationModel.id == verification_id, VerificationModel.owner_id == actor_id))
        if verification is None: raise LookupError("Verification report is not available.")
        document = self._latest(DocumentModel, DocumentModel.verification_id, verification_id)
        if document is None: raise LookupError("Verification has no document report data.")
        ocr = self._latest(OCRResultModel, OCRResultModel.document_id, document.id); validation = self._latest(DocumentValidationModel, DocumentValidationModel.document_id, document.id); tampering = self._latest(TamperingResultModel, TamperingResultModel.document_id, document.id); face = self._latest(FaceVerificationModel, FaceVerificationModel.document_id, document.id); risk = self._latest(RiskAssessmentModel, RiskAssessmentModel.verification_id, verification_id)
        ocr_fields = [] if ocr is None else list(ocr.fields)
        validation_findings = [] if validation is None else list(validation.findings)
        tampering_findings = [] if tampering is None else list(tampering.findings)
        risk_factors = [] if risk is None else list(risk.factors)
        lines = ["Report ID: pending", f"Generated at (UTC): {datetime.now(UTC).isoformat()}", f"Verification reference: {verification_id}", f"Document type: {document.document_type}", f"Document reference: {document.original_filename} (checksum retained in source record)", f"OCR status: {_safe(None if ocr is None else ocr.status)}", f"OCR confidence: {_safe(None if ocr is None else ocr.overall_confidence)}", f"OCR structured fields: {', '.join(f'{field.name} ({field.confidence:.2f})' for field in ocr_fields) if ocr_fields else 'Unavailable'}", f"Validation: {_safe(None if validation is None else validation.status)}", f"Validation summary: {_safe(None if validation is None else validation.summary)}", f"Validation findings: {len(validation_findings)}", *[f"Validation finding — {finding.name}: {finding.severity}; passed={finding.passed}" for finding in validation_findings], f"Tampering status: {_safe(None if tampering is None else tampering.status)}", f"Tampering summary: {_safe(None if tampering is None else tampering.summary)}", f"Tampering findings: {len(tampering_findings)}", *[f"Technical finding — {finding.title}: {finding.severity}; confidence={finding.confidence:.2f}" for finding in tampering_findings], f"Face outcome: {_safe(None if face is None else face.outcome)}", f"Face similarity: {_safe(None if face is None else face.similarity_score)}", f"Face confidence: {_safe(None if face is None else face.confidence)}", f"Face quality: {_safe(None if face is None else face.document_face_quality)} / {_safe(None if face is None else face.presented_face_quality)}", f"Risk score: {_safe(None if risk is None else risk.risk_score)}", f"Risk level: {_safe(None if risk is None else risk.risk_level)}", f"Recommendation: {_safe(None if risk is None else risk.recommendation)}", f"Risk factors: {len(risk_factors)}", *[f"Risk factor — {factor.factor_name}: {factor.severity}; contribution={factor.contribution}; source={factor.source_module}" for factor in risk_factors], "Officer decision: See linked case workflow; no automatic decision is generated.", "Audit summary: Relevant events remain available through the authorized audit explorer.", f"Disclaimer: {DISCLAIMER}"]
        report_id = uuid4(); lines[0] = f"Report ID: {report_id}"; content = _pdf("TRUSTID VERIFICATION REPORT", lines); now = datetime.now(UTC); self.db.add(ReportModel(id=report_id, report_type="VERIFICATION", reference_type="verification", reference_id=verification_id, generated_by=actor_id, report_version=VERSION, created_at=now)); self.db.add(AuditEventModel(event_type="REPORT_GENERATED", actor_id=actor_id, verification_id=verification_id, status="GENERATED", provider="server-report-service", created_at=now)); self.db.commit(); return content, report_id

    def case_report(self, case_id: UUID, actor_id: UUID) -> tuple[bytes, UUID]:
        case = self.db.scalar(select(CaseModel).join(VerificationModel).where(CaseModel.id == case_id, or_(VerificationModel.owner_id == actor_id, CaseModel.created_by == actor_id, CaseModel.assigned_to == actor_id, CaseModel.assigned_supervisor == actor_id)))
        if case is None: raise LookupError("Case report is not available.")
        evidence = self.db.scalars(select(CaseEvidenceModel).where(CaseEvidenceModel.case_id == case_id).order_by(CaseEvidenceModel.created_at)).all(); notes = self.db.scalars(select(CaseNoteModel).where(CaseNoteModel.case_id == case_id).order_by(CaseNoteModel.created_at)).all(); decisions = self.db.scalars(select(CaseDecisionModel).where(CaseDecisionModel.case_id == case_id).order_by(CaseDecisionModel.created_at)).all()
        lines = ["Report ID: pending", f"Generated at (UTC): {datetime.now(UTC).isoformat()}", f"Case number: {case.case_number}", f"Title: {case.title}", f"Status: {case.status}", f"Priority: {case.priority}", f"Linked verification: {case.verification_id}", f"Resolution: {_safe(case.resolution)}", f"Resolution reason: {_safe(case.resolution_reason)}", f"Evidence references: {len(evidence)}", *[f"Evidence — {item.title}: {item.summary} ({item.source_type})" for item in evidence], f"Officer notes: {len(notes)}", *[f"Note recorded at {item.created_at.isoformat() if item.created_at else 'Unavailable'} by {item.author_id}" for item in notes], f"Officer decisions: {len(decisions)}", *[f"Decision: {item.decision}; reason recorded; decided by {item.decided_by}" for item in decisions], f"Disclaimer: {DISCLAIMER}"]
        report_id = uuid4(); lines[0] = f"Report ID: {report_id}"; content = _pdf("TRUSTID INVESTIGATION CASE REPORT", lines); now = datetime.now(UTC); self.db.add(ReportModel(id=report_id, report_type="CASE", reference_type="case", reference_id=case_id, generated_by=actor_id, report_version=VERSION, created_at=now)); self.db.add(AuditEventModel(event_type="REPORT_GENERATED", actor_id=actor_id, verification_id=case.verification_id, case_id=case_id, status="GENERATED", provider="server-report-service", created_at=now)); self.db.commit(); return content, report_id

    def recent(self, actor_id: UUID, limit: int = 50) -> list[ReportModel]:
        return list(self.db.scalars(select(ReportModel).where(ReportModel.generated_by == actor_id).order_by(ReportModel.created_at.desc()).limit(limit)).all())

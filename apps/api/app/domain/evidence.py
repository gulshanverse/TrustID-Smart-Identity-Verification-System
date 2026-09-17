from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.face import FaceOutcome, FaceVerificationResult
from app.domain.ocr import OCRResult
from app.domain.risk import RiskAssessmentResult, RiskSeverity
from app.domain.tampering import TamperingResult
from app.domain.validation import DocumentValidationResult, ValidationStatus


class EvidenceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INCONCLUSIVE = "INCONCLUSIVE"


class EvidenceSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass(frozen=True)
class EvidenceProvenance:
    module: str
    provider: str
    version: str
    rule: str | None = None


@dataclass(frozen=True)
class NormalizedEvidence:
    evidence_id: UUID
    verification_id: UUID
    source_module: str
    evidence_type: str
    status: EvidenceStatus
    severity: EvidenceSeverity
    confidence: float | None
    score: float | None
    explanation: str
    reason_code: str
    provenance: EvidenceProvenance
    created_at: str


@dataclass(frozen=True)
class VerificationFinding:
    finding_id: UUID
    verification_id: UUID
    code: str
    status: EvidenceStatus
    severity: EvidenceSeverity
    title: str
    explanation: str
    evidence_ids: tuple[UUID, ...]
    provenance: EvidenceProvenance
    risk_contribution: int
    created_at: str


@dataclass(frozen=True)
class CorrelationResult:
    evidence: tuple[NormalizedEvidence, ...]
    findings: tuple[VerificationFinding, ...]
    summary: str


def _id(verification_id: UUID, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trustid:evidence:{verification_id}:{key}")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _prov(module: str, provider: str, version: str, rule: str | None = None) -> EvidenceProvenance:
    return EvidenceProvenance(module, provider, version, rule)


def _item(verification_id: UUID, key: str, module: str, evidence_type: str, status: EvidenceStatus, severity: EvidenceSeverity, explanation: str, code: str, provenance: EvidenceProvenance, confidence: float | None = None, score: float | None = None) -> NormalizedEvidence:
    return NormalizedEvidence(_id(verification_id, key), verification_id, module, evidence_type, status, severity, confidence, score, explanation, code, provenance, _now())


def correlate(verification_id: UUID, ocr: OCRResult, validation: DocumentValidationResult, tampering: TamperingResult, face: FaceVerificationResult, risk: RiskAssessmentResult, external: ExternalVerificationResult | None = None) -> CorrelationResult:
    evidence: list[NormalizedEvidence] = []
    findings: list[VerificationFinding] = []

    ocr_status = EvidenceStatus.PASS if ocr.status.value == "COMPLETED" else EvidenceStatus.NOT_AVAILABLE
    evidence.append(_item(verification_id, "ocr", "OCR", "EXTRACTION", ocr_status, EvidenceSeverity.INFO, "Structured OCR extraction completed." if ocr_status == EvidenceStatus.PASS else "OCR extraction is unavailable.", "OCR_COMPLETED" if ocr_status == EvidenceStatus.PASS else "OCR_NOT_AVAILABLE", _prov("OCR", ocr.provider, ocr.provider_version), ocr.overall_confidence))

    for index, consistency in enumerate(ocr.field_consistency):
        status_value = consistency.get("status") or "NOT_AVAILABLE"
        status = EvidenceStatus.PASS if status_value == "MATCH" else EvidenceStatus.FAIL if status_value == "MISMATCH" else EvidenceStatus.NOT_AVAILABLE
        field = consistency.get("field") or "unknown_field"
        item = _item(verification_id, f"field:{field}:{index}", "MRZ", "FIELD_CONSISTENCY", status, EvidenceSeverity.INFO if status == EvidenceStatus.PASS else EvidenceSeverity.HIGH if status == EvidenceStatus.FAIL else EvidenceSeverity.LOW, f"OCR and MRZ comparison for {field} returned {status_value}.", f"MRZ_OCR_{field.upper()}_{status_value}", _prov("MRZ", "TD3 parser", "repository-td3", "OCR_MRZ_FIELD_COMPARISON"))
        evidence.append(item)
        if status == EvidenceStatus.FAIL:
            findings.append(VerificationFinding(_id(verification_id, f"finding:{item.reason_code}"), verification_id, item.reason_code, EvidenceStatus.FAIL, EvidenceSeverity.HIGH, f"{field.replace('_', ' ').title()} inconsistency", f"The normalized OCR and MRZ values for {field.replace('_', ' ')} differ. This is an inconsistency requiring officer review, not an automatic fraud conclusion.", (item.evidence_id,), item.provenance, 20, item.created_at))

    validation_status = EvidenceStatus.PASS if validation.status == ValidationStatus.PASSED else EvidenceStatus.REVIEW if validation.status == ValidationStatus.REVIEW else EvidenceStatus.FAIL if validation.status == ValidationStatus.FAILED else EvidenceStatus.NOT_AVAILABLE
    validation_severity = EvidenceSeverity.INFO if validation_status == EvidenceStatus.PASS else EvidenceSeverity.MEDIUM
    validation_evidence = _item(verification_id, "validation", "DOCUMENT_VALIDATION", "VALIDATION", validation_status, validation_severity, validation.summary, f"DOCUMENT_VALIDATION_{validation_status.value}", _prov("DOCUMENT_VALIDATION", validation.provider, validation.provider_version))
    evidence.append(validation_evidence)

    tampering_status = EvidenceStatus.NOT_AVAILABLE if tampering.status.value == "NOT_AVAILABLE" else EvidenceStatus.PASS if tampering.technical_signal_score == 0 else EvidenceStatus.REVIEW
    tampering_evidence = _item(verification_id, "tampering", "TAMPERING", "TECHNICAL_SIGNAL", tampering_status, EvidenceSeverity.INFO if tampering_status == EvidenceStatus.PASS else EvidenceSeverity.MEDIUM, tampering.summary, "TAMPERING_CLEAN" if tampering_status == EvidenceStatus.PASS else "TAMPERING_SIGNAL", _prov("TAMPERING", tampering.provider, tampering.provider_version), tampering.overall_confidence, tampering.technical_signal_score)
    evidence.append(tampering_evidence)
    if tampering_status == EvidenceStatus.REVIEW:
        findings.append(VerificationFinding(_id(verification_id, "finding:TAMPERING_SIGNAL"), verification_id, "TAMPERING_SIGNAL", EvidenceStatus.REVIEW, EvidenceSeverity.MEDIUM, "Technical document signal", "Tampering analysis produced a suspicious technical signal. This is a technical signal requiring officer review, not an automatic fraud finding.", (tampering_evidence.evidence_id,), tampering_evidence.provenance, 15, tampering_evidence.created_at))

    face_status = EvidenceStatus.PASS if face.outcome == FaceOutcome.MATCH else EvidenceStatus.FAIL if face.outcome == FaceOutcome.NO_MATCH else EvidenceStatus.REVIEW if face.outcome == FaceOutcome.REVIEW else EvidenceStatus.NOT_AVAILABLE
    face_severity = EvidenceSeverity.INFO if face_status == EvidenceStatus.PASS else EvidenceSeverity.HIGH if face_status == EvidenceStatus.FAIL else EvidenceSeverity.MEDIUM
    face_evidence = _item(verification_id, "face", "FACE", "FACE_COMPARISON", face_status, face_severity, face.summary, f"FACE_{face.outcome.value}", _prov("FACE", face.provider, face.provider_version), face.confidence, face.similarity_score)
    evidence.append(face_evidence)
    if face.outcome == FaceOutcome.NO_MATCH:
        findings.append(VerificationFinding(_id(verification_id, "finding:FACE_NO_MATCH"), verification_id, "FACE_NO_MATCH", EvidenceStatus.FAIL, EvidenceSeverity.HIGH, "Face comparison did not meet threshold", "The face provider returned NO_MATCH. This is a biometric signal requiring enhanced officer review and is not proof of fraud.", (face_evidence.evidence_id,), face_evidence.provenance, 25, face_evidence.created_at))

    risk_evidence = _item(verification_id, "risk", "RISK", "RISK_ASSESSMENT", EvidenceStatus.PASS, EvidenceSeverity.INFO if risk.risk_level.value == "LOW" else EvidenceSeverity.MEDIUM if risk.risk_level.value == "REVIEW" else EvidenceSeverity.HIGH, risk.summary, "RISK_ASSESSMENT_COMPLETED", _prov("RISK", "deterministic risk engine", risk.assessment_version), risk.confidence, float(risk.risk_score))
    evidence.append(risk_evidence)
    for factor in risk.factors:
        if factor.contribution > 0:
            findings.append(VerificationFinding(_id(verification_id, f"finding:RISK:{factor.name}"), verification_id, "RISK_CONTRIBUTION", EvidenceStatus.REVIEW, EvidenceSeverity.HIGH if factor.severity == RiskSeverity.HIGH else EvidenceSeverity.MEDIUM, factor.name, factor.explanation, (risk_evidence.evidence_id,), _prov("RISK", "deterministic risk engine", risk.assessment_version, factor.source_module), factor.contribution, risk_evidence.created_at))

    if external is not None:
        external_status = EvidenceStatus.PASS if external.status == ExternalStatus.VERIFIED else EvidenceStatus.FAIL if external.status == ExternalStatus.NO_MATCH else EvidenceStatus.NOT_AVAILABLE if external.status == ExternalStatus.NOT_AVAILABLE else EvidenceStatus.INCONCLUSIVE
        external_evidence = _item(verification_id, "external", "EXTERNAL_VERIFICATION", "DATABASE_RESULT", external_status, EvidenceSeverity.INFO if external_status == EvidenceStatus.PASS else EvidenceSeverity.MEDIUM, external.reason, f"EXTERNAL_{external.status.value}", _prov("EXTERNAL_VERIFICATION", external.provider, external.provider_version), None)
        evidence.append(external_evidence)
        if external.status == ExternalStatus.NO_MATCH:
            findings.append(VerificationFinding(_id(verification_id, "finding:EXTERNAL_RECORD_MISMATCH"), verification_id, "EXTERNAL_RECORD_MISMATCH", EvidenceStatus.FAIL, EvidenceSeverity.HIGH, "External record did not match", "An authorized provider returned NO_MATCH. This is a contradiction requiring officer review, not confirmation of fraud.", (external_evidence.evidence_id,), external_evidence.provenance, 0, external_evidence.created_at))

    severity_order = {EvidenceSeverity.CRITICAL: 0, EvidenceSeverity.HIGH: 1, EvidenceSeverity.MEDIUM: 2, EvidenceSeverity.LOW: 3, EvidenceSeverity.INFO: 4}
    ordered_findings = tuple(sorted(findings, key=lambda item: (severity_order[item.severity], item.code)))
    summary = f"Correlated {len(evidence)} evidence items and {len(ordered_findings)} findings across OCR, MRZ, validation, tampering, face, and risk modules."
    return CorrelationResult(tuple(evidence), ordered_findings, summary)

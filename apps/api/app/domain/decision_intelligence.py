from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.evidence import CorrelationResult
from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.face import FaceOutcome, FaceVerificationResult
from app.domain.ocr import OCRResult
from app.domain.risk import RiskAssessmentResult
from app.domain.tampering import TamperingResult, TamperingStatus
from app.domain.validation import DocumentValidationResult, ValidationStatus


class ReviewPriority(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


@dataclass(frozen=True)
class DecisionEvidence:
    evidence_id: UUID
    category: str
    source: str
    status: str
    severity: str
    explanation: str
    provider: str
    version: str
    rule_id: str | None = None


@dataclass(frozen=True)
class Contradiction:
    code: str
    severity: str
    evidence_ids: tuple[UUID, ...]
    explanation: str
    provenance: str


@dataclass(frozen=True)
class ReviewPriorityItem:
    priority: ReviewPriority
    code: str
    explanation: str
    evidence_ids: tuple[UUID, ...]


@dataclass(frozen=True)
class MissingInformation:
    code: str
    status: str
    explanation: str


@dataclass(frozen=True)
class RiskContext:
    score: int
    band: str
    assessment_version: str
    factors: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class DecisionIntelligenceResult:
    verification_id: UUID
    status: str
    version: str
    generated_at: str
    analysis_fingerprint: str
    evidence_summary: tuple[DecisionEvidence, ...]
    contradictions: tuple[Contradiction, ...]
    review_priorities: tuple[ReviewPriorityItem, ...]
    missing_information: tuple[MissingInformation, ...]
    risk_context: RiskContext
    provenance: tuple[str, ...]

    def snapshot(self) -> dict[str, object]:
        """Return safe immutable context for historical officer-decision storage."""
        return {
            "decision_intelligence_version": self.version,
            "analysis_fingerprint": self.analysis_fingerprint,
            "risk": {
                "score": self.risk_context.score,
                "band": self.risk_context.band,
                "assessment_version": self.risk_context.assessment_version,
                "factors": list(self.risk_context.factors),
            },
            "evidence_ids": [str(item.evidence_id) for item in self.evidence_summary],
            "correlation": [
                {"code": item.code, "evidence_ids": [str(value) for value in item.evidence_ids]}
                for item in self.contradictions
            ],
            "review_priorities": [
                {"code": item.code, "priority": item.priority.value, "evidence_ids": [str(value) for value in item.evidence_ids]}
                for item in self.review_priorities
            ],
            "missing_information": [
                {"code": item.code, "status": item.status} for item in self.missing_information
            ],
            "provenance": list(self.provenance),
        }


def _id(verification_id: UUID, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trustid:decision-intelligence:{verification_id}:{key}")


def _category(source: str) -> str:
    return "DOCUMENT" if source in {"OCR", "MRZ", "DOCUMENT_VALIDATION"} else "IDENTITY" if source == "FACE" else "FORENSICS" if source == "TAMPERING" else "EXTERNAL" if source == "EXTERNAL_VERIFICATION" else "CORRELATION"


def _fingerprint(value: object) -> str:
    normalized = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True, default=str)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class DecisionIntelligenceService:
    version = "phase6-decision-intelligence-v1"

    def build(self, verification_id: UUID, ocr: OCRResult, validation: DocumentValidationResult, tampering: TamperingResult, face: FaceVerificationResult, risk: RiskAssessmentResult, correlation: CorrelationResult, external: ExternalVerificationResult | None = None) -> DecisionIntelligenceResult:
        evidence: list[DecisionEvidence] = [
            DecisionEvidence(item.evidence_id, _category(item.source_module), item.source_module, item.status.value, item.severity.value, item.explanation, item.provenance.provider, item.provenance.version, item.provenance.rule)
            for item in correlation.evidence
        ]
        evidence.extend(
            DecisionEvidence(_id(verification_id, f"rule:{rule.rule_id}:{index}"), "DOCUMENT", "LOCAL_RULES", rule.status.value, rule.severity, rule.explanation, rule.provenance, rule.rule_version, rule.rule_id)
            for index, rule in enumerate(validation.rules)
        )
        evidence.sort(key=lambda item: (item.category, item.source, item.evidence_id.hex))
        evidence_by_source = {item.source: item.evidence_id for item in evidence}
        finding_by_code = {item.code: item for item in correlation.findings}

        contradictions: list[Contradiction] = []
        for finding in correlation.findings:
            if finding.code in {"MRZ_OCR_PASSPORT_NUMBER_MISMATCH", "MRZ_OCR_DATE_OF_BIRTH_MISMATCH", "MRZ_OCR_EXPIRY_DATE_MISMATCH", "EXTERNAL_RECORD_MISMATCH"}:
                contradictions.append(Contradiction(finding.code, finding.severity.value, finding.evidence_ids, "Evidence conflict requiring officer review. " + finding.explanation, f"{finding.provenance.module}:{finding.provenance.version}"))
        if validation.status == ValidationStatus.FAILED and face.outcome == FaceOutcome.MATCH:
            contradictions.append(Contradiction("VALID_FACE_DOCUMENT_VALIDATION_FAILURE", "HIGH", (), "Document validation failed while face verification returned MATCH. Evidence conflict requiring officer review.", "Phase 3 correlation and authoritative risk assessment"))
        if external is not None and external.status == ExternalStatus.UNKNOWN:
            contradictions.append(Contradiction("EXTERNAL_UNKNOWN_WITH_LOCAL_EVIDENCE", "MEDIUM", (), "External verification is UNKNOWN and cannot establish a result; local evidence remains separate.", f"{external.provider}:{external.provider_version}"))
        contradictions.sort(key=lambda item: (item.severity, item.code))

        priorities: list[ReviewPriorityItem] = []
        def add(priority: ReviewPriority, code: str, explanation: str) -> None:
            finding = finding_by_code.get(code)
            if finding is None and code == "EXTERNAL_NO_MATCH":
                finding = finding_by_code.get("EXTERNAL_RECORD_MISMATCH")
            evidence_ids = () if finding is None else finding.evidence_ids
            if not evidence_ids and code == "DOCUMENT_VALIDATION_FAILED":
                evidence_ids = tuple(item.evidence_id for item in evidence if item.source in {"DOCUMENT_VALIDATION", "LOCAL_RULES"})
            if not evidence_ids and code == "FORENSIC_SIGNAL":
                evidence_ids = (() if evidence_by_source.get("TAMPERING") is None else (evidence_by_source["TAMPERING"],))
            priorities.append(ReviewPriorityItem(priority, code, explanation, evidence_ids))
        if face.outcome == FaceOutcome.NO_MATCH:
            add(ReviewPriority.HIGH, "FACE_NO_MATCH", "Face verification returned NO_MATCH. Officer review is required; this does not establish fraud.")
        if external is not None and external.status == ExternalStatus.NO_MATCH:
            add(ReviewPriority.HIGH, "EXTERNAL_NO_MATCH", "An authorized provider returned NO_MATCH. Review the conflict; it is not automatic fraud confirmation.")
        if validation.status == ValidationStatus.FAILED:
            add(ReviewPriority.MEDIUM, "DOCUMENT_VALIDATION_FAILED", validation.summary)
        if tampering.technical_signal_score > 0:
            add(ReviewPriority.MEDIUM, "FORENSIC_SIGNAL", "Tampering analysis produced a technical signal requiring officer review.")
        for item in contradictions:
            if item.code != "EXTERNAL_RECORD_MISMATCH":
                priorities.append(ReviewPriorityItem(ReviewPriority.MEDIUM, item.code, item.explanation, item.evidence_ids))
        if external is None or external.status == ExternalStatus.NOT_AVAILABLE:
            priorities.append(ReviewPriorityItem(ReviewPriority.LOW, "EXTERNAL_NOT_AVAILABLE", "External verification is NOT_AVAILABLE because no authorized provider result is available.", evidence_by_source.get("EXTERNAL_VERIFICATION") and (evidence_by_source["EXTERNAL_VERIFICATION"],) or ()))
        priorities.sort(key=lambda item: (list(ReviewPriority).index(item.priority), item.code))

        missing = [MissingInformation("LIVENESS_NOT_IMPLEMENTED", "NOT_AVAILABLE", "Liveness/PAD is not implemented in the existing provider semantics.")]
        if face.outcome == FaceOutcome.NOT_AVAILABLE:
            missing.append(MissingInformation("FACE_VERIFICATION_NOT_AVAILABLE", "NOT_AVAILABLE", "Face verification did not produce a reliable comparison."))
        if tampering.status != TamperingStatus.COMPLETED:
            missing.append(MissingInformation("TAMPERING_ANALYSIS_NOT_AVAILABLE", "NOT_AVAILABLE", "Tampering analysis did not complete."))
        if ocr.status != ocr.status.COMPLETED:
            missing.append(MissingInformation("OCR_NOT_AVAILABLE", "NOT_AVAILABLE", "OCR did not complete; only persisted structured evidence is presented."))
        if validation.status == ValidationStatus.UNAVAILABLE:
            missing.append(MissingInformation("DOCUMENT_VALIDATION_NOT_AVAILABLE", "NOT_AVAILABLE", "Document validation did not complete."))
        if external is None or external.status == ExternalStatus.NOT_AVAILABLE:
            missing.append(MissingInformation("EXTERNAL_VERIFICATION_NOT_AVAILABLE", "NOT_AVAILABLE", "No authorized external database result is available."))

        factors: tuple[dict[str, object], ...] = tuple({"factor": item.name, "contribution": item.contribution, "source_evidence": item.evidence_reference, "explanation": item.explanation, "provenance": risk.assessment_version} for item in sorted(risk.factors, key=lambda item: (item.source_module, item.name)))
        risk_context = RiskContext(risk.risk_score, risk.risk_level.value, risk.assessment_version, factors)
        fingerprint = _fingerprint({
            "version": self.version,
            "evidence": [{"id": str(item.evidence_id), "category": item.category, "source": item.source, "status": item.status, "severity": item.severity, "explanation": item.explanation, "provider": item.provider, "version": item.version, "rule": item.rule_id} for item in evidence],
            "contradictions": [{"code": item.code, "severity": item.severity, "evidence_ids": [str(value) for value in item.evidence_ids], "explanation": item.explanation, "provenance": item.provenance} for item in contradictions],
            "priorities": [{"priority": item.priority.value, "code": item.code, "explanation": item.explanation, "evidence_ids": [str(value) for value in item.evidence_ids]} for item in priorities],
            "missing": [{"code": item.code, "status": item.status, "explanation": item.explanation} for item in missing],
            "risk": {"score": risk_context.score, "band": risk_context.band, "version": risk_context.assessment_version, "factors": list(factors)},
            "external": None if external is None else {"status": external.status.value, "provider": external.provider, "version": external.provider_version},
            "correlation_summary": correlation.summary,
        })
        return DecisionIntelligenceResult(verification_id, "COMPLETED", self.version, datetime.now(UTC).isoformat(), fingerprint, tuple(evidence), tuple(contradictions), tuple(priorities), tuple(missing), risk_context, ("Phase 3 evidence correlation", "authoritative deterministic risk engine", "Phase 5 rules/provider provenance"))


def decision_snapshot(result: DecisionIntelligenceResult) -> dict[str, object]:
    return result.snapshot()

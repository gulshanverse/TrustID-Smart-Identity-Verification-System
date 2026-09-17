from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid5

from app.domain.evidence import CorrelationResult
from app.domain.external_verification import ExternalStatus, ExternalVerificationResult
from app.domain.face import FaceOutcome, FaceVerificationResult
from app.domain.ocr import OCRResult
from app.domain.risk import RiskAssessmentResult
from app.domain.tampering import TamperingResult
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
    evidence_summary: tuple[DecisionEvidence, ...]
    contradictions: tuple[Contradiction, ...]
    review_priorities: tuple[ReviewPriorityItem, ...]
    missing_information: tuple[MissingInformation, ...]
    risk_context: RiskContext
    provenance: tuple[str, ...]


def _id(verification_id: UUID, key: str) -> UUID:
    return uuid5(NAMESPACE_URL, f"trustid:decision-intelligence:{verification_id}:{key}")


def _category(source: str) -> str:
    return (
        "DOCUMENT"
        if source in {"OCR", "MRZ", "DOCUMENT_VALIDATION"}
        else "IDENTITY"
        if source == "FACE"
        else "FORENSICS"
        if source == "TAMPERING"
        else "EXTERNAL"
        if source == "EXTERNAL_VERIFICATION"
        else "CORRELATION"
    )


class DecisionIntelligenceService:
    version = "phase6-decision-intelligence-v1"

    def build(
        self,
        verification_id: UUID,
        ocr: OCRResult,
        validation: DocumentValidationResult,
        tampering: TamperingResult,
        face: FaceVerificationResult,
        risk: RiskAssessmentResult,
        correlation: CorrelationResult,
        external: ExternalVerificationResult | None = None,
    ) -> DecisionIntelligenceResult:
        evidence: list[DecisionEvidence] = []
        for item in correlation.evidence:
            evidence.append(
                DecisionEvidence(
                    item.evidence_id,
                    _category(item.source_module),
                    item.source_module,
                    item.status.value,
                    item.severity.value,
                    item.explanation,
                    item.provenance.provider,
                    item.provenance.version,
                    item.provenance.rule,
                )
            )
        for index, rule in enumerate(validation.rules):
            evidence.append(
                DecisionEvidence(
                    _id(verification_id, f"rule:{rule.rule_id}:{index}"),
                    "DOCUMENT",
                    "LOCAL_RULES",
                    rule.status.value,
                    rule.severity,
                    rule.explanation,
                    rule.provenance,
                    rule.rule_version,
                    rule.rule_id,
                )
            )
        evidence.sort(key=lambda item: (item.category, item.source, item.evidence_id.hex))

        contradictions: list[Contradiction] = []
        for finding in correlation.findings:
            if finding.code in {
                "MRZ_OCR_PASSPORT_NUMBER_MISMATCH",
                "MRZ_OCR_DATE_OF_BIRTH_MISMATCH",
                "MRZ_OCR_EXPIRY_DATE_MISMATCH",
                "EXTERNAL_RECORD_MISMATCH",
                "FACE_NO_MATCH",
                "TAMPERING_SIGNAL",
            }:
                contradictions.append(
                    Contradiction(
                        finding.code,
                        finding.severity.value,
                        finding.evidence_ids,
                        "Evidence conflict requiring officer review. " + finding.explanation,
                        f"{finding.provenance.module}:{finding.provenance.version}",
                    )
                )
        if validation.status == ValidationStatus.FAILED and face.outcome == FaceOutcome.MATCH:
            contradictions.append(
                Contradiction(
                    "VALID_FACE_DOCUMENT_VALIDATION_FAILURE",
                    "HIGH",
                    (),
                    "Document validation failed while face verification returned MATCH. Evidence conflict requiring officer review.",
                    "Phase 3 correlation and authoritative risk assessment",
                )
            )
        if external is not None and external.status == ExternalStatus.UNKNOWN:
            contradictions.append(
                Contradiction(
                    "EXTERNAL_UNKNOWN_WITH_LOCAL_EVIDENCE",
                    "MEDIUM",
                    (),
                    "External verification is UNKNOWN and cannot establish a result; local evidence remains separate.",
                    f"{external.provider}:{external.provider_version}",
                )
            )
        contradictions.sort(key=lambda item: (item.severity, item.code))

        priorities: list[ReviewPriorityItem] = []
        if face.outcome == FaceOutcome.NO_MATCH:
            priorities.append(
                ReviewPriorityItem(
                    ReviewPriority.HIGH,
                    "FACE_NO_MATCH",
                    "Face verification returned NO_MATCH. Officer review is required; this does not establish fraud.",
                    (),
                )
            )
        if external is not None and external.status == ExternalStatus.NO_MATCH:
            priorities.append(
                ReviewPriorityItem(
                    ReviewPriority.HIGH,
                    "EXTERNAL_NO_MATCH",
                    "An authorized provider returned NO_MATCH. Review the conflict; it is not automatic fraud confirmation.",
                    (),
                )
            )
        if validation.status == ValidationStatus.FAILED:
            priorities.append(
                ReviewPriorityItem(
                    ReviewPriority.MEDIUM, "DOCUMENT_VALIDATION_FAILED", validation.summary, ()
                )
            )
        if tampering.technical_signal_score > 0:
            priorities.append(
                ReviewPriorityItem(
                    ReviewPriority.MEDIUM,
                    "FORENSIC_SIGNAL",
                    "Tampering analysis produced a technical signal requiring officer review.",
                    (),
                )
            )
        for item in contradictions:
            if item.code not in {"FACE_NO_MATCH", "EXTERNAL_RECORD_MISMATCH"}:
                priorities.append(
                    ReviewPriorityItem(
                        ReviewPriority.MEDIUM, item.code, item.explanation, item.evidence_ids
                    )
                )
        if external is None or external.status == ExternalStatus.NOT_AVAILABLE:
            priorities.append(
                ReviewPriorityItem(
                    ReviewPriority.LOW,
                    "EXTERNAL_NOT_AVAILABLE",
                    "External verification is NOT_AVAILABLE because no authorized provider result is available.",
                    (),
                )
            )
        priorities.sort(key=lambda item: (list(ReviewPriority).index(item.priority), item.code))

        missing = [
            MissingInformation(
                "LIVENESS_NOT_IMPLEMENTED",
                "NOT_AVAILABLE",
                "Liveness/PAD is not implemented in the existing provider semantics.",
            ),
            MissingInformation(
                "EXTERNAL_VERIFICATION_NOT_AVAILABLE",
                "NOT_AVAILABLE",
                "No authorized external database result is available.",
            ),
        ]
        if external is not None and external.status != ExternalStatus.NOT_AVAILABLE:
            missing = [
                item for item in missing if item.code != "EXTERNAL_VERIFICATION_NOT_AVAILABLE"
            ]
        factors = tuple(
            {
                "factor": item.name,
                "contribution": item.contribution,
                "source_evidence": item.evidence_reference,
                "explanation": item.explanation,
                "provenance": risk.assessment_version,
            }
            for item in sorted(risk.factors, key=lambda item: (item.source_module, item.name))
        )
        return DecisionIntelligenceResult(
            verification_id,
            "COMPLETED",
            self.version,
            datetime.now(UTC).isoformat(),
            tuple(evidence),
            tuple(contradictions),
            tuple(priorities),
            tuple(missing),
            RiskContext(risk.risk_score, risk.risk_level.value, risk.assessment_version, factors),
            (
                "Phase 3 evidence correlation",
                "authoritative deterministic risk engine",
                "Phase 5 rules/provider provenance",
            ),
        )

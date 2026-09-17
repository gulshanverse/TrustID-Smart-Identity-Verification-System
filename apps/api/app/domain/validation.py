from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID, uuid4

from app.domain.documents import DocumentRecord
from app.domain.ocr import OCRResult
from app.domain.rules import Clock, RuleResult, RulesEngine, RuleStatus


class ValidationStatus(StrEnum):
    PASSED = "PASSED"
    REVIEW = "REVIEW"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"


class ValidationSeverity(StrEnum):
    INFO = "INFO"
    REVIEW = "REVIEW"
    HIGH = "HIGH"


@dataclass(frozen=True)
class ValidationFinding:
    name: str
    severity: ValidationSeverity
    passed: bool
    explanation: str
    reference: str | None = None
    rule_id: str | None = None
    rule_version: str | None = None
    field: str | None = None
    observed: str | None = None
    expected: str | None = None


@dataclass(frozen=True)
class DocumentValidationResult:
    id: UUID
    document_id: UUID
    status: ValidationStatus
    provider: str
    provider_version: str
    summary: str
    findings: tuple[ValidationFinding, ...]
    created_at: str
    updated_at: str
    rules: tuple[RuleResult, ...] = ()


class DocumentValidationProvider:
    name = "provider"
    version = "unknown"

    def validate(self, document: DocumentRecord, ocr: OCRResult) -> tuple[ValidationStatus, str, tuple[ValidationFinding, ...]]:
        raise NotImplementedError


class DemoDocumentValidationProvider(DocumentValidationProvider):
    name = "DEMO / SIMULATED"
    version = "phase5-rules-v1"

    def __init__(self, clock: Clock | None = None) -> None:
        self.engine = RulesEngine(clock)
        self.last_rules: tuple[RuleResult, ...] = ()

    def validate(self, document: DocumentRecord, ocr: OCRResult) -> tuple[ValidationStatus, str, tuple[ValidationFinding, ...]]:
        rules = self.engine.evaluate(document.document_type, ocr)
        self.last_rules = rules
        findings = tuple(self._finding(rule) for rule in rules)
        if ocr.status.value != "COMPLETED":
            return ValidationStatus.UNAVAILABLE, "Document validation is unavailable because OCR did not complete.", findings
        if any(rule.status == RuleStatus.FAIL and rule.severity == "HIGH" for rule in rules):
            return ValidationStatus.FAILED, "Document validation found a significant structured-data issue.", findings
        if any(rule.status in {RuleStatus.FAIL, RuleStatus.REVIEW, RuleStatus.NOT_AVAILABLE} for rule in rules):
            return ValidationStatus.REVIEW, "Document validation requires officer review.", findings
        if all(rule.status == RuleStatus.NOT_APPLICABLE for rule in rules):
            return ValidationStatus.REVIEW, "No applicable rules are configured for this document type.", findings
        return ValidationStatus.PASSED, "Document validation passed the configured deterministic rules.", findings

    @staticmethod
    def _finding(rule: RuleResult) -> ValidationFinding:
        severity = ValidationSeverity.HIGH if rule.severity == "HIGH" else ValidationSeverity.REVIEW if rule.severity == "REVIEW" else ValidationSeverity.INFO
        # Preserve the existing UI/API's compact names while exposing full rule metadata.
        name = "validity" if rule.rule_id in {"PASSPORT_EXPIRY_VALIDITY", "VISA_ENTRY_VALIDITY"} else "required_fields" if "_REQUIRED_" in rule.rule_id else rule.rule_id.lower()
        passed = rule.status == RuleStatus.PASS
        return ValidationFinding(name, severity, passed, rule.explanation, rule.field, rule.rule_id, rule.rule_version, rule.field, rule.observed, rule.expected)


def new_validation_result_id() -> UUID:
    return uuid4()


def validation_timestamp() -> str:
    return datetime.now(UTC).isoformat()

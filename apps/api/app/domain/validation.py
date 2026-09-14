from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from typing import ClassVar
from uuid import UUID, uuid4

from app.domain.documents import DocumentRecord, DocumentType
from app.domain.ocr import OCRResult


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


class DocumentValidationProvider:
    name = "provider"
    version = "unknown"

    def validate(self, document: DocumentRecord, ocr: OCRResult) -> tuple[ValidationStatus, str, tuple[ValidationFinding, ...]]:
        raise NotImplementedError


class DemoDocumentValidationProvider(DocumentValidationProvider):
    name = "DEMO / SIMULATED"
    version = "1.0"

    required_fields: ClassVar[dict[DocumentType, tuple[str, ...]]] = {
        DocumentType.PASSPORT: ("full_name", "passport_number", "nationality", "date_of_birth", "expiry_date"),
        DocumentType.VISA: ("visa_number", "visa_type", "entry_validity", "stay_duration"),
    }

    def validate(self, document: DocumentRecord, ocr: OCRResult) -> tuple[ValidationStatus, str, tuple[ValidationFinding, ...]]:
        values = {field.name: field for field in ocr.fields}
        findings: list[ValidationFinding] = []
        required = self.required_fields.get(document.document_type, ("document_type", "reference"))
        missing = [name for name in required if name not in values or not values[name].normalized_value]
        findings.append(ValidationFinding("required_fields", ValidationSeverity.HIGH if missing else ValidationSeverity.INFO, not missing, "Required structured fields are present." if not missing else f"Required fields are missing: {', '.join(missing)}.", ",".join(missing) if missing else None))
        if document.document_type == DocumentType.PASSPORT and "passport_number" in values:
            valid = values["passport_number"].normalized_value.startswith("DEMO-P")
            findings.append(ValidationFinding("document_number_format", ValidationSeverity.REVIEW, valid, "Document number matches the configured demo format." if valid else "Document number does not match the configured demo format.", "passport_number"))
        expiry_name = "expiry_date" if document.document_type == DocumentType.PASSPORT else "entry_validity"
        if expiry_name in values:
            try:
                expiry = date.fromisoformat(values[expiry_name].normalized_value)
                valid = expiry >= datetime.now(UTC).date()
            except ValueError:
                valid = False
            findings.append(ValidationFinding("validity", ValidationSeverity.HIGH if not valid else ValidationSeverity.INFO, valid, "Document validity date is current." if valid else "Document validity date is expired or malformed.", expiry_name))
        if ocr.status.value != "COMPLETED":
            return ValidationStatus.UNAVAILABLE, "Document validation is unavailable because OCR did not complete.", tuple(findings)
        if any(not item.passed and item.severity == ValidationSeverity.HIGH for item in findings):
            return ValidationStatus.FAILED, "Document validation found a significant structured-data issue.", tuple(findings)
        if any(not item.passed for item in findings):
            return ValidationStatus.REVIEW, "Document validation requires officer review.", tuple(findings)
        return ValidationStatus.PASSED, "Document validation passed the configured deterministic rules.", tuple(findings)


def new_validation_result_id() -> UUID:
    return uuid4()

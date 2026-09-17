from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum

from app.domain.documents import DocumentType
from app.domain.ocr import OCRResult


class RuleStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    INCONCLUSIVE = "INCONCLUSIVE"


class ValidityStatus(StrEnum):
    VALID = "VALID"
    EXPIRED = "EXPIRED"
    NOT_YET_VALID = "NOT_YET_VALID"
    INVALID_DATE = "INVALID_DATE"
    NOT_AVAILABLE = "NOT_AVAILABLE"


@dataclass(frozen=True)
class RuleResult:
    rule_id: str
    rule_version: str
    document_type: DocumentType
    field: str | None
    condition: str
    severity: str
    explanation: str
    status: RuleStatus
    observed: str | None = None
    expected: str | None = None
    provenance: str = "TrustID deterministic rules"


class Clock:
    def today(self) -> date:
        return datetime.now(UTC).date()


class FixedClock(Clock):
    def __init__(self, value: date) -> None:
        self.value = value

    def today(self) -> date:
        return self.value


def evaluate_validity(value: str | None, current_date: date) -> ValidityStatus:
    if not value:
        return ValidityStatus.NOT_AVAILABLE
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return ValidityStatus.INVALID_DATE
    if parsed > current_date:
        return ValidityStatus.NOT_YET_VALID
    return ValidityStatus.VALID


class RulesEngine:
    version = "phase5-rules-v1"

    def __init__(self, clock: Clock | None = None) -> None:
        self.clock = clock or Clock()

    def evaluate(self, document_type: DocumentType, ocr: OCRResult) -> tuple[RuleResult, ...]:
        fields = {item.name: item.normalized_value.strip() for item in ocr.fields if item.normalized_value.strip()}
        results: list[RuleResult] = []
        if ocr.status.value != "COMPLETED":
            return (RuleResult("OCR_REQUIRED", self.version, document_type, None, "OCR status is COMPLETED", "REVIEW", "Rules cannot evaluate fields until OCR completes.", RuleStatus.NOT_AVAILABLE),)
        if document_type == DocumentType.PASSPORT:
            results.extend(self._passport(document_type, fields, ocr))
        elif document_type == DocumentType.VISA:
            results.extend(self._visa(document_type, fields))
        else:
            results.append(RuleResult("UNSUPPORTED_DOCUMENT_TYPE", self.version, document_type, None, "Document type has an authoritative rule catalog", "REVIEW", "This document type is recognized by the domain model but has no Phase 5 rule catalog yet.", RuleStatus.NOT_APPLICABLE))
        return tuple(results)

    def _required(self, document_type: DocumentType, fields: Mapping[str, str], name: str) -> RuleResult:
        present = name in fields
        return RuleResult(f"{document_type.value}_REQUIRED_{name.upper()}", self.version, document_type, name, "field is present and non-empty", "HIGH" if not present else "INFO", "Required field is present." if present else "Required field is missing; this is not a forgery conclusion.", RuleStatus.PASS if present else RuleStatus.FAIL, fields.get(name), "non-empty")

    def _passport(self, document_type: DocumentType, fields: Mapping[str, str], ocr: OCRResult) -> list[RuleResult]:
        results = [self._required(document_type, fields, field) for field in ("full_name", "passport_number", "nationality", "date_of_birth", "expiry_date")]
        number = fields.get("passport_number")
        valid_number = bool(number and re.fullmatch(r"(?:[A-Z0-9]{6,9}|DEMO-P[0-9]{6})", number))
        results.append(RuleResult("PASSPORT_NUMBER_FORMAT", self.version, document_type, "passport_number", "1-9 uppercase alphanumeric characters", "REVIEW", "Passport number format is valid." if valid_number else "Passport number does not match the supported technical format.", RuleStatus.PASS if valid_number else RuleStatus.FAIL, number, "A-Z and 0-9, length 6-9"))
        for field in ("date_of_birth", "expiry_date"):
            value = fields.get(field)
            try:
                parsed = date.fromisoformat(value) if value else None
                valid = parsed is not None
            except ValueError:
                parsed, valid = None, False
            results.append(RuleResult(f"{field.upper()}_ISO_DATE", self.version, document_type, field, "ISO-8601 calendar date", "HIGH" if not valid else "INFO", "Date is valid." if valid else "Date is missing or malformed.", RuleStatus.PASS if valid else RuleStatus.FAIL, value, "YYYY-MM-DD"))
            if field == "date_of_birth" and parsed is not None:
                future = parsed > self.clock.today()
                results.append(RuleResult("DOB_NOT_IN_FUTURE", self.version, document_type, field, "date of birth is not after verification date", "HIGH" if future else "INFO", "Date of birth is valid." if not future else "Date of birth is after the verification date.", RuleStatus.FAIL if future else RuleStatus.PASS, value, f"<= {self.clock.today().isoformat()}"))
        expiry_value = fields.get("expiry_date")
        try:
            expiry = ValidityStatus.NOT_AVAILABLE if not expiry_value else ValidityStatus.VALID if date.fromisoformat(expiry_value) >= self.clock.today() else ValidityStatus.EXPIRED
        except ValueError:
            expiry = ValidityStatus.INVALID_DATE
        results.append(RuleResult("PASSPORT_EXPIRY_VALIDITY", self.version, document_type, "expiry_date", "expiry date is on or after verification date", "HIGH" if expiry != ValidityStatus.VALID else "INFO", f"Passport validity is {expiry.value.lower().replace('_', ' ')}.", RuleStatus.PASS if expiry == ValidityStatus.VALID else RuleStatus.FAIL if expiry in {ValidityStatus.EXPIRED, ValidityStatus.INVALID_DATE} else RuleStatus.REVIEW, fields.get("expiry_date"), f">= {self.clock.today().isoformat()}"))
        if ocr.mrz.detected:
            mrz_ok = ocr.mrz.valid and all(item.valid is not False for item in ocr.mrz.checksums)
            results.append(RuleResult("MRZ_CHECKSUMS", self.version, document_type, "mrz", "all supported MRZ checksums validate", "HIGH" if not mrz_ok else "INFO", "MRZ checksums are valid." if mrz_ok else "One or more MRZ checksums are invalid.", RuleStatus.PASS if mrz_ok else RuleStatus.FAIL, ocr.mrz.normalized_text or None, "valid checksums"))
        else:
            results.append(RuleResult("MRZ_CHECKSUMS", self.version, document_type, "mrz", "MRZ is available for a supported passport format", "REVIEW", "MRZ is not available; no checksum conclusion was made.", RuleStatus.NOT_AVAILABLE, None, "MRZ data"))
        return results

    def _visa(self, document_type: DocumentType, fields: Mapping[str, str]) -> list[RuleResult]:
        results = [self._required(document_type, fields, field) for field in ("visa_number", "visa_type", "entry_validity", "stay_duration")]
        entry = evaluate_validity(fields.get("entry_validity"), self.clock.today())
        results.append(RuleResult("VISA_ENTRY_VALIDITY", self.version, document_type, "entry_validity", "entry date is valid and not expired at verification", "HIGH", f"Visa entry validity is {entry.value.lower().replace('_', ' ')}.", RuleStatus.PASS if entry == ValidityStatus.VALID else RuleStatus.FAIL if entry in {ValidityStatus.EXPIRED, ValidityStatus.INVALID_DATE} else RuleStatus.REVIEW, fields.get("entry_validity"), f"<= {self.clock.today().isoformat()}"))
        duration = fields.get("stay_duration", "")
        match = re.fullmatch(r"(\d+)\s*days?", duration, re.IGNORECASE)
        valid_duration = bool(match and 1 <= int(match.group(1)) <= 365)
        results.append(RuleResult("VISA_STAY_DURATION", self.version, document_type, "stay_duration", "integer duration from 1 through 365 days", "HIGH", "Stay duration is within the configured technical range." if valid_duration else "Stay duration is missing or outside the configured technical range.", RuleStatus.PASS if valid_duration else RuleStatus.FAIL, duration or None, "1-365 days"))
        return results

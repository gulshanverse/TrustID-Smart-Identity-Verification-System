from __future__ import annotations

"""Phase 8 document intelligence.

This module is deliberately deterministic and provider-neutral. It preserves raw
values, never invents confidence, and treats contradictions as review signals.
"""

import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, date, datetime
from enum import StrEnum


class FindingStatus(StrEnum):
    MATCH = "MATCH"
    NO_MATCH = "NO_MATCH"
    REVIEW = "REVIEW"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class FindingSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class NormalizedField:
    name: str
    raw_value: str | None
    normalized_value: str | None
    confidence: float | None
    rule_id: str
    rule_version: str = "8.1"


@dataclass(frozen=True)
class ConsistencyFinding:
    rule_id: str
    rule_version: str
    field: str
    status: FindingStatus
    severity: FindingSeverity
    explanation: str
    provenance: str = "deterministic:advanced-document-intelligence"


@dataclass(frozen=True)
class CrossDocumentFinding:
    code: str
    left_document: str
    right_document: str
    field: str
    status: FindingStatus
    severity: FindingSeverity
    explanation: str
    provenance: str = "deterministic:cross-document-correlation-8.2"


_DATE_FIELDS = {"date_of_birth", "issue_date", "expiry_date", "entry_validity"}
_COUNTRY_FIELDS = {"nationality", "issuing_country", "country_code"}
_NUMBER_FIELDS = {"passport_number", "document_number", "visa_number", "reference"}


def normalize_field(name: str, value: object | None, confidence: float | None = None) -> NormalizedField:
    """Normalize a field while retaining the exact provider/OCR value."""
    raw = None if value is None else str(value)
    key = name.strip().lower()
    if raw is None or not raw.strip():
        normalized = None
    elif key in _DATE_FIELDS:
        normalized = _normalize_date(raw)
    elif key in _COUNTRY_FIELDS:
        normalized = re.sub(r"[^A-Za-z]", "", raw).upper() or None
    elif key in _NUMBER_FIELDS:
        normalized = re.sub(r"[^A-Za-z0-9]", "", raw).upper() or None
    elif key == "gender" or key == "sex":
        normalized = {"MALE": "M", "FEMALE": "F", "X": "X"}.get(raw.strip().upper(), raw.strip().upper())
    else:
        normalized = re.sub(r"\s+", " ", raw.strip()).upper()
    return NormalizedField(key, raw, normalized, confidence, f"NORMALIZE_{key.upper()}")


def normalize_fields(fields: Mapping[str, object | None], confidences: Mapping[str, float | None] | None = None) -> tuple[NormalizedField, ...]:
    confidence_map = confidences or {}
    return tuple(normalize_field(name, value, confidence_map.get(name)) for name, value in fields.items())


def _normalize_date(value: str) -> str | None:
    compact = value.strip().replace("/", "-").replace(".", "-")
    for fmt in ("%Y-%m-%d", "%Y%m%d", "%d-%m-%Y", "%m-%d-%Y"):
        try:
            return datetime.strptime(compact, fmt).replace(tzinfo=UTC).date().isoformat()
        except ValueError:
            continue
    return None


def consistency_checks(fields: Mapping[str, object | None], mrz_fields: Mapping[str, object | None] | None = None) -> tuple[ConsistencyFinding, ...]:
    normalized = {item.name: item for item in normalize_fields(fields)}
    checks: list[ConsistencyFinding] = []

    def date_check(field: str) -> None:
        item = normalized.get(field)
        if item is None or item.normalized_value is None:
            checks.append(ConsistencyFinding(f"DATE_{field.upper()}_AVAILABLE", "8.1", field, FindingStatus.NOT_AVAILABLE, FindingSeverity.LOW, f"{field} is not available or has an unsupported date format."))
            return
        try:
            parsed = date.fromisoformat(item.normalized_value)
            status = FindingStatus.NO_MATCH if field == "date_of_birth" and parsed > datetime.now(UTC).date() else FindingStatus.MATCH
            checks.append(ConsistencyFinding(f"DATE_{field.upper()}_VALID", "8.1", field, status, FindingSeverity.INFO if status == FindingStatus.MATCH else FindingSeverity.MEDIUM, f"{field} is a valid calendar date." if status == FindingStatus.MATCH else f"{field} is in the future; officer review is required."))
        except ValueError:
            checks.append(ConsistencyFinding(f"DATE_{field.upper()}_VALID", "8.1", field, FindingStatus.REVIEW, FindingSeverity.MEDIUM, f"{field} could not be parsed as a calendar date."))

    for field in _DATE_FIELDS:
        if field in fields:
            date_check(field)
    issue = normalized.get("issue_date")
    expiry = normalized.get("expiry_date")
    if issue and expiry and issue.normalized_value and expiry.normalized_value:
        status = FindingStatus.MATCH if issue.normalized_value < expiry.normalized_value else FindingStatus.NO_MATCH
        checks.append(ConsistencyFinding("DATE_EXPIRY_AFTER_ISSUE", "8.1", "expiry_date", status, FindingSeverity.INFO if status == FindingStatus.MATCH else FindingSeverity.MEDIUM, "Expiry date follows issue date." if status == FindingStatus.MATCH else "Expiry date does not follow issue date; officer review is required."))

    if mrz_fields is not None:
        for field in ("passport_number", "date_of_birth", "expiry_date", "nationality"):
            visual = normalized.get(field)
            mrz = normalize_field(field, mrz_fields.get(field))
            if visual is None or visual.normalized_value is None or mrz.normalized_value is None:
                status, explanation = FindingStatus.NOT_AVAILABLE, f"{field} is not available in both visual and MRZ sources."
            else:
                status = FindingStatus.MATCH if visual.normalized_value == mrz.normalized_value else FindingStatus.NO_MATCH
                explanation = f"Visual and MRZ values for {field} match." if status == FindingStatus.MATCH else f"Visual and MRZ values for {field} differ; this is an inconsistency requiring officer review."
            checks.append(ConsistencyFinding(f"MRZ_VISUAL_{field.upper()}", "8.1", field, status, FindingSeverity.INFO if status == FindingStatus.MATCH else FindingSeverity.MEDIUM, explanation, "MRZ parser + OCR visual fields"))
    return tuple(checks)


def correlate_documents(documents: Iterable[tuple[str, Mapping[str, object | None]]]) -> tuple[CrossDocumentFinding, ...]:
    entries = list(documents)
    findings: list[CrossDocumentFinding] = []
    comparable = ("full_name", "date_of_birth", "nationality", "passport_number", "visa_reference", "expiry_date")
    for index, (left_name, left_fields) in enumerate(entries):
        left = {item.name: item.normalized_value for item in normalize_fields(left_fields)}
        for right_name, right_fields in entries[index + 1 :]:
            right = {item.name: item.normalized_value for item in normalize_fields(right_fields)}
            for field in comparable:
                if field not in left or field not in right or not left[field] or not right[field]:
                    continue
                status = FindingStatus.MATCH if left[field] == right[field] else FindingStatus.NO_MATCH
                code = {"full_name": "CROSS_DOCUMENT_NAME_MISMATCH", "date_of_birth": "CROSS_DOCUMENT_DOB_MISMATCH", "visa_reference": "CROSS_DOCUMENT_REFERENCE_MISMATCH", "expiry_date": "CROSS_DOCUMENT_VALIDITY_CONFLICT"}.get(field, "CROSS_DOCUMENT_FIELD_MISMATCH")
                findings.append(CrossDocumentFinding(code, left_name, right_name, field, status, FindingSeverity.INFO if status == FindingStatus.MATCH else FindingSeverity.MEDIUM, f"{field} matches between {left_name} and {right_name}." if status == FindingStatus.MATCH else f"{field} differs between {left_name} and {right_name}; this is a REVIEW signal, not a fraud conclusion."))
    return tuple(findings)


def liveness_boundary() -> dict[str, str]:
    return {"status": "NOT_IMPLEMENTED", "provider": "NONE", "explanation": "No validated presentation-attack detection provider is configured; static face images are never labelled LIVE."}


def advanced_forensics_boundary() -> dict[str, str]:
    return {"status": "DATASET_VALIDATION_PENDING", "provider": "EXISTING_TAMPERING_BOUNDARY", "explanation": "Technical tampering signals remain provider-specific and review-oriented; no forensic certainty is claimed."}


def field_confidence(value: object | None) -> float | None:
    return value if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def field_map(items: Iterable[NormalizedField]) -> dict[str, NormalizedField]:
    return {item.name: item for item in items}


def summarize_findings(findings: Iterable[ConsistencyFinding | CrossDocumentFinding]) -> dict[str, int]:
    summary = {status.value: 0 for status in FindingStatus}
    for finding in findings:
        summary[finding.status.value] += 1
    return summary


__all__ = ["ConsistencyFinding", "CrossDocumentFinding", "FindingSeverity", "FindingStatus", "NormalizedField", "advanced_forensics_boundary", "consistency_checks", "correlate_documents", "field_confidence", "liveness_boundary", "normalize_field", "normalize_fields", "summarize_findings"]

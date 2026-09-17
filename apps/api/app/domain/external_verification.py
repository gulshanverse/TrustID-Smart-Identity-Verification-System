from __future__ import annotations

import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum

from app.domain.documents import DocumentType


class ExternalStatus(StrEnum):
    VERIFIED = "VERIFIED"
    NO_MATCH = "NO_MATCH"
    UNKNOWN = "UNKNOWN"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    UNAUTHORIZED = "UNAUTHORIZED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ExternalVerificationQuery:
    document_type: DocumentType
    document_number: str
    country_code: str | None = None
    date_of_birth_reference: str | None = None

    def minimized(self) -> dict[str, str]:
        result = {"document_type": self.document_type.value, "document_number": self.document_number}
        if self.country_code:
            result["country_code"] = self.country_code
        if self.date_of_birth_reference:
            result["date_of_birth_reference"] = self.date_of_birth_reference
        return result


@dataclass(frozen=True)
class ExternalVerificationResult:
    status: ExternalStatus
    provider: str
    provider_version: str
    reason: str
    query_reference: str | None
    response_timestamp: str
    demo: bool = False


class ExternalVerificationProvider:
    name = "External Verification"
    version = "unknown"

    def verify(self, query: ExternalVerificationQuery) -> ExternalVerificationResult:
        raise NotImplementedError


class ProductionExternalVerificationProvider(ExternalVerificationProvider):
    name = "Production External Verification"
    version = "phase5-production-adapter-v1"

    def __init__(self, configured: bool = False) -> None:
        self.configured = configured

    def verify(self, query: ExternalVerificationQuery) -> ExternalVerificationResult:
        # Deliberately no network fallback: an absent authorized integration is not a demo.
        status = ExternalStatus.UNKNOWN if self.configured else ExternalStatus.NOT_AVAILABLE
        reason = "No authorized external database provider is configured." if not self.configured else "Provider transport is not implemented in this deployment."
        return ExternalVerificationResult(status, self.name, self.version, reason, None, datetime.now(UTC).isoformat())


class MockExternalVerificationProvider(ExternalVerificationProvider):
    name = "Simulated External Verification"
    version = "phase5-mock-v1"

    def __init__(self, outcomes: Mapping[str, ExternalStatus] | None = None) -> None:
        self.outcomes = dict(outcomes or {})

    def verify(self, query: ExternalVerificationQuery) -> ExternalVerificationResult:
        outcome = self.outcomes.get(query.document_number, ExternalStatus.UNKNOWN)
        reference = "demo-" + hashlib.sha256(query.document_number.encode()).hexdigest()[:16]
        return ExternalVerificationResult(outcome, self.name, self.version, "Synthetic demo outcome; not a government or live database result.", reference, datetime.now(UTC).isoformat(), True)


DemoExternalVerificationProvider = MockExternalVerificationProvider

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from uuid import NAMESPACE_URL, UUID, uuid4, uuid5

from app.domain.documents import DocumentRecord
from app.domain.ocr import OCRResult


class TamperingStatus(StrEnum):
    QUEUED = "QUEUED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    NOT_AVAILABLE = "NOT_AVAILABLE"


class TamperingScenario(StrEnum):
    CLEAN = "CLEAN"
    TEXT_MANIPULATION = "TEXT_MANIPULATION"
    PHOTO_INCONSISTENCY = "PHOTO_INCONSISTENCY"
    STAMP_ALTERATION = "STAMP_ALTERATION"
    METADATA_ANOMALY = "METADATA_ANOMALY"


class FindingType(StrEnum):
    TEXT_MANIPULATION = "TEXT_MANIPULATION"
    PHOTO_INCONSISTENCY = "PHOTO_INCONSISTENCY"
    STAMP_ALTERATION = "STAMP_ALTERATION"
    METADATA_ANOMALY = "METADATA_ANOMALY"
    VISUAL_INCONSISTENCY = "VISUAL_INCONSISTENCY"
    DOCUMENT_STRUCTURE_ANOMALY = "DOCUMENT_STRUCTURE_ANOMALY"


class FindingSeverity(StrEnum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


@dataclass(frozen=True)
class TamperingEvidence:
    evidence_type: str
    page: int | None
    region: str | None
    description: str
    source_reference: str | None
    technical_signal: str
    confidence: float


@dataclass(frozen=True)
class TamperingFinding:
    id: UUID
    finding_type: FindingType
    severity: FindingSeverity
    confidence: float
    title: str
    description: str
    evidence: tuple[TamperingEvidence, ...]
    related_ocr_field: str | None = None


@dataclass(frozen=True)
class TamperingResult:
    id: UUID
    document_id: UUID
    status: TamperingStatus
    technical_signal_score: float
    overall_confidence: float
    provider: str
    provider_version: str
    summary: str
    findings: tuple[TamperingFinding, ...]
    created_at: str
    updated_at: str


class TamperingProvider:
    name = "provider"
    version = "unknown"

    def analyze(self, document: DocumentRecord, content: bytes, ocr_result: OCRResult | None) -> tuple[float, float, str, tuple[TamperingFinding, ...]]:
        raise NotImplementedError


class DemoTamperingProvider(TamperingProvider):
    name = "DEMO / SIMULATED"
    version = "1.0"

    def __init__(self, scenario: TamperingScenario = TamperingScenario.CLEAN) -> None:
        self.scenario = scenario

    def analyze(self, document: DocumentRecord, content: bytes, ocr_result: OCRResult | None) -> tuple[float, float, str, tuple[TamperingFinding, ...]]:
        marker = f"TRUSTID-TAMPERING:{self.scenario.value}".encode()
        if marker not in content:
            raise ValueError("The demo tampering provider only processes explicitly marked fixtures.")
        if self.scenario == TamperingScenario.CLEAN:
            return 0.0, 0.96, "No suspicious technical tampering signals detected.", ()
        definitions = {
            TamperingScenario.TEXT_MANIPULATION: (FindingType.TEXT_MANIPULATION, FindingSeverity.MEDIUM, 0.91, "Potential text manipulation detected.", "The analyzed text region contains characteristics that differ from surrounding document text.", "text region", "rendering consistency"),
            TamperingScenario.PHOTO_INCONSISTENCY: (FindingType.PHOTO_INCONSISTENCY, FindingSeverity.MEDIUM, 0.89, "Potential photo replacement/inconsistency detected.", "A deterministic demo fixture marks the photo region for technical review.", "photo region", "region consistency"),
            TamperingScenario.STAMP_ALTERATION: (FindingType.STAMP_ALTERATION, FindingSeverity.HIGH, 0.88, "Potential stamp or visa-region alteration detected.", "A deterministic demo fixture marks the visa/stamp region for technical review.", "visa/stamp region", "region anomaly"),
            TamperingScenario.METADATA_ANOMALY: (FindingType.METADATA_ANOMALY, FindingSeverity.LOW, 0.86, "Suspicious metadata characteristics detected.", "A deterministic demo fixture contains metadata characteristics requiring review.", "metadata", "metadata property"),
        }
        finding_type, severity, confidence, title, description, region, signal = definitions[self.scenario]
        evidence = (TamperingEvidence("region", 1, region, description, f"demo:{self.scenario.value.lower()}", signal, confidence), TamperingEvidence("technical_signal", 1, region, "Fixture-linked technical signal for officer review.", None, signal, confidence))
        field = "passport_number" if self.scenario == TamperingScenario.TEXT_MANIPULATION and ocr_result else None
        finding = TamperingFinding(uuid5(NAMESPACE_URL, f"trustid-demo-tampering:{self.scenario.value}"), finding_type, severity, confidence, title, description, evidence, field)
        return 0.28, confidence, "Technical signal identified; review recommended.", (finding,)


def new_tampering_result_id() -> UUID:
    return uuid4()

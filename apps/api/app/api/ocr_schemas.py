from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.ocr import OCRStatus


class OCREvidenceResponse(BaseModel):
    page: int | None = None
    text: str | None = None
    start_offset: int | None = None
    end_offset: int | None = None
    line_index: int | None = None


class OCRFieldResponse(BaseModel):
    name: str
    value: str
    normalized_value: str
    confidence: float
    source_text: str
    evidence: OCREvidenceResponse | None = None


class OCRResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    document_id: UUID
    status: OCRStatus
    raw_text: str
    language: str
    overall_confidence: float
    provider: str
    provider_version: str
    fields: list[OCRFieldResponse]
    created_at: datetime
    updated_at: datetime

from uuid import UUID

from pydantic import BaseModel, Field

from app.domain.documents import DocumentType


class ExternalVerifyRequest(BaseModel):
    document_type: DocumentType
    document_number: str = Field(min_length=1, max_length=64)
    country_code: str | None = Field(default=None, min_length=2, max_length=3, pattern=r"^[A-Za-z]{2,3}$")

class ExternalVerificationResponse(BaseModel):
    verification_id: UUID
    status: str
    provider: str
    provider_version: str
    reason: str
    query_reference: str | None
    response_timestamp: str
    demo: bool

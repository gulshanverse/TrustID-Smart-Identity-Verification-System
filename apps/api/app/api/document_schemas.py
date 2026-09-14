from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain.documents import DocumentLifecycle, DocumentType


class VerificationResponse(BaseModel):
    id: UUID
    created_at: datetime

class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    verification_id: UUID
    document_type: DocumentType
    original_filename: str
    mime_type: str
    file_size: int
    checksum_sha256: str
    status: DocumentLifecycle
    created_at: datetime
    updated_at: datetime

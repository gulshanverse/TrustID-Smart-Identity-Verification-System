from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.dependencies import require_permission
from app.api.document_schemas import DocumentResponse, VerificationResponse
from app.db.session import get_db
from app.domain.auth import Permission
from app.domain.documents import DocumentRecord, DocumentType
from app.repositories.document_repository import SqlAlchemyDocumentRepository
from app.services.auth_service import AuthUser
from app.services.document_service import DocumentService

router = APIRouter(prefix="/verifications", tags=["documents"])


def get_document_service(db: Session = Depends(get_db)) -> DocumentService:
    from app.main import storage
    return DocumentService(storage, SqlAlchemyDocumentRepository(db))


def to_response(record: DocumentRecord) -> DocumentResponse:
    return DocumentResponse(
        id=record.id, verification_id=record.verification_id, document_type=record.document_type,
        original_filename=record.original_filename, mime_type=record.mime_type, file_size=record.file_size,
        checksum_sha256=record.checksum_sha256, status=record.status,
        created_at=datetime.fromisoformat(record.created_at), updated_at=datetime.fromisoformat(record.updated_at),
    )


@router.post("", response_model=VerificationResponse, status_code=status.HTTP_201_CREATED)
def create_verification(user: AuthUser = Depends(require_permission(Permission.VERIFICATION_WORKFLOW)), service: DocumentService = Depends(get_document_service)) -> VerificationResponse:
    record = service.create_verification(user.id, user.email, user.display_name)
    return VerificationResponse(id=record.id, created_at=datetime.fromisoformat(record.created_at))


@router.post("/{verification_id}/documents", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    verification_id: UUID,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    user: AuthUser = Depends(require_permission(Permission.DOCUMENT_CREATE)),
    service: DocumentService = Depends(get_document_service),
) -> DocumentResponse:
    try:
        content = await file.read()
        record = service.upload(verification_id, user.id, file.filename, file.content_type, content, document_type)
        return to_response(record)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Document storage is unavailable in this environment.") from exc


@router.get("/{verification_id}/documents", response_model=list[DocumentResponse])
def list_documents(verification_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), service: DocumentService = Depends(get_document_service)) -> list[DocumentResponse]:
    try:
        return [to_response(record) for record in service.list_documents(verification_id, user.id)]
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


documents_router = APIRouter(prefix="/documents", tags=["documents"])

@documents_router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_READ)), service: DocumentService = Depends(get_document_service)) -> DocumentResponse:
    try:
        return to_response(service.get_document(document_id, user.id))
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

@documents_router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(document_id: UUID, user: AuthUser = Depends(require_permission(Permission.DOCUMENT_DELETE)), service: DocumentService = Depends(get_document_service)) -> None:
    try:
        service.delete_document(document_id, user.id)
    except LookupError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc

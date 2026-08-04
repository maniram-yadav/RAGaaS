"""`/api/documents/*` router (STORY-010).

Multipart upload plus the basic CRUD surface from plan §7
(`POST /upload`, `GET`, `GET /{id}`, `DELETE /{id}`). Depends only on
`IStorageService`/`IDocumentRepository` (resolved via `StorageFactory`/
`RepositoryFactory`) and `ConfigService` — never a concrete storage/repository
implementation (Dependency Inversion).

Out of scope here (per the story): actually parsing/loading a document's
*content* (STORY-011+) and enqueuing background processing (STORY-015) — a
freshly uploaded `Document` stays in `DocumentStatus.UPLOADED`.

Multi-tenancy: every query is scoped by the caller's `org_id`. `list_by_org`
filters at the query level; `get`/`delete` 404 (never leak existence) for a
document belonging to a different org. The org/tenant model itself hasn't
been built yet (`User.org_id` is a nullable placeholder — see STORY-006's
"Out of scope"), so a user with no `org_id` is scoped to their own user id
instead, keeping isolation meaningful without a real `Organization` model.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.core.config import ConfigService, get_config_service
from app.core.repository_factory import RepositoryFactory, get_repository_factory
from app.core.storage_factory import StorageFactory, get_storage_factory
from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)
from app.domain.ingestion.repository import IDocumentRepository
from app.domain.ingestion.upload_validation import validate_upload
from app.domain.storage.errors import StorageObjectNotFoundError
from app.domain.storage.service import IStorageService
from app.domain.users.entities import User

router = APIRouter(prefix="/api/documents", tags=["documents"])

#: Fallback values used only if `system_config.ingestion` (STORY-003's
#: registered default builder) is somehow unavailable — normal operation
#: always resolves these through `ConfigService`.
_FALLBACK_MAX_UPLOAD_SIZE_BYTES = 20 * 1024 * 1024
_FALLBACK_ALLOWED_EXTENSIONS = [".txt", ".pdf", ".docx", ".xlsx", ".csv"]


class DocumentResponse(BaseModel):
    """Public projection of a `Document`."""

    id: UUID
    org_id: str
    filename: str
    file_type: str
    status: str
    schema_json: dict[str, Any] | None
    uploaded_by: UUID
    created_at: datetime

    @classmethod
    def from_domain(cls, document: Document) -> DocumentResponse:
        return cls(
            id=document.id,
            org_id=document.org_id,
            filename=document.filename,
            file_type=document.file_type,
            status=DocumentStatus(document.status).value,
            schema_json=document.schema_json,
            uploaded_by=document.uploaded_by,
            created_at=document.created_at,
        )


def _org_id_for(user: User) -> str:
    """The tenant scope for `user`'s documents (see module docstring)."""
    return user.org_id or str(user.id)


async def get_document_repository(
    repository_factory: RepositoryFactory = Depends(get_repository_factory),
) -> IDocumentRepository:
    """Resolve the active `IDocumentRepository` (mirrors `get_auth_service`'s shape)."""
    return await repository_factory.get_document_repository()


async def get_storage_service(
    storage_factory: StorageFactory = Depends(get_storage_factory),
) -> IStorageService:
    """Resolve the active `IStorageService`."""
    return await storage_factory.get_storage_service()


async def _read_capped(file: UploadFile, cap: int) -> bytes:
    """Read at most `cap + 1` bytes from `file`.

    Lets an oversized upload be rejected without buffering an arbitrarily
    large file in memory first — reading stops as soon as more than `cap`
    bytes have been seen, which is enough for `validate_upload` to raise
    `FileTooLargeError`.
    """
    chunks: list[bytes] = []
    total = 0
    while total <= cap:
        chunk = await file.read(1024 * 1024)
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    return b"".join(chunks)


@router.post("/upload", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    document_repository: IDocumentRepository = Depends(get_document_repository),
    storage_service: IStorageService = Depends(get_storage_service),
    config_service: ConfigService = Depends(get_config_service),
) -> DocumentResponse:
    """Validate, store, and record metadata for an uploaded file.

    Rejects an oversized or disallowed file type with a clear 4xx before
    anything is persisted. Does not enqueue background processing
    (STORY-015) — the created `Document` stays `DocumentStatus.UPLOADED`.
    """
    ingestion_section = await config_service.get("ingestion")
    max_size_bytes = int(
        ingestion_section.get("max_upload_size_bytes", _FALLBACK_MAX_UPLOAD_SIZE_BYTES)
    )
    allowed_extensions = ingestion_section.get(
        "allowed_extensions", _FALLBACK_ALLOWED_EXTENSIONS
    )

    filename = file.filename or ""
    content = await _read_capped(file, max_size_bytes)

    try:
        extension = validate_upload(
            filename=filename,
            content=content,
            allowed_extensions=allowed_extensions,
            max_size_bytes=max_size_bytes,
        )
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except FileTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE, detail=str(exc)
        ) from exc

    storage_uri = await storage_service.save(filename, content)

    document = Document(
        org_id=_org_id_for(current_user),
        filename=filename,
        file_type=extension,
        storage_uri=storage_uri,
        uploaded_by=current_user.id,
    )
    created = await document_repository.create(document)
    return DocumentResponse.from_domain(created)


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    current_user: User = Depends(get_current_user),
    document_repository: IDocumentRepository = Depends(get_document_repository),
) -> list[DocumentResponse]:
    """List every document belonging to the caller's org."""
    documents = await document_repository.list_by_org(_org_id_for(current_user))
    return [DocumentResponse.from_domain(document) for document in documents]


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_repository: IDocumentRepository = Depends(get_document_repository),
) -> DocumentResponse:
    """Fetch one document, 404ing (never leaking existence) for another org's document."""
    document = await document_repository.get_by_id(document_id)
    if document is None or document.org_id != _org_id_for(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    return DocumentResponse.from_domain(document)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT, response_model=None)
async def delete_document(
    document_id: UUID,
    current_user: User = Depends(get_current_user),
    document_repository: IDocumentRepository = Depends(get_document_repository),
    storage_service: IStorageService = Depends(get_storage_service),
) -> None:
    """Delete a document's metadata and its stored file.

    404s (never leaking existence) for another org's document.
    """
    document = await document_repository.get_by_id(document_id)
    if document is None or document.org_id != _org_id_for(current_user):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        await storage_service.delete(document.storage_uri)
    except StorageObjectNotFoundError:
        pass  # Already gone from storage; still remove the metadata row below.

    try:
        await document_repository.delete(document_id)
    except DocumentNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found"
        ) from exc

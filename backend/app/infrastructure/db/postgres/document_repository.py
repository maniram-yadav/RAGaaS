"""`PostgresDocumentRepository` — the first concrete `IDocumentRepository`.

Follows the exact pattern established by `PostgresUserRepository` (STORY-004).
Deliberately **not** self-registered into a `RepositoryFactory` registry here
— wiring `RepositoryFactory.get_document_repository()` is part of STORY-010's
scope (the upload endpoint is the first consumer), not this story's four
scope bullets.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import DocumentNotFoundError
from app.domain.ingestion.repository import IDocumentRepository
from app.infrastructure.db.postgres.models import DocumentModel


def _to_entity(row: DocumentModel) -> Document:
    return Document(
        id=row.id,
        org_id=row.org_id,
        filename=row.filename,
        file_type=row.file_type,
        storage_uri=row.storage_uri,
        schema_json=row.schema_json,
        status=DocumentStatus(row.status),
        uploaded_by=row.uploaded_by,
        created_at=row.created_at,
    )


class PostgresDocumentRepository(IDocumentRepository):
    """SQLAlchemy 2.0 async implementation of `IDocumentRepository` (Postgres)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def create(self, document: Document) -> Document:
        async with self._sessionmaker() as session:
            row = DocumentModel(
                id=document.id,
                org_id=document.org_id,
                filename=document.filename,
                file_type=document.file_type,
                storage_uri=document.storage_uri,
                schema_json=document.schema_json,
                status=DocumentStatus(document.status).value,
                uploaded_by=document.uploaded_by,
            )
            session.add(row)
            await session.commit()
            await session.refresh(row)
            return _to_entity(row)

    async def get_by_id(self, document_id: UUID) -> Document | None:
        async with self._sessionmaker() as session:
            row = await session.get(DocumentModel, document_id)
            return _to_entity(row) if row is not None else None

    async def list_by_org(self, org_id: str) -> list[Document]:
        async with self._sessionmaker() as session:
            result = await session.execute(
                select(DocumentModel)
                .where(DocumentModel.org_id == org_id)
                .order_by(DocumentModel.created_at)
            )
            return [_to_entity(row) for row in result.scalars().all()]

    async def update_status(self, document_id: UUID, status: DocumentStatus) -> Document:
        async with self._sessionmaker() as session:
            row = await session.get(DocumentModel, document_id)
            if row is None:
                raise DocumentNotFoundError(document_id)
            row.status = DocumentStatus(status).value
            await session.commit()
            await session.refresh(row)
            return _to_entity(row)

    async def delete(self, document_id: UUID) -> None:
        async with self._sessionmaker() as session:
            row = await session.get(DocumentModel, document_id)
            if row is None:
                raise DocumentNotFoundError(document_id)
            await session.delete(row)
            await session.commit()

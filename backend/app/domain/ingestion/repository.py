"""`IDocumentRepository` — the repository abstraction all persistence access
for the document aggregate goes through.

Follows the exact pattern established by `IUserRepository` (STORY-004): a
narrow ABC here, with concrete implementations living in
`app/infrastructure/db/<backend>/`. Business logic and API routers depend on
this interface only — never on `PostgresDocumentRepository`/
`MongoDocumentRepository` directly (Dependency Inversion).

Every method that can return more than one document (`list_by_org`) is scoped
by `org_id` — no query here may cross tenant boundaries.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.ingestion.entities import Document, DocumentStatus


class IDocumentRepository(ABC):
    """Persistence contract for the `Document` aggregate."""

    @abstractmethod
    async def create(self, document: Document) -> Document:
        """Persist a new document and return the stored entity."""

    @abstractmethod
    async def get_by_id(self, document_id: UUID) -> Document | None:
        """Return the document with `document_id`, or `None` if it doesn't exist."""

    @abstractmethod
    async def list_by_org(self, org_id: str) -> list[Document]:
        """Return every document belonging to `org_id`.

        Never returns documents belonging to any other org — every concrete
        implementation must filter by `org_id` at the query level.
        """

    @abstractmethod
    async def update_status(self, document_id: UUID, status: DocumentStatus) -> Document:
        """Update `document_id`'s status and return the stored entity.

        Raises:
            app.domain.ingestion.errors.DocumentNotFoundError: if
                `document_id` doesn't exist.
        """

    @abstractmethod
    async def delete(self, document_id: UUID) -> None:
        """Delete the document with `document_id`.

        Raises:
            app.domain.ingestion.errors.DocumentNotFoundError: if
                `document_id` doesn't exist.
        """

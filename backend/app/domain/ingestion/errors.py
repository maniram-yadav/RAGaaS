"""Domain-level errors for the ingestion module.

Kept in the domain layer (not the Postgres/Mongo infra layers) so callers can
catch a stable exception type regardless of which `IDocumentRepository`
implementation is active (Dependency Inversion / Liskov: every implementation
must raise these, not a driver-specific exception like
`sqlalchemy.exc.IntegrityError`).
"""

from __future__ import annotations

from uuid import UUID


class DocumentNotFoundError(Exception):
    """Raised by `IDocumentRepository.update_status`/`delete` when the
    document id is unknown.
    """

    def __init__(self, document_id: UUID) -> None:
        self.document_id = document_id
        super().__init__(f"No document found with id {document_id!s}")

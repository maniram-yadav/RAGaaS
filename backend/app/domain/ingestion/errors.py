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


class UnsupportedFileTypeError(Exception):
    """Raised when a file's extension isn't allow-listed for upload
    (STORY-010's `validate_upload`), or its content doesn't match what its
    extension claims to be (the "MIME sniff" half of that same check).

    Reused as-is by `LoaderFactory.get_loader()` (STORY-011) for the sibling
    "no loader registered for this extension" condition — both are the same
    underlying domain concept ("this file type isn't supported here").
    """

    def __init__(self, extension: str) -> None:
        self.extension = extension
        super().__init__(f"Unsupported file type: {extension!r}")


class FileTooLargeError(Exception):
    """Raised by `validate_upload` when a file's size exceeds
    `system_config.ingestion.max_upload_size_bytes`.
    """

    def __init__(self, size_bytes: int, max_size_bytes: int) -> None:
        self.size_bytes = size_bytes
        self.max_size_bytes = max_size_bytes
        super().__init__(
            f"File size {size_bytes} bytes exceeds the {max_size_bytes} byte limit"
        )

"""The `Document` domain entity.

Plain-Python dataclass (no ORM/framework dependency) per Dependency Inversion —
`app/domain/**` must be importable without SQLAlchemy, Motor, or any concrete
persistence driver installed. Field shape follows the plan's data model
(§6 "Core data model"): ``Document(id, org_id, filename, file_type,
storage_uri, schema_json[nullable], status, uploaded_by, created_at)``.

``status`` is a `DocumentStatus` (subclasses `str`, mirroring `Role` in
`app.domain.users.entities`) so it round-trips unchanged through the Postgres
`String` column used by `PostgresDocumentRepository` — no migration change is
needed, and callers that compare `status` against a plain string keep
working. ``schema_json`` is a nullable free-form mapping — populated by the
Excel/Csv loaders (STORY-026); every other loader leaves it `None`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class DocumentStatus(str, Enum):
    """Lifecycle status of a `Document` (plan §6; needed by STORY-015/018).

    Subclasses `str` so `DocumentStatus.UPLOADED == "uploaded"` holds — code
    that treats `status` as a plain string (including the Postgres
    `String(32)` column) keeps working unchanged.
    """

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class Document:
    """An uploaded document, independent of how it is persisted."""

    org_id: str
    filename: str
    file_type: str
    storage_uri: str
    uploaded_by: UUID
    id: UUID = field(default_factory=uuid4)
    schema_json: dict[str, Any] | None = None
    status: DocumentStatus = DocumentStatus.UPLOADED
    created_at: datetime = field(default_factory=_utcnow)

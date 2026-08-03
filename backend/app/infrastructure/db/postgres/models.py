"""SQLAlchemy 2.0 async ORM models for the Postgres backend.

`UserModel` is the persistence-layer mapping for `app.domain.users.entities.User`.
`DocumentModel` is the persistence-layer mapping for
`app.domain.ingestion.entities.Document` (STORY-009). Both intentionally live
here (infra), not in `app/domain/**` — the domain layer stays framework-free
(Dependency Inversion). Conversion between an ORM row and its domain entity
happens in the matching `Postgres*Repository`.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.postgres.base import Base


class UserModel(Base):
    """`users` table — mirrors the plan's `User(id, email, hashed_password,
    name, role, org_id, created_at)` entity, plus `updated_at`.
    """

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    # Plain string placeholder for now; STORY-006 introduces the `Role` enum.
    role: Mapped[str] = mapped_column(String(32), nullable=False, server_default="member")
    # Placeholder for the not-yet-built org/tenant model (STORY-006 notes).
    org_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class DocumentModel(Base):
    """`documents` table — mirrors the plan's `Document(id, org_id, filename,
    file_type, storage_uri, schema_json[nullable], status, uploaded_by,
    created_at)` entity (plan §6).
    """

    __tablename__ = "documents"

    id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Not a foreign key: the org/tenant model doesn't exist yet (mirrors
    # `UserModel.org_id`'s placeholder), but every query filters by it.
    org_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    file_type: Mapped[str] = mapped_column(String(64), nullable=False)
    storage_uri: Mapped[str] = mapped_column(String(1024), nullable=False)
    # Populated by the Excel/Csv loaders (STORY-026); every other loader
    # leaves this `NULL`.
    schema_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, server_default="uploaded")
    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

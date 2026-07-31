"""SQLAlchemy 2.0 async ORM models for the Postgres backend.

`UserModel` is the persistence-layer mapping for `app.domain.users.entities.User`.
It intentionally lives here (infra), not in `app/domain/**` — the domain layer
stays framework-free (Dependency Inversion). Conversion between `UserModel` and
`User` happens in `PostgresUserRepository`.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, String, func
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

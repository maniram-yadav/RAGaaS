"""The `User` domain entity.

Plain-Python dataclass (no ORM/framework dependency) per Dependency Inversion —
`app/domain/**` must be importable without SQLAlchemy, Motor, or any concrete
persistence driver installed. Field shape follows the plan's data model
(§4 "Core data model"): ``User(id, email, hashed_password, name, role, org_id,
created_at)``.

``role`` is a `Role` (STORY-006), which subclasses `str` so it round-trips
unchanged through the Postgres/Mongo `String` column used by every concrete
`IUserRepository` — no migration change is needed, and existing callers that
compare `role` against a plain string (e.g. ``user.role == "admin"``) keep
working. ``org_id`` remains a placeholder for the not-yet-built org/tenant
model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from uuid import UUID, uuid4


class Role(str, Enum):
    """RBAC role for a `User` (plan §4: "`User`, `Role`, `Session` models").

    Subclasses `str` so `Role.MEMBER == "member"` holds — code that treats
    `role` as a plain string (including the Postgres `String(32)` column)
    keeps working unchanged.
    """

    ADMIN = "admin"
    MEMBER = "member"
    OWNER = "owner"


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class User:
    """A registered user, independent of how it is persisted."""

    email: str
    hashed_password: str
    name: str
    id: UUID = field(default_factory=uuid4)
    role: Role = Role.MEMBER
    org_id: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

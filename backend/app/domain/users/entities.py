"""The `User` domain entity.

Plain-Python dataclass (no ORM/framework dependency) per Dependency Inversion —
`app/domain/**` must be importable without SQLAlchemy, Motor, or any concrete
persistence driver installed. Field shape follows the plan's data model
(§4 "Core data model"): ``User(id, email, hashed_password, name, role, org_id,
created_at)``.

``role`` is kept as a plain string here (default ``"member"``) rather than an
enum: STORY-006 owns introducing the `Role` enum/RBAC semantics on top of this
placeholder field, per `.claude/rules/story-routing.md`. ``org_id`` is
similarly a placeholder for the not-yet-built org/tenant model.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import UUID, uuid4


def _utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(slots=True)
class User:
    """A registered user, independent of how it is persisted."""

    email: str
    hashed_password: str
    name: str
    id: UUID = field(default_factory=uuid4)
    role: str = "member"
    org_id: str | None = None
    created_at: datetime = field(default_factory=_utcnow)
    updated_at: datetime = field(default_factory=_utcnow)

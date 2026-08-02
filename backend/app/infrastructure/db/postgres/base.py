"""Declarative base shared by every SQLAlchemy 2.0 async ORM model in the
Postgres backend. Every `infrastructure/db/postgres/models.py` (this story
adds `UserModel`; later stories add Document/Conversation/... models) maps
onto this one `Base` so Alembic autogenerate and `Base.metadata.create_all`
see the whole schema.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Shared declarative base for all Postgres ORM models."""

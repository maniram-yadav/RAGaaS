"""`PostgresUserRepository` — the first concrete `IUserRepository`.

Registers itself under the `"postgres"` key in `app.core.repository_factory`'s
registry on import (Open/Closed: `RepositoryFactory` never needs an `if/elif`
branch added for this backend — it just imports this module once, listed in
`_USER_REPOSITORY_MODULES`).
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.repository_factory import register_user_repository
from app.domain.users.entities import User
from app.domain.users.errors import UserAlreadyExistsError, UserNotFoundError
from app.domain.users.repository import IUserRepository
from app.infrastructure.db.postgres.models import UserModel
from app.infrastructure.db.postgres.session import get_postgres_sessionmaker


def _to_entity(row: UserModel) -> User:
    return User(
        id=row.id,
        email=row.email,
        hashed_password=row.hashed_password,
        name=row.name,
        role=row.role,
        org_id=row.org_id,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class PostgresUserRepository(IUserRepository):
    """SQLAlchemy 2.0 async implementation of `IUserRepository` (Postgres)."""

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self._sessionmaker = sessionmaker

    async def create(self, user: User) -> User:
        async with self._sessionmaker() as session:
            row = UserModel(
                id=user.id,
                email=user.email,
                hashed_password=user.hashed_password,
                name=user.name,
                role=user.role,
                org_id=user.org_id,
            )
            session.add(row)
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise UserAlreadyExistsError(user.email) from exc
            await session.refresh(row)
            return _to_entity(row)

    async def get_by_id(self, user_id: UUID) -> User | None:
        async with self._sessionmaker() as session:
            row = await session.get(UserModel, user_id)
            return _to_entity(row) if row is not None else None

    async def get_by_email(self, email: str) -> User | None:
        async with self._sessionmaker() as session:
            result = await session.execute(select(UserModel).where(UserModel.email == email))
            row = result.scalar_one_or_none()
            return _to_entity(row) if row is not None else None

    async def update(self, user: User) -> User:
        async with self._sessionmaker() as session:
            row = await session.get(UserModel, user.id)
            if row is None:
                raise UserNotFoundError(user.id)
            row.email = user.email
            row.hashed_password = user.hashed_password
            row.name = user.name
            row.role = user.role
            row.org_id = user.org_id
            try:
                await session.commit()
            except IntegrityError as exc:
                await session.rollback()
                raise UserAlreadyExistsError(user.email) from exc
            await session.refresh(row)
            return _to_entity(row)

    async def delete(self, user_id: UUID) -> None:
        async with self._sessionmaker() as session:
            row = await session.get(UserModel, user_id)
            if row is None:
                raise UserNotFoundError(user_id)
            await session.delete(row)
            await session.commit()


@register_user_repository("postgres")
def _build_postgres_user_repository() -> IUserRepository:
    """Registry builder used by `RepositoryFactory.get_user_repository()`."""
    return PostgresUserRepository(get_postgres_sessionmaker())

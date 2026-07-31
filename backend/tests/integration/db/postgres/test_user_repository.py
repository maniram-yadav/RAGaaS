"""Integration tests for `PostgresUserRepository` against a real Postgres
(testcontainers) — proves the "CRUD round-trip test passes against a real
Postgres container" acceptance criterion.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.users.entities import User
from app.domain.users.errors import UserAlreadyExistsError, UserNotFoundError
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository


@pytest.fixture
def repo(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> PostgresUserRepository:
    return PostgresUserRepository(postgres_sessionmaker)


@pytest.mark.asyncio
async def test_create_then_get_by_id_round_trip(repo: PostgresUserRepository) -> None:
    user = User(email="alice@example.com", hashed_password="hashed", name="Alice")

    created = await repo.create(user)
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.email == "alice@example.com"
    assert fetched.name == "Alice"
    assert fetched.role == "member"
    assert fetched.org_id is None


@pytest.mark.asyncio
async def test_get_by_email_round_trip(repo: PostgresUserRepository) -> None:
    user = User(email="bob@example.com", hashed_password="hashed", name="Bob")
    await repo.create(user)

    fetched = await repo.get_by_email("bob@example.com")

    assert fetched is not None
    assert fetched.id == user.id


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(repo: PostgresUserRepository) -> None:
    assert await repo.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_get_by_email_returns_none_when_missing(repo: PostgresUserRepository) -> None:
    assert await repo.get_by_email("nobody@example.com") is None


@pytest.mark.asyncio
async def test_create_duplicate_email_raises(repo: PostgresUserRepository) -> None:
    await repo.create(User(email="dup@example.com", hashed_password="a", name="A"))

    with pytest.raises(UserAlreadyExistsError):
        await repo.create(User(email="dup@example.com", hashed_password="b", name="B"))


@pytest.mark.asyncio
async def test_update_round_trip(repo: PostgresUserRepository) -> None:
    user = User(email="carol@example.com", hashed_password="hashed", name="Carol")
    created = await repo.create(user)

    created.name = "Carol Updated"
    created.role = "admin"
    updated = await repo.update(created)

    assert updated.name == "Carol Updated"
    assert updated.role == "admin"

    refetched = await repo.get_by_id(created.id)
    assert refetched is not None
    assert refetched.name == "Carol Updated"
    assert refetched.role == "admin"


@pytest.mark.asyncio
async def test_update_missing_user_raises(repo: PostgresUserRepository) -> None:
    ghost = User(id=uuid4(), email="ghost@example.com", hashed_password="x", name="Ghost")

    with pytest.raises(UserNotFoundError):
        await repo.update(ghost)


@pytest.mark.asyncio
async def test_delete_round_trip(repo: PostgresUserRepository) -> None:
    user = User(email="dave@example.com", hashed_password="hashed", name="Dave")
    created = await repo.create(user)

    await repo.delete(created.id)

    assert await repo.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_delete_missing_user_raises(repo: PostgresUserRepository) -> None:
    with pytest.raises(UserNotFoundError):
        await repo.delete(uuid4())

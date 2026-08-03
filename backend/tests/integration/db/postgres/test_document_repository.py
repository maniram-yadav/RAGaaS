"""Integration tests for `PostgresDocumentRepository` against a real Postgres
(testcontainers) — proves the "CRUD round-trip test passes" acceptance
criterion. Reuses STORY-004's `postgres_sessionmaker` test harness.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain.ingestion.entities import Document, DocumentStatus
from app.domain.ingestion.errors import DocumentNotFoundError
from app.domain.users.entities import User
from app.infrastructure.db.postgres.document_repository import PostgresDocumentRepository
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository


@pytest.fixture
def repo(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> PostgresDocumentRepository:
    return PostgresDocumentRepository(postgres_sessionmaker)


@pytest.fixture
async def uploader_id(
    postgres_sessionmaker: async_sessionmaker[AsyncSession],
) -> object:
    """A real `users.id` to satisfy `documents.uploaded_by`'s foreign key."""
    user_repo = PostgresUserRepository(postgres_sessionmaker)
    user = await user_repo.create(
        User(email=f"uploader-{uuid4()}@example.com", hashed_password="hashed", name="Uploader")
    )
    return user.id


def _make_document(uploaded_by: object, **overrides: object) -> Document:
    defaults: dict[str, object] = {
        "org_id": "org-1",
        "filename": "report.txt",
        "file_type": "text/plain",
        "storage_uri": "file:///tmp/report.txt",
        "uploaded_by": uploaded_by,
    }
    defaults.update(overrides)
    return Document(**defaults)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_create_then_get_by_id_round_trip(
    repo: PostgresDocumentRepository, uploader_id: object
) -> None:
    document = _make_document(uploader_id)

    created = await repo.create(document)
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.id == document.id
    assert fetched.org_id == "org-1"
    assert fetched.filename == "report.txt"
    assert fetched.file_type == "text/plain"
    assert fetched.storage_uri == "file:///tmp/report.txt"
    assert fetched.schema_json is None
    assert fetched.status == DocumentStatus.UPLOADED
    assert fetched.uploaded_by == uploader_id


@pytest.mark.asyncio
async def test_create_persists_schema_json(
    repo: PostgresDocumentRepository, uploader_id: object
) -> None:
    document = _make_document(
        uploader_id, filename="data.csv", file_type="text/csv", schema_json={"columns": ["a", "b"]}
    )

    created = await repo.create(document)
    fetched = await repo.get_by_id(created.id)

    assert fetched is not None
    assert fetched.schema_json == {"columns": ["a", "b"]}


@pytest.mark.asyncio
async def test_get_by_id_returns_none_when_missing(repo: PostgresDocumentRepository) -> None:
    assert await repo.get_by_id(uuid4()) is None


@pytest.mark.asyncio
async def test_list_by_org_returns_only_documents_for_that_org(
    repo: PostgresDocumentRepository, uploader_id: object
) -> None:
    org_a_doc = await repo.create(_make_document(uploader_id, org_id="org-a", filename="a.txt"))
    await repo.create(_make_document(uploader_id, org_id="org-b", filename="b.txt"))

    org_a_documents = await repo.list_by_org("org-a")

    assert [document.id for document in org_a_documents] == [org_a_doc.id]


@pytest.mark.asyncio
async def test_list_by_org_returns_empty_list_for_unknown_org(
    repo: PostgresDocumentRepository,
) -> None:
    assert await repo.list_by_org("no-such-org") == []


@pytest.mark.asyncio
async def test_update_status_round_trip(
    repo: PostgresDocumentRepository, uploader_id: object
) -> None:
    created = await repo.create(_make_document(uploader_id))

    updated = await repo.update_status(created.id, DocumentStatus.PROCESSING)

    assert updated.status == DocumentStatus.PROCESSING

    refetched = await repo.get_by_id(created.id)
    assert refetched is not None
    assert refetched.status == DocumentStatus.PROCESSING


@pytest.mark.asyncio
async def test_update_status_missing_document_raises(repo: PostgresDocumentRepository) -> None:
    with pytest.raises(DocumentNotFoundError):
        await repo.update_status(uuid4(), DocumentStatus.READY)


@pytest.mark.asyncio
async def test_delete_round_trip(repo: PostgresDocumentRepository, uploader_id: object) -> None:
    created = await repo.create(_make_document(uploader_id))

    await repo.delete(created.id)

    assert await repo.get_by_id(created.id) is None


@pytest.mark.asyncio
async def test_delete_missing_document_raises(repo: PostgresDocumentRepository) -> None:
    with pytest.raises(DocumentNotFoundError):
        await repo.delete(uuid4())

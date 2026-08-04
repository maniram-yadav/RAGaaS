"""Integration test for `POST /api/documents/upload` + the CRUD surface
(STORY-010), exercised through the real FastAPI app with `RepositoryFactory`/
`StorageFactory` genuinely resolving to `PostgresDocumentRepository`/
`LocalFsStorage` — real Postgres (testcontainers) for metadata, a per-test
temp directory for the stored bytes, real Redis for the auth token
blacklist.

Only the bootstrap layer (`get_auth_service`, `get_repository_factory`,
`get_storage_factory`, `get_config_service`) is swapped for test infra —
mirroring `tests/integration/auth/test_auth_flow.py` and
`tests/integration/db/postgres/test_repository_factory.py`'s established
approach — the upload router's own business logic and its
`Depends(get_repository_factory)`/`Depends(get_storage_factory)` wiring are
untouched, so this proves the real Dependency-Inversion path end to end.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_auth_service
from app.core.config import ConfigService, get_config_service
from app.core.repository_factory import RepositoryFactory, get_repository_factory
from app.core.settings import get_settings
from app.core.storage_factory import StorageFactory, get_storage_factory
from app.domain.users.auth_service import AuthService
from app.infrastructure.auth.redis_token_blacklist import RedisTokenBlacklist
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository
from app.main import app

#: Kept small so the "oversized" test doesn't need to push megabytes of
#: content through the in-process ASGI transport.
_TEST_MAX_UPLOAD_SIZE_BYTES = 1024


@pytest.fixture
async def client(
    user_repository: PostgresUserRepository,
    token_blacklist: RedisTokenBlacklist,
    fresh_postgres_sessionmaker_cache: None,
    tmp_path: Path,
) -> AsyncIterator[AsyncClient]:
    auth_service = AuthService(user_repository, token_blacklist)
    fixed_settings = get_settings().model_copy(
        update={
            "local_storage_base_path": str(tmp_path),
            "ingestion_max_upload_size_bytes": _TEST_MAX_UPLOAD_SIZE_BYTES,
        }
    )
    fixed_config_service = ConfigService(collection=None, settings=fixed_settings)

    app.dependency_overrides[get_auth_service] = lambda: auth_service
    app.dependency_overrides[get_repository_factory] = lambda: RepositoryFactory(
        config_service=fixed_config_service
    )
    app.dependency_overrides[get_storage_factory] = lambda: StorageFactory(
        config_service=fixed_config_service
    )
    app.dependency_overrides[get_config_service] = lambda: fixed_config_service

    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        for dependency in (
            get_auth_service,
            get_repository_factory,
            get_storage_factory,
            get_config_service,
        ):
            app.dependency_overrides.pop(dependency, None)


async def _signup_and_login(client: AsyncClient, email: str) -> str:
    signup_response = await client.post(
        "/api/auth/signup",
        json={"email": email, "password": "s3cret!!!", "name": "Uploader"},
    )
    assert signup_response.status_code == 201, signup_response.text

    login_response = await client.post(
        "/api/auth/login", data={"username": email, "password": "s3cret!!!"}
    )
    assert login_response.status_code == 200, login_response.text
    return str(login_response.json()["access_token"])


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.mark.asyncio
async def test_upload_then_get_by_id_round_trip(client: AsyncClient) -> None:
    """The story's headline acceptance criterion, end to end."""
    token = await _signup_and_login(client, "uploader@example.com")

    upload_response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token),
        files={"file": ("report.txt", b"hello world", "text/plain")},
    )

    assert upload_response.status_code == 201, upload_response.text
    body = upload_response.json()
    assert body["filename"] == "report.txt"
    assert body["file_type"] == ".txt"
    assert body["status"] == "uploaded"

    get_response = await client.get(f"/api/documents/{body['id']}", headers=_auth_headers(token))

    assert get_response.status_code == 200
    assert get_response.json()["id"] == body["id"]


@pytest.mark.asyncio
async def test_upload_rejects_a_disallowed_file_type(client: AsyncClient) -> None:
    token = await _signup_and_login(client, "badtype@example.com")

    response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token),
        files={"file": ("virus.exe", b"MZ\x90\x00", "application/octet-stream")},
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_content_that_does_not_match_its_extension(
    client: AsyncClient,
) -> None:
    token = await _signup_and_login(client, "spoofed@example.com")

    response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token),
        files={"file": ("fake.pdf", b"not actually a pdf", "application/pdf")},
    )

    assert response.status_code == 415


@pytest.mark.asyncio
async def test_upload_rejects_an_oversized_file(client: AsyncClient) -> None:
    token = await _signup_and_login(client, "toobig@example.com")
    oversized_content = b"a" * (_TEST_MAX_UPLOAD_SIZE_BYTES * 2)

    response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token),
        files={"file": ("big.txt", oversized_content, "text/plain")},
    )

    assert response.status_code == 413


@pytest.mark.asyncio
async def test_upload_requires_authentication(client: AsyncClient) -> None:
    response = await client.post(
        "/api/documents/upload", files={"file": ("no-auth.txt", b"x", "text/plain")}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_documents_is_scoped_to_the_caller(client: AsyncClient) -> None:
    token_a = await _signup_and_login(client, "org-a@example.com")
    token_b = await _signup_and_login(client, "org-b@example.com")

    await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token_a),
        files={"file": ("a.txt", b"a doc", "text/plain")},
    )

    response_b = await client.get("/api/documents", headers=_auth_headers(token_b))

    assert response_b.status_code == 200
    assert response_b.json() == []


@pytest.mark.asyncio
async def test_get_another_users_document_404s(client: AsyncClient) -> None:
    token_owner = await _signup_and_login(client, "owner@example.com")
    token_stranger = await _signup_and_login(client, "stranger@example.com")

    upload_response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token_owner),
        files={"file": ("secret.txt", b"secret", "text/plain")},
    )
    document_id = upload_response.json()["id"]

    response = await client.get(
        f"/api/documents/{document_id}", headers=_auth_headers(token_stranger)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_another_users_document_404s(client: AsyncClient) -> None:
    token_owner = await _signup_and_login(client, "owner2@example.com")
    token_stranger = await _signup_and_login(client, "stranger2@example.com")

    upload_response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token_owner),
        files={"file": ("secret2.txt", b"secret", "text/plain")},
    )
    document_id = upload_response.json()["id"]

    response = await client.delete(
        f"/api/documents/{document_id}", headers=_auth_headers(token_stranger)
    )

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_then_get_404s(client: AsyncClient) -> None:
    token = await _signup_and_login(client, "deleter@example.com")

    upload_response = await client.post(
        "/api/documents/upload",
        headers=_auth_headers(token),
        files={"file": ("d.txt", b"bye", "text/plain")},
    )
    document_id = upload_response.json()["id"]

    delete_response = await client.delete(
        f"/api/documents/{document_id}", headers=_auth_headers(token)
    )
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/documents/{document_id}", headers=_auth_headers(token))
    assert get_response.status_code == 404


@pytest.mark.asyncio
async def test_get_unknown_document_id_404s(client: AsyncClient) -> None:
    token = await _signup_and_login(client, "noexist@example.com")

    response = await client.get(
        "/api/documents/00000000-0000-0000-0000-000000000000", headers=_auth_headers(token)
    )

    assert response.status_code == 404

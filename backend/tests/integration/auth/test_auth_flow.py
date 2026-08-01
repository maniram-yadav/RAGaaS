"""Integration test for the full auth flow against real Postgres + real Redis
(STORY-006's headline acceptance criterion): signup -> login -> authenticated
`/api/me` -> refresh, plus the story's other required proofs (duplicate-email
signup rejection, wrong-password login rejection, refresh rotation, and
expired/blacklisted token rejection).

Exercises the real FastAPI app/routers via an in-process ASGI transport, with
only `get_auth_service` overridden to use containers instead of the process-
wide (Mongo-backed) singletons — mirroring
`tests/integration/db/postgres/test_repository_factory.py`'s approach of
sidestepping `ConfigService`'s Mongo dependency for a test that isn't about
config resolution itself.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from uuid import UUID

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_auth_service
from app.core.security import TokenType, create_access_token, decode_token
from app.core.settings import get_settings
from app.domain.users.auth_service import AuthService
from app.infrastructure.auth.redis_token_blacklist import RedisTokenBlacklist
from app.infrastructure.db.postgres.user_repository import PostgresUserRepository
from app.main import app


@pytest.fixture
async def client(
    user_repository: PostgresUserRepository, token_blacklist: RedisTokenBlacklist
) -> AsyncIterator[AsyncClient]:
    service = AuthService(user_repository, token_blacklist)
    app.dependency_overrides[get_auth_service] = lambda: service
    transport = ASGITransport(app=app)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac
    finally:
        app.dependency_overrides.pop(get_auth_service, None)


async def _signup(client: AsyncClient, email: str, password: str = "s3cret!!!") -> dict:
    response = await client.post(
        "/api/auth/signup", json={"email": email, "password": password, "name": "Flow User"}
    )
    assert response.status_code == 201, response.text
    return response.json()


async def _login(client: AsyncClient, email: str, password: str = "s3cret!!!") -> dict:
    response = await client.post(
        "/api/auth/login", data={"username": email, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.asyncio
async def test_full_signup_login_me_refresh_flow(client: AsyncClient) -> None:
    """The story's headline acceptance criterion, end to end."""
    signed_up = await _signup(client, "flow@example.com")
    assert signed_up["email"] == "flow@example.com"
    assert "hashed_password" not in signed_up

    tokens = await _login(client, "flow@example.com")
    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]

    me_response = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {access_token}"}
    )
    assert me_response.status_code == 200
    assert me_response.json()["email"] == "flow@example.com"

    refresh_response = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert refresh_response.status_code == 200
    rotated = refresh_response.json()
    assert rotated["refresh_token"] != refresh_token
    assert rotated["access_token"] != access_token

    # Rotation: the just-used refresh token must now be rejected on reuse.
    reuse_response = await client.post(
        "/api/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert reuse_response.status_code == 401


@pytest.mark.asyncio
async def test_signup_rejects_a_duplicate_email(client: AsyncClient) -> None:
    await _signup(client, "dup@example.com")

    response = await client.post(
        "/api/auth/signup",
        json={"email": "dup@example.com", "password": "different-pw1", "name": "Dup"},
    )

    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_rejects_the_wrong_password(client: AsyncClient) -> None:
    await _signup(client, "wrongpw@example.com")

    response = await client.post(
        "/api/auth/login",
        data={"username": "wrongpw@example.com", "password": "not-the-password"},
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_logout_blacklists_the_refresh_token(client: AsyncClient) -> None:
    await _signup(client, "logout@example.com")
    tokens = await _login(client, "logout@example.com")

    logout_response = await client.post(
        "/api/auth/logout", json={"refresh_token": tokens["refresh_token"]}
    )
    assert logout_response.status_code == 204

    reuse_response = await client.post(
        "/api/auth/refresh", json={"refresh_token": tokens["refresh_token"]}
    )
    assert reuse_response.status_code == 401


@pytest.mark.asyncio
async def test_expired_access_token_is_rejected_by_me(client: AsyncClient) -> None:
    signed_up = await _signup(client, "expired@example.com")

    settings = get_settings()
    expired_settings = settings.model_copy(update={"jwt_access_token_expire_minutes": -1})
    expired_token = create_access_token(
        expired_settings, subject=UUID(signed_up["id"]), role="member", org_id=None
    )

    response = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {expired_token}"}
    )

    assert response.status_code == 401


@pytest.mark.asyncio
async def test_blacklisted_access_token_is_rejected_by_me(
    client: AsyncClient, token_blacklist: RedisTokenBlacklist
) -> None:
    """A token whose `jti` has been revoked (e.g. by a future admin-forced
    logout) must be rejected even though it hasn't naturally expired yet.

    `token_blacklist` talks to the same real Redis instance the app's
    overridden `AuthService` uses (both are built from the module-scoped
    `redis_container` via `_infra_env`), so a write through one is visible
    through the other.
    """
    signed_up = await _signup(client, "blacklisted@example.com")
    tokens = await _login(client, "blacklisted@example.com")

    settings = get_settings()
    payload = decode_token(settings, tokens["access_token"], expected_type=TokenType.ACCESS)
    assert str(payload.sub) == signed_up["id"]

    # Simulate revocation the same way `AuthService.logout` would for a
    # refresh token, but directly against the access token's jti.
    await token_blacklist.blacklist(payload.jti, 3600)

    response = await client.get(
        "/api/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert response.status_code == 401

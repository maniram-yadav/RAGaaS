"""Unit tests for `AuthService`, against an in-memory fake `IUserRepository`
and a fake token blacklist (no real Postgres/Redis) — the real-infra proof
lives in `tests/integration/auth/test_auth_flow.py`.
"""

from __future__ import annotations

from uuid import UUID

import pytest

from app.core.security import TokenType, decode_token
from app.core.settings import Settings
from app.domain.users.auth_service import AuthService
from app.domain.users.entities import Role, User
from app.domain.users.errors import (
    InvalidCredentialsError,
    TokenRejectedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


class _FakeUserRepository:
    """In-memory stand-in satisfying `IUserRepository`'s shape."""

    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}

    async def create(self, user: User) -> User:
        if any(existing.email == user.email for existing in self._by_id.values()):
            raise UserAlreadyExistsError(user.email)
        self._by_id[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    async def update(self, user: User) -> User:
        if user.id not in self._by_id:
            raise UserNotFoundError(user.id)
        self._by_id[user.id] = user
        return user

    async def delete(self, user_id: UUID) -> None:
        if user_id not in self._by_id:
            raise UserNotFoundError(user_id)
        del self._by_id[user_id]


class _FakeTokenBlacklist:
    """In-memory stand-in for `RedisTokenBlacklist`."""

    def __init__(self) -> None:
        self._jtis: set[str] = set()

    async def blacklist(self, jti: str, ttl_seconds: int) -> None:
        self._jtis.add(jti)

    async def is_blacklisted(self, jti: str) -> bool:
        return jti in self._jtis


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "app_secret_key": "unit-test-secret",
        "jwt_algorithm": "HS256",
        "jwt_access_token_expire_minutes": 15,
        "jwt_refresh_token_expire_days": 30,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


def _service(**setting_overrides: object) -> tuple[AuthService, _FakeUserRepository]:
    repo = _FakeUserRepository()
    service = AuthService(repo, _FakeTokenBlacklist(), settings=_settings(**setting_overrides))
    return service, repo


# --- signup ---


@pytest.mark.asyncio
async def test_signup_creates_a_user_with_a_hashed_password_and_member_role() -> None:
    service, _ = _service()

    user = await service.signup(email="a@example.com", password="s3cret!!", name="Ann")

    assert user.email == "a@example.com"
    assert user.hashed_password != "s3cret!!"
    assert user.role == Role.MEMBER


@pytest.mark.asyncio
async def test_signup_rejects_a_duplicate_email() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")

    with pytest.raises(UserAlreadyExistsError):
        await service.signup(email="a@example.com", password="different1", name="Ann2")


# --- login ---


@pytest.mark.asyncio
async def test_login_rejects_wrong_password() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="a@example.com", password="wrong-password")


@pytest.mark.asyncio
async def test_login_rejects_unknown_email() -> None:
    service, _ = _service()

    with pytest.raises(InvalidCredentialsError):
        await service.login(email="nobody@example.com", password="anything1")


@pytest.mark.asyncio
async def test_login_issues_a_working_token_pair() -> None:
    service, _ = _service()
    user = await service.signup(email="a@example.com", password="s3cret!!", name="Ann")

    pair = await service.login(email="a@example.com", password="s3cret!!")
    resolved = await service.get_current_user(pair.access_token)

    assert resolved.id == user.id


# --- get_current_user ---


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_refresh_token() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")

    with pytest.raises(TokenRejectedError):
        await service.get_current_user(pair.refresh_token)


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_token_for_a_deleted_user() -> None:
    service, repo = _service()
    user = await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")
    await repo.delete(user.id)

    with pytest.raises(TokenRejectedError):
        await service.get_current_user(pair.access_token)


# --- refresh (rotation) ---


@pytest.mark.asyncio
async def test_refresh_issues_a_new_pair_and_blacklists_the_old_refresh_token() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    original = await service.login(email="a@example.com", password="s3cret!!")

    rotated = await service.refresh(original.refresh_token)

    assert rotated.refresh_token != original.refresh_token
    assert rotated.access_token != original.access_token
    # Rotation: the old refresh token must be rejected on reuse.
    with pytest.raises(TokenRejectedError):
        await service.refresh(original.refresh_token)


@pytest.mark.asyncio
async def test_refresh_rejects_an_access_token() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")

    with pytest.raises(TokenRejectedError):
        await service.refresh(pair.access_token)


@pytest.mark.asyncio
async def test_refresh_rejects_an_expired_refresh_token() -> None:
    service, _ = _service(jwt_refresh_token_expire_days=-1)
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")

    with pytest.raises(TokenRejectedError):
        await service.refresh(pair.refresh_token)


# --- logout (blacklist) ---


@pytest.mark.asyncio
async def test_logout_blacklists_the_refresh_token() -> None:
    service, _ = _service()
    await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")

    await service.logout(pair.refresh_token)

    with pytest.raises(TokenRejectedError):
        await service.refresh(pair.refresh_token)


@pytest.mark.asyncio
async def test_get_current_user_rejects_a_blacklisted_access_token() -> None:
    settings = _settings()
    repo = _FakeUserRepository()
    blacklist = _FakeTokenBlacklist()
    service = AuthService(repo, blacklist, settings=settings)
    user = await service.signup(email="a@example.com", password="s3cret!!", name="Ann")
    pair = await service.login(email="a@example.com", password="s3cret!!")
    payload = decode_token(settings, pair.access_token, expected_type=TokenType.ACCESS)
    await blacklist.blacklist(payload.jti, 3600)

    with pytest.raises(TokenRejectedError):
        await service.get_current_user(pair.access_token)

    # Sanity: the user itself is untouched by blacklisting its token.
    assert (await repo.get_by_id(user.id)) is not None

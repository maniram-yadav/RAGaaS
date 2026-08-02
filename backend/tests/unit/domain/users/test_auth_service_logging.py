"""Acceptance criterion: "Passwords never appear in logs" (STORY-006).

Captures every `structlog` event emitted by `AuthService.signup`/`login`
(including the rejected-login path) and asserts the plaintext password never
appears anywhere in the captured log records.
"""

from __future__ import annotations

from uuid import UUID

from structlog.testing import capture_logs

from app.core.settings import Settings
from app.domain.users.auth_service import AuthService
from app.domain.users.entities import User
from app.domain.users.errors import InvalidCredentialsError

_PASSWORD = "sup3r-s3cret-p4ssw0rd!"


class _FakeUserRepository:
    def __init__(self) -> None:
        self._by_id: dict[UUID, User] = {}

    async def create(self, user: User) -> User:
        self._by_id[user.id] = user
        return user

    async def get_by_id(self, user_id: UUID) -> User | None:
        return self._by_id.get(user_id)

    async def get_by_email(self, email: str) -> User | None:
        return next((u for u in self._by_id.values() if u.email == email), None)

    async def update(self, user: User) -> User:
        self._by_id[user.id] = user
        return user

    async def delete(self, user_id: UUID) -> None:
        del self._by_id[user_id]


class _FakeTokenBlacklist:
    async def blacklist(self, jti: str, ttl_seconds: int) -> None:
        return None

    async def is_blacklisted(self, jti: str) -> bool:
        return False


def _assert_password_absent(events: list[dict[str, object]]) -> None:
    for event in events:
        for value in event.values():
            assert _PASSWORD not in str(value), f"password leaked into log event: {event}"


async def test_signup_and_login_never_log_the_plaintext_password() -> None:
    settings = Settings(_env_file=None, app_secret_key="unit-test-secret")
    service = AuthService(_FakeUserRepository(), _FakeTokenBlacklist(), settings=settings)

    with capture_logs() as logs:
        await service.signup(email="a@example.com", password=_PASSWORD, name="Ann")
        await service.login(email="a@example.com", password=_PASSWORD)

    assert len(logs) >= 2  # signup + login events were actually captured
    _assert_password_absent(logs)


async def test_rejected_login_never_logs_the_attempted_password() -> None:
    settings = Settings(_env_file=None, app_secret_key="unit-test-secret")
    service = AuthService(_FakeUserRepository(), _FakeTokenBlacklist(), settings=settings)
    await service.signup(email="a@example.com", password=_PASSWORD, name="Ann")

    with capture_logs() as logs:
        try:
            await service.login(email="a@example.com", password="wrong-password-attempt")
        except InvalidCredentialsError:
            pass

    assert len(logs) >= 1
    _assert_password_absent(logs)
    for event in logs:
        assert "wrong-password-attempt" not in str(event)

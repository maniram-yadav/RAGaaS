"""`AuthService` — signup/login/refresh/logout business logic (STORY-006).

Design pattern: Dependency Inversion. The service's only dependency on
persistence is `IUserRepository` (STORY-004) — it never touches SQLAlchemy/
Motor directly, and API routers never touch `IUserRepository` directly either
(they go through this service). The JWT/password-hashing helpers in
`app.core.security` are treated as stable library calls, not swappable
strategies, so they're imported directly rather than hidden behind another
interface (per `.claude/rules/coding-standards.md`'s Interface Segregation
guidance — don't add an abstraction the story doesn't need).

`_TokenBlacklistPort` is a narrow `typing.Protocol` (structural typing, not a
registered domain contract) purely so this service can be unit-tested against
an in-memory fake instead of real Redis — it is not meant to be a second
swappable "backend" the way `IUserRepository`/`IStorageService` are, so it
gets no factory/registry of its own.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Protocol

import structlog

from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    TokenPair,
    TokenPayload,
    TokenType,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.settings import Settings, get_settings
from app.domain.users.entities import Role, User
from app.domain.users.errors import (
    InvalidCredentialsError,
    TokenRejectedError,
)
from app.domain.users.repository import IUserRepository

logger = structlog.get_logger(__name__)


class _TokenBlacklistPort(Protocol):
    """The narrow shape `AuthService` needs from a JWT revocation store."""

    async def blacklist(self, jti: str, ttl_seconds: int) -> None: ...

    async def is_blacklisted(self, jti: str) -> bool: ...


class AuthService:
    """Signup/login/refresh/logout, and access-token -> `User` resolution."""

    def __init__(
        self,
        user_repository: IUserRepository,
        blacklist: _TokenBlacklistPort,
        settings: Settings | None = None,
    ) -> None:
        self._users = user_repository
        self._blacklist = blacklist
        self._settings = settings or get_settings()

    async def signup(self, *, email: str, password: str, name: str) -> User:
        """Create a new `User` with a bcrypt-hashed password.

        Raises:
            app.domain.users.errors.UserAlreadyExistsError: if `email` is
                already registered.
        """
        user = User(
            email=email,
            hashed_password=hash_password(password),
            name=name,
            role=Role.MEMBER,
        )
        created = await self._users.create(user)
        logger.info("auth.signup", user_id=str(created.id), email=created.email)
        return created

    async def authenticate(self, *, email: str, password: str) -> User:
        """Verify `email`/`password`, returning the matching `User`.

        Raises:
            app.domain.users.errors.InvalidCredentialsError: on unknown email
                or a password mismatch. Deliberately the same error either
                way, so callers can't enumerate registered emails.
        """
        user = await self._users.get_by_email(email)
        if user is None or not verify_password(password, user.hashed_password):
            logger.info("auth.login.rejected", email=email)
            raise InvalidCredentialsError
        return user

    async def login(self, *, email: str, password: str) -> TokenPair:
        """Authenticate and issue a fresh access+refresh `TokenPair`."""
        user = await self.authenticate(email=email, password=password)
        pair = create_token_pair(
            self._settings, subject=user.id, role=str(user.role), org_id=user.org_id
        )
        logger.info("auth.login", user_id=str(user.id))
        return pair

    async def refresh(self, refresh_token: str) -> TokenPair:
        """Rotate `refresh_token`: blacklist it and issue a brand-new pair.

        Raises:
            app.domain.users.errors.TokenRejectedError: if the token is
                expired, malformed, the wrong type, already blacklisted, or
                its subject no longer exists.
        """
        payload = self._decode(refresh_token, expected_type=TokenType.REFRESH)
        if await self._blacklist.is_blacklisted(payload.jti):
            raise TokenRejectedError("Refresh token has already been used or revoked")

        user = await self._users.get_by_id(payload.sub)
        if user is None:
            raise TokenRejectedError("Token subject no longer exists")

        await self._revoke(payload)
        pair = create_token_pair(
            self._settings, subject=user.id, role=str(user.role), org_id=user.org_id
        )
        logger.info("auth.refresh", user_id=str(user.id))
        return pair

    async def logout(self, refresh_token: str) -> None:
        """Blacklist `refresh_token` so it can no longer be used to refresh.

        Raises:
            app.domain.users.errors.TokenRejectedError: if the token is
                expired, malformed, or the wrong type.
        """
        payload = self._decode(refresh_token, expected_type=TokenType.REFRESH)
        await self._revoke(payload)
        logger.info("auth.logout", user_id=str(payload.sub))

    async def get_current_user(self, access_token: str) -> User:
        """Resolve `access_token` to its `User` — the `get_current_user` dependency's logic.

        Raises:
            app.domain.users.errors.TokenRejectedError: if the token is
                expired, malformed, the wrong type, blacklisted, or its
                subject no longer exists.
        """
        payload = self._decode(access_token, expected_type=TokenType.ACCESS)
        if await self._blacklist.is_blacklisted(payload.jti):
            raise TokenRejectedError("Access token has been revoked")

        user = await self._users.get_by_id(payload.sub)
        if user is None:
            raise TokenRejectedError("Token subject no longer exists")
        return user

    def _decode(self, token: str, *, expected_type: TokenType) -> TokenPayload:
        """Decode `token`, translating `app.core.security` errors to the
        domain-stable `TokenRejectedError`.
        """
        try:
            return decode_token(self._settings, token, expected_type=expected_type)
        except TokenExpiredError as exc:
            raise TokenRejectedError("Token has expired") from exc
        except InvalidTokenError as exc:
            raise TokenRejectedError("Token is invalid") from exc

    async def _revoke(self, payload: TokenPayload) -> None:
        ttl_seconds = int((payload.exp - datetime.now(UTC)).total_seconds())
        await self._blacklist.blacklist(payload.jti, max(ttl_seconds, 1))

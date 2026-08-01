"""Password hashing and JWT encode/decode primitives (plan §8: `app/core/` —
"config loader, security, DI container").

Kept as pure, framework-free functions parameterized by `Settings` so
`app.domain.users.auth_service.AuthService` can depend on them directly
without pulling FastAPI/Starlette into the domain layer. The only *volatile*
collaborator `AuthService` depends on as an interface is `IUserRepository`
(Dependency Inversion, per this story's design pattern) — hashing/JWT-signing
algorithms are treated as stable library calls, not swappable strategies.

Secrets (`Settings.app_secret_key`) are read from the bootstrap env-var layer
only, never from `system_config` (`.claude/rules/config-management.md`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.settings import Settings

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """Hash `password` with bcrypt (via passlib). Never log the input or output."""
    return _pwd_context.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    """Return whether `password` matches `hashed_password`."""
    return _pwd_context.verify(password, hashed_password)


class TokenType(str, Enum):
    """Discriminates access vs. refresh JWTs so one can never be used as the other."""

    ACCESS = "access"
    REFRESH = "refresh"


class InvalidTokenError(Exception):
    """Raised when a JWT is malformed, has a bad signature, or the wrong `type` claim."""


class TokenExpiredError(Exception):
    """Raised when a JWT's `exp` claim is in the past."""


@dataclass(frozen=True, slots=True)
class TokenPayload:
    """Decoded, validated claims of an access or refresh JWT."""

    sub: UUID
    role: str
    org_id: str | None
    jti: str
    token_type: TokenType
    exp: datetime


@dataclass(frozen=True, slots=True)
class TokenPair:
    """An issued access + refresh token pair, ready to return from an endpoint."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _encode(
    *,
    settings: Settings,
    subject: UUID,
    role: str,
    org_id: str | None,
    token_type: TokenType,
    expires_delta: timedelta,
    jti: str | None = None,
) -> tuple[str, str]:
    """Encode a JWT; returns `(token, jti)`."""
    now = datetime.now(UTC)
    resolved_jti = jti or str(uuid4())
    claims: dict[str, Any] = {
        "sub": str(subject),
        "role": role,
        "org_id": org_id,
        "type": token_type.value,
        "jti": resolved_jti,
        "iat": now,
        "exp": now + expires_delta,
    }
    token = jwt.encode(claims, settings.app_secret_key, algorithm=settings.jwt_algorithm)
    return token, resolved_jti


def create_access_token(
    settings: Settings, *, subject: UUID, role: str, org_id: str | None
) -> str:
    """Issue a short-lived access JWT."""
    token, _ = _encode(
        settings=settings,
        subject=subject,
        role=role,
        org_id=org_id,
        token_type=TokenType.ACCESS,
        expires_delta=timedelta(minutes=settings.jwt_access_token_expire_minutes),
    )
    return token


def create_refresh_token(
    settings: Settings, *, subject: UUID, role: str, org_id: str | None
) -> str:
    """Issue a long-lived refresh JWT."""
    token, _ = _encode(
        settings=settings,
        subject=subject,
        role=role,
        org_id=org_id,
        token_type=TokenType.REFRESH,
        expires_delta=timedelta(days=settings.jwt_refresh_token_expire_days),
    )
    return token


def create_token_pair(
    settings: Settings, *, subject: UUID, role: str, org_id: str | None
) -> TokenPair:
    """Issue a fresh access+refresh `TokenPair` for `subject`."""
    return TokenPair(
        access_token=create_access_token(settings, subject=subject, role=role, org_id=org_id),
        refresh_token=create_refresh_token(settings, subject=subject, role=role, org_id=org_id),
    )


def decode_token(settings: Settings, token: str, *, expected_type: TokenType) -> TokenPayload:
    """Decode and validate `token`, asserting it is a `expected_type` token.

    Raises:
        TokenExpiredError: if `exp` is in the past.
        InvalidTokenError: if the signature/shape is invalid, or `type` claim
            doesn't match `expected_type` (e.g. an access token presented
            where a refresh token is required, or vice versa).
    """
    try:
        claims = jwt.decode(token, settings.app_secret_key, algorithms=[settings.jwt_algorithm])
    except jwt.ExpiredSignatureError as exc:
        raise TokenExpiredError("Token has expired") from exc
    except JWTError as exc:
        raise InvalidTokenError("Token is malformed or has an invalid signature") from exc

    token_type_claim = claims.get("type")
    if token_type_claim != expected_type.value:
        raise InvalidTokenError(
            f"Expected a {expected_type.value!r} token, got {token_type_claim!r}"
        )

    try:
        return TokenPayload(
            sub=UUID(claims["sub"]),
            role=claims["role"],
            org_id=claims.get("org_id"),
            jti=claims["jti"],
            token_type=TokenType(token_type_claim),
            exp=datetime.fromtimestamp(claims["exp"], tz=UTC),
        )
    except (KeyError, ValueError) as exc:
        raise InvalidTokenError("Token is missing required claims") from exc

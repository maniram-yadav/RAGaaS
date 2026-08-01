"""Unit tests for `app.core.security` — password hashing and JWT primitives."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.core.security import (
    InvalidTokenError,
    TokenExpiredError,
    TokenType,
    create_access_token,
    create_refresh_token,
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from app.core.settings import Settings


def _settings(**overrides: object) -> Settings:
    defaults: dict[str, object] = {
        "app_secret_key": "unit-test-secret",
        "jwt_algorithm": "HS256",
        "jwt_access_token_expire_minutes": 15,
        "jwt_refresh_token_expire_days": 30,
    }
    defaults.update(overrides)
    return Settings(_env_file=None, **defaults)  # type: ignore[arg-type]


# --- password hashing ---


def test_hash_password_does_not_return_the_plaintext() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed != "correct horse battery staple"


def test_verify_password_accepts_the_correct_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("correct horse battery staple", hashed) is True


def test_verify_password_rejects_the_wrong_password() -> None:
    hashed = hash_password("correct horse battery staple")

    assert verify_password("wrong password", hashed) is False


# --- JWT issuance/decoding ---


def test_access_token_round_trips_through_decode() -> None:
    settings = _settings()
    user_id = uuid4()

    token = create_access_token(settings, subject=user_id, role="member", org_id="org-1")
    payload = decode_token(settings, token, expected_type=TokenType.ACCESS)

    assert payload.sub == user_id
    assert payload.role == "member"
    assert payload.org_id == "org-1"
    assert payload.token_type == TokenType.ACCESS


def test_refresh_token_round_trips_through_decode() -> None:
    settings = _settings()
    user_id = uuid4()

    token = create_refresh_token(settings, subject=user_id, role="admin", org_id=None)
    payload = decode_token(settings, token, expected_type=TokenType.REFRESH)

    assert payload.sub == user_id
    assert payload.role == "admin"
    assert payload.org_id is None
    assert payload.token_type == TokenType.REFRESH


def test_create_token_pair_returns_distinct_access_and_refresh_tokens() -> None:
    settings = _settings()
    pair = create_token_pair(settings, subject=uuid4(), role="member", org_id=None)

    assert pair.access_token != pair.refresh_token
    assert pair.token_type == "bearer"


def test_decode_rejects_an_access_token_presented_as_a_refresh_token() -> None:
    settings = _settings()
    token = create_access_token(settings, subject=uuid4(), role="member", org_id=None)

    with pytest.raises(InvalidTokenError):
        decode_token(settings, token, expected_type=TokenType.REFRESH)


def test_decode_rejects_a_refresh_token_presented_as_an_access_token() -> None:
    settings = _settings()
    token = create_refresh_token(settings, subject=uuid4(), role="member", org_id=None)

    with pytest.raises(InvalidTokenError):
        decode_token(settings, token, expected_type=TokenType.ACCESS)


def test_decode_rejects_a_malformed_token() -> None:
    settings = _settings()

    with pytest.raises(InvalidTokenError):
        decode_token(settings, "not-a-jwt", expected_type=TokenType.ACCESS)


def test_decode_rejects_a_token_signed_with_a_different_secret() -> None:
    settings = _settings()
    other_settings = _settings(app_secret_key="a-different-secret")
    token = create_access_token(settings, subject=uuid4(), role="member", org_id=None)

    with pytest.raises(InvalidTokenError):
        decode_token(other_settings, token, expected_type=TokenType.ACCESS)


def test_decode_rejects_an_expired_token() -> None:
    settings = _settings(jwt_access_token_expire_minutes=-1)
    token = create_access_token(settings, subject=uuid4(), role="member", org_id=None)

    with pytest.raises(TokenExpiredError):
        decode_token(settings, token, expected_type=TokenType.ACCESS)

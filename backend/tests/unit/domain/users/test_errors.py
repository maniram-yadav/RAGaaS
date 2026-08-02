"""Unit tests for the users domain error types."""

from __future__ import annotations

from uuid import uuid4

from app.domain.users.errors import (
    InvalidCredentialsError,
    TokenRejectedError,
    UserAlreadyExistsError,
    UserNotFoundError,
)


def test_user_already_exists_error_carries_the_email() -> None:
    error = UserAlreadyExistsError("dup@example.com")

    assert error.email == "dup@example.com"
    assert "dup@example.com" in str(error)


def test_user_not_found_error_carries_the_user_id() -> None:
    user_id = uuid4()
    error = UserNotFoundError(user_id)

    assert error.user_id == user_id
    assert str(user_id) in str(error)


def test_invalid_credentials_error_message_does_not_echo_input() -> None:
    error = InvalidCredentialsError()

    assert str(error) == "Invalid email or password"


def test_token_rejected_error_carries_a_reason_message() -> None:
    error = TokenRejectedError("Token has expired")

    assert str(error) == "Token has expired"

"""Unit tests for the users domain error types."""

from __future__ import annotations

from uuid import uuid4

from app.domain.users.errors import UserAlreadyExistsError, UserNotFoundError


def test_user_already_exists_error_carries_the_email() -> None:
    error = UserAlreadyExistsError("dup@example.com")

    assert error.email == "dup@example.com"
    assert "dup@example.com" in str(error)


def test_user_not_found_error_carries_the_user_id() -> None:
    user_id = uuid4()
    error = UserNotFoundError(user_id)

    assert error.user_id == user_id
    assert str(user_id) in str(error)

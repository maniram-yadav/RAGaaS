"""Domain-level errors for the users module.

Kept in the domain layer (not the Postgres/Mongo infra layers) so callers can
catch a stable exception type regardless of which `IUserRepository`
implementation is active (Dependency Inversion / Liskov: every implementation
must raise these, not a driver-specific exception like
`sqlalchemy.exc.IntegrityError`).
"""

from __future__ import annotations

from uuid import UUID


class UserAlreadyExistsError(Exception):
    """Raised by `IUserRepository.create`/`update` on a duplicate email."""

    def __init__(self, email: str) -> None:
        self.email = email
        super().__init__(f"A user with email {email!r} already exists")


class UserNotFoundError(Exception):
    """Raised by `IUserRepository.update`/`delete` when the user id is unknown."""

    def __init__(self, user_id: UUID) -> None:
        self.user_id = user_id
        super().__init__(f"No user found with id {user_id!s}")


class InvalidCredentialsError(Exception):
    """Raised by `AuthService.login` on an unknown email or wrong password.

    Deliberately not `UserNotFoundError` (STORY-006): the login endpoint must
    not distinguish "no such user" from "wrong password" in its response, to
    avoid leaking which emails are registered.
    """

    def __init__(self) -> None:
        super().__init__("Invalid email or password")


class TokenRejectedError(Exception):
    """Raised by `AuthService` when a presented JWT must not be honored.

    Wraps `app.core.security.InvalidTokenError`/`TokenExpiredError` and the
    `AuthService`-level blacklist check into one stable exception type that
    API dependencies (`get_current_user`) can catch without importing
    `app.core.security` or `app.infrastructure.auth` directly.
    """

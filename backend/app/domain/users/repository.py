"""`IUserRepository` — the repository abstraction all persistence access for
the users aggregate goes through.

This is the pattern later stories copy for every other aggregate (Document,
Conversation, TabularColumnProfile, Plan, Subscription, ...): a narrow ABC in
`app/domain/<aggregate>/repository.py`, with concrete implementations living
in `app/infrastructure/db/<backend>/`. Business logic and API routers depend
on this interface only — never on `PostgresUserRepository`/`MongoUserRepository`
directly (Dependency Inversion).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from uuid import UUID

from app.domain.users.entities import User


class IUserRepository(ABC):
    """Persistence contract for the `User` aggregate."""

    @abstractmethod
    async def create(self, user: User) -> User:
        """Persist a new user and return the stored entity.

        Raises:
            app.domain.users.errors.UserAlreadyExistsError: if `user.email`
                is already taken.
        """

    @abstractmethod
    async def get_by_id(self, user_id: UUID) -> User | None:
        """Return the user with `user_id`, or `None` if it doesn't exist."""

    @abstractmethod
    async def get_by_email(self, email: str) -> User | None:
        """Return the user with `email`, or `None` if it doesn't exist."""

    @abstractmethod
    async def update(self, user: User) -> User:
        """Persist changes to an existing user and return the stored entity.

        Raises:
            app.domain.users.errors.UserNotFoundError: if `user.id` doesn't exist.
            app.domain.users.errors.UserAlreadyExistsError: if the update would
                collide with another user's email.
        """

    @abstractmethod
    async def delete(self, user_id: UUID) -> None:
        """Delete the user with `user_id`.

        Raises:
            app.domain.users.errors.UserNotFoundError: if `user_id` doesn't exist.
        """

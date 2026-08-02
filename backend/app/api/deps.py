"""FastAPI dependency providers shared across routers (STORY-006).

Routers depend on these, never on `PostgresUserRepository`/`RedisTokenBlacklist`/
`AuthService`'s constructor directly — this module is the one place that wires
concrete infrastructure into the domain-layer `AuthService` (Dependency
Inversion stays intact: `AuthService` itself still only imports
`IUserRepository`).
"""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from typing import Any

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from app.core.repository_factory import RepositoryFactory, get_repository_factory
from app.domain.users.auth_service import AuthService
from app.domain.users.entities import Role, User
from app.domain.users.errors import TokenRejectedError
from app.infrastructure.auth.redis_token_blacklist import get_token_blacklist

#: Points Swagger/OpenAPI's "Authorize" flow at the login endpoint; token
#: verification itself is fully handled by `get_current_user` below.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


async def get_auth_service(
    repository_factory: RepositoryFactory = Depends(get_repository_factory),
) -> AuthService:
    """Build an `AuthService` wired to the active `IUserRepository` + blacklist."""
    user_repository = await repository_factory.get_user_repository()
    return AuthService(user_repository, get_token_blacklist())


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service),
) -> User:
    """Resolve the bearer access token in `Authorization` to the current `User`.

    Raises:
        fastapi.HTTPException: 401 if the token is missing, expired,
            malformed, the wrong type, blacklisted, or its subject no longer
            exists.
    """
    try:
        return await auth_service.get_current_user(token)
    except TokenRejectedError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc


def require_role(
    *roles: Role,
) -> Callable[[User], Coroutine[Any, Any, User]]:
    """RBAC dependency factory: `Depends(require_role(Role.ADMIN, Role.OWNER))`.

    Returns a dependency that resolves the current user (reusing
    `get_current_user`) and additionally requires their role to be one of
    `roles`. Not yet wired into any router — later stories (e.g. STORY-050's
    admin config API) consume it directly.
    """

    async def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return current_user

    return _dependency

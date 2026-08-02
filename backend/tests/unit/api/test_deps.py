"""Unit tests for `app.api.deps`'s RBAC dependency helper (STORY-006).

`require_role`'s inner dependency callable is exercised directly (bypassing
FastAPI's DI resolution, which is exercised end-to-end by the integration
auth-flow test) — it only needs a `User` to make its allow/deny decision.
"""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.api.deps import require_role
from app.domain.users.entities import Role, User


def _user(role: Role) -> User:
    return User(email="a@example.com", hashed_password="h", name="A", role=role)


@pytest.mark.asyncio
async def test_require_role_allows_a_matching_role() -> None:
    dependency = require_role(Role.ADMIN, Role.OWNER)

    result = await dependency(_user(Role.ADMIN))

    assert result.role == Role.ADMIN


@pytest.mark.asyncio
async def test_require_role_rejects_a_non_matching_role() -> None:
    dependency = require_role(Role.ADMIN, Role.OWNER)

    with pytest.raises(HTTPException) as exc_info:
        await dependency(_user(Role.MEMBER))

    assert exc_info.value.status_code == 403

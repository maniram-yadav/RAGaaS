"""`IUserRepository` shape tests.

`IUserRepository` is an ABC: it must not be instantiable directly, and it must
declare exactly the five CRUD methods the story specifies. This keeps the
interface narrow (Interface Segregation) and enforces that any future
implementation (e.g. Mongo, STORY-045) implements the full contract (Liskov).
"""

from __future__ import annotations

import pytest

from app.domain.users.repository import IUserRepository


def test_iuserrepository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        IUserRepository()  # type: ignore[abstract]


def test_iuserrepository_declares_the_five_crud_methods() -> None:
    expected = {"create", "get_by_id", "get_by_email", "update", "delete"}

    assert expected == IUserRepository.__abstractmethods__

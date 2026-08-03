"""`IDocumentRepository` shape tests.

`IDocumentRepository` is an ABC: it must not be instantiable directly, and it
must declare exactly the five CRUD methods the story specifies. This keeps
the interface narrow (Interface Segregation) and enforces that any future
implementation (e.g. Mongo, STORY-045) implements the full contract
(Liskov).
"""

from __future__ import annotations

import pytest

from app.domain.ingestion.repository import IDocumentRepository


def test_idocumentrepository_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        IDocumentRepository()  # type: ignore[abstract]


def test_idocumentrepository_declares_the_five_crud_methods() -> None:
    expected = {"create", "get_by_id", "list_by_org", "update_status", "delete"}

    assert expected == IDocumentRepository.__abstractmethods__

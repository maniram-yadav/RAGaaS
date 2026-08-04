"""`BaseLoader`/`RawDocument` shape tests (STORY-011).

`BaseLoader` is an ABC: it must not be instantiable directly, and it must
declare exactly the one `load` method the story specifies. This keeps the
interface narrow (Interface Segregation) and enforces that every concrete
loader (`TextLoader` here; `PdfLoader`/`DocxLoader`/`ExcelLoader`/`CsvLoader`
later) implements the full contract (Liskov).
"""

from __future__ import annotations

import pytest

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument


def test_baseloader_cannot_be_instantiated_directly() -> None:
    with pytest.raises(TypeError):
        BaseLoader()  # type: ignore[abstract]


def test_baseloader_declares_exactly_load() -> None:
    assert BaseLoader.__abstractmethods__ == frozenset({"load"})


def test_rawdocument_defaults_metadata_to_an_empty_dict() -> None:
    raw = RawDocument(content="hello")

    assert raw.content == "hello"
    assert raw.metadata == {}


def test_rawdocument_holds_content_and_metadata() -> None:
    raw = RawDocument(content="hello", metadata={"source": "notes.txt"})

    assert raw.content == "hello"
    assert raw.metadata == {"source": "notes.txt"}


def test_rawdocument_instances_do_not_share_the_default_metadata_dict() -> None:
    """`field(default_factory=dict)` must produce a fresh dict per instance —
    mutating one `RawDocument`'s metadata must not leak into another's.
    """
    first = RawDocument(content="a")
    second = RawDocument(content="b")

    first.metadata["source"] = "a.txt"

    assert second.metadata == {}

"""Unit tests for `LoaderFactory` (STORY-011)."""

from __future__ import annotations

import pytest

from app.domain.ingestion.errors import UnsupportedFileTypeError
from app.domain.ingestion.loaders.docx_loader import DocxLoader
from app.domain.ingestion.loaders.factory import LoaderFactory
from app.domain.ingestion.loaders.pdf_loader import PdfLoader
from app.domain.ingestion.loaders.text_loader import TextLoader


def test_get_loader_returns_a_text_loader_for_dot_txt() -> None:
    loader = LoaderFactory.get_loader(".txt")

    assert isinstance(loader, TextLoader)


def test_get_loader_is_case_insensitive() -> None:
    loader = LoaderFactory.get_loader(".TXT")

    assert isinstance(loader, TextLoader)


def test_get_loader_returns_a_fresh_instance_each_call() -> None:
    first = LoaderFactory.get_loader(".txt")
    second = LoaderFactory.get_loader(".txt")

    assert first is not second


def test_get_loader_returns_a_pdf_loader_for_dot_pdf() -> None:
    # STORY-012: registering `.pdf` proves Open/Closed — this used to be the
    # "unregistered extension" example below; now it resolves to `PdfLoader`.
    loader = LoaderFactory.get_loader(".pdf")

    assert isinstance(loader, PdfLoader)


def test_get_loader_is_case_insensitive_for_pdf() -> None:
    loader = LoaderFactory.get_loader(".PDF")

    assert isinstance(loader, PdfLoader)


def test_get_loader_returns_a_docx_loader_for_dot_docx() -> None:
    # STORY-013: registering `.docx` proves Open/Closed — this used to be the
    # "unregistered extension" example above; now it resolves to `DocxLoader`.
    loader = LoaderFactory.get_loader(".docx")

    assert isinstance(loader, DocxLoader)


def test_get_loader_is_case_insensitive_for_docx() -> None:
    loader = LoaderFactory.get_loader(".DOCX")

    assert isinstance(loader, DocxLoader)


def test_get_loader_raises_for_an_unregistered_extension() -> None:
    # `.xlsx` isn't registered until STORY-026 — stands in for "any not-yet-
    # supported extension" here.
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        LoaderFactory.get_loader(".xlsx")

    assert exc_info.value.extension == ".xlsx"


def test_get_loader_raises_for_a_completely_unknown_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        LoaderFactory.get_loader(".exe")

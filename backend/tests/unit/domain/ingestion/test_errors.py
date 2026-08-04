"""Unit tests for ingestion domain errors."""

from __future__ import annotations

from uuid import uuid4

from app.domain.ingestion.errors import (
    DocumentNotFoundError,
    FileTooLargeError,
    UnsupportedFileTypeError,
)


def test_document_not_found_error_carries_the_document_id_and_a_message() -> None:
    document_id = uuid4()

    error = DocumentNotFoundError(document_id)

    assert error.document_id == document_id
    assert str(document_id) in str(error)


def test_unsupported_file_type_error_carries_the_extension_and_a_message() -> None:
    error = UnsupportedFileTypeError(".exe")

    assert error.extension == ".exe"
    assert ".exe" in str(error)


def test_file_too_large_error_carries_the_sizes_and_a_message() -> None:
    error = FileTooLargeError(size_bytes=2000, max_size_bytes=1024)

    assert error.size_bytes == 2000
    assert error.max_size_bytes == 1024
    assert "2000" in str(error)
    assert "1024" in str(error)

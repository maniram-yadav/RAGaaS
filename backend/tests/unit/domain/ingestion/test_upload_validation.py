"""Unit tests for `app.domain.ingestion.upload_validation.validate_upload`
(STORY-010's "extension + MIME sniff" allow-list validation).
"""

from __future__ import annotations

import pytest

from app.domain.ingestion.errors import FileTooLargeError, UnsupportedFileTypeError
from app.domain.ingestion.upload_validation import extension_of, validate_upload

_ALLOWED = [".txt", ".pdf", ".docx", ".xlsx", ".csv"]


def test_extension_of_lowercases_and_extracts_suffix() -> None:
    assert extension_of("Report.PDF") == ".pdf"
    assert extension_of("data.CSV") == ".csv"
    assert extension_of("no-extension") == ""


def test_accepts_a_well_formed_text_file() -> None:
    extension = validate_upload(
        filename="notes.txt",
        content=b"hello world",
        allowed_extensions=_ALLOWED,
        max_size_bytes=1024,
    )

    assert extension == ".txt"


def test_accepts_a_well_formed_pdf_file() -> None:
    extension = validate_upload(
        filename="report.pdf",
        content=b"%PDF-1.4 rest of a pdf...",
        allowed_extensions=_ALLOWED,
        max_size_bytes=1024,
    )

    assert extension == ".pdf"


def test_accepts_a_well_formed_docx_file() -> None:
    extension = validate_upload(
        filename="letter.docx",
        content=b"PK\x03\x04rest of a zip...",
        allowed_extensions=_ALLOWED,
        max_size_bytes=1024,
    )

    assert extension == ".docx"


def test_rejects_a_disallowed_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        validate_upload(
            filename="malware.exe",
            content=b"MZ\x90\x00",
            allowed_extensions=_ALLOWED,
            max_size_bytes=1024,
        )

    assert exc_info.value.extension == ".exe"


def test_rejects_no_extension() -> None:
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload(
            filename="noextension",
            content=b"hello",
            allowed_extensions=_ALLOWED,
            max_size_bytes=1024,
        )


def test_rejects_content_that_does_not_match_its_claimed_extension() -> None:
    """A renamed executable claiming to be a `.pdf` must still be rejected."""
    with pytest.raises(UnsupportedFileTypeError) as exc_info:
        validate_upload(
            filename="not-really.pdf",
            content=b"MZ\x90\x00 this is not a pdf",
            allowed_extensions=_ALLOWED,
            max_size_bytes=1024,
        )

    assert exc_info.value.extension == ".pdf"


def test_rejects_an_oversized_file() -> None:
    with pytest.raises(FileTooLargeError) as exc_info:
        validate_upload(
            filename="big.txt",
            content=b"a" * 2000,
            allowed_extensions=_ALLOWED,
            max_size_bytes=1024,
        )

    assert exc_info.value.size_bytes == 2000
    assert exc_info.value.max_size_bytes == 1024


def test_accepts_a_file_exactly_at_the_size_limit() -> None:
    extension = validate_upload(
        filename="exact.txt",
        content=b"a" * 1024,
        allowed_extensions=_ALLOWED,
        max_size_bytes=1024,
    )

    assert extension == ".txt"


def test_extension_match_is_case_insensitive() -> None:
    extension = validate_upload(
        filename="REPORT.TXT",
        content=b"hello",
        allowed_extensions=_ALLOWED,
        max_size_bytes=1024,
    )

    assert extension == ".txt"

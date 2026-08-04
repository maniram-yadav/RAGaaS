"""Upload-time validation for the document ingestion module (STORY-010).

Pure domain-layer functions — no FastAPI/HTTP dependency — so they're testable
in isolation and reusable by any future non-HTTP entrypoint (e.g. a bulk
import job). `app/api/documents.py` is the only caller, and it's the one place
that translates the domain errors raised here into HTTP status codes.

Validation is two-layered per the story's scope ("extension + MIME sniff"):

1. The claimed file extension must be in the caller-supplied allow-list
   (`system_config.ingestion.allowed_extensions`).
2. The file's actual bytes must look like the type its extension claims (a
   cheap magic-byte/heuristic sniff — not a full MIME database), so a renamed
   `.exe` can't sneak in as a `.txt`.

`_EXTENSION_SNIFFERS` is a registry dict (Open/Closed), mirroring the shape
`LoaderFactory` (STORY-011) uses for its own per-extension dispatch: a new
extension's sniff rule is one new entry here, never a branch added to
`validate_upload`.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import PurePosixPath

from app.domain.ingestion.errors import FileTooLargeError, UnsupportedFileTypeError


def _looks_like_text(content: bytes) -> bool:
    """Heuristic: text/CSV files shouldn't contain a NUL byte in their first 1KiB."""
    return b"\x00" not in content[:1024]


def _looks_like_pdf(content: bytes) -> bool:
    return content.startswith(b"%PDF-")


def _looks_like_ooxml_zip(content: bytes) -> bool:
    """`.docx`/`.xlsx` are ZIP containers (OOXML); ZIPs start with a local
    file header signature (or, for a pathological empty archive, the
    end-of-central-directory signature).
    """
    return content.startswith((b"PK\x03\x04", b"PK\x05\x06"))


#: extension -> "does `content` look like this type?" sniffer. Open/Closed: a
#: new extension is one new registry entry, never a branch in `validate_upload`.
_EXTENSION_SNIFFERS: dict[str, Callable[[bytes], bool]] = {
    ".txt": _looks_like_text,
    ".csv": _looks_like_text,
    ".pdf": _looks_like_pdf,
    ".docx": _looks_like_ooxml_zip,
    ".xlsx": _looks_like_ooxml_zip,
}


def extension_of(filename: str) -> str:
    """Return `filename`'s lowercased extension (e.g. `"Report.PDF"` -> `".pdf"`)."""
    return PurePosixPath(filename).suffix.lower()


def validate_upload(
    *,
    filename: str,
    content: bytes,
    allowed_extensions: list[str],
    max_size_bytes: int,
) -> str:
    """Validate an uploaded file's extension, size, and content.

    Returns the validated (lowercased) extension on success.

    Raises:
        app.domain.ingestion.errors.UnsupportedFileTypeError: `filename`'s
            extension isn't in `allowed_extensions`, or `content` doesn't
            look like that extension's type.
        app.domain.ingestion.errors.FileTooLargeError: `content` is larger
            than `max_size_bytes`.
    """
    extension = extension_of(filename)
    allowed = {ext.lower() for ext in allowed_extensions}
    if extension not in allowed:
        raise UnsupportedFileTypeError(extension)

    if len(content) > max_size_bytes:
        raise FileTooLargeError(size_bytes=len(content), max_size_bytes=max_size_bytes)

    sniffer = _EXTENSION_SNIFFERS.get(extension)
    if sniffer is not None and not sniffer(content):
        raise UnsupportedFileTypeError(extension)

    return extension

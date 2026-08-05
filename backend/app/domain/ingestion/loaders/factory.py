"""`LoaderFactory` — resolves the `BaseLoader` for a given file extension
(STORY-011, plan §4.1).

A registry dict keyed by lowercased extension (Open/Closed), mirroring the
shape of `app.domain.ingestion.upload_validation._EXTENSION_SNIFFERS`: a new
file type is one new `BaseLoader` subclass (its own module, under
`app.domain.ingestion.loaders`) + one new entry in `_LOADER_REGISTRY`
below — `LoaderFactory.get_loader` itself never grows an `if/elif` branch to
support a new type.

Reuses `UnsupportedFileTypeError` (already used by STORY-010's
`validate_upload` for the sibling "this extension isn't supported" case)
rather than inventing a new error type, per that error's own docstring.
"""

from __future__ import annotations

from app.domain.ingestion.errors import UnsupportedFileTypeError
from app.domain.ingestion.loaders.base import BaseLoader
from app.domain.ingestion.loaders.pdf_loader import PdfLoader
from app.domain.ingestion.loaders.text_loader import TextLoader

#: lowercased extension -> zero-arg `BaseLoader` builder. Open/Closed: a new
#: loader is one new entry here (+ its own module) — never a branch added to
#: `LoaderFactory.get_loader`.
_LOADER_REGISTRY: dict[str, type[BaseLoader]] = {
    ".txt": TextLoader,
    ".pdf": PdfLoader,
}


class LoaderFactory:
    """Resolves the `BaseLoader` strategy for a given file extension."""

    @staticmethod
    def get_loader(file_type: str) -> BaseLoader:
        """Return a `BaseLoader` instance for `file_type` (e.g. `".txt"`).

        `file_type` is matched case-insensitively.

        Raises:
            app.domain.ingestion.errors.UnsupportedFileTypeError: if no
                loader is registered for `file_type`.
        """
        extension = file_type.lower()
        try:
            loader_cls = _LOADER_REGISTRY[extension]
        except KeyError as exc:
            raise UnsupportedFileTypeError(extension) from exc
        return loader_cls()

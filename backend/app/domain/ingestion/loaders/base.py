"""`BaseLoader` interface + `RawDocument` value object (STORY-011, plan §4.1).

`BaseLoader` is the Strategy every file-type loader implements: parse a raw
file into a `RawDocument` (extracted text + metadata). Concrete loaders
(`TextLoader` here; `PdfLoader`/`DocxLoader` — STORY-012/013;
`ExcelLoader`/`CsvLoader` — STORY-026) must all be substitutable for one
another (Liskov) — same `load(file, *, filename=...) -> RawDocument`
contract regardless of file type.

`file` is a binary file-like object (anything supporting `.read() -> bytes`,
e.g. an `io.BytesIO` wrapping bytes returned by `IStorageService.read(uri)`,
or a real open file handle in tests) rather than a path or storage URI —
loaders never touch the filesystem or `IStorageService` themselves; sourcing
the bytes is the caller's job (STORY-015's `BaseProcessingPipeline.extract()`
hook, once it exists).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, BinaryIO


@dataclass(slots=True)
class RawDocument:
    """The result of loading a source file: extracted text + metadata.

    `metadata` always carries at least `source` (the original filename) and
    `file_type` (its lowercased extension); individual loaders may add more
    (e.g. a future `PdfLoader` adding `page_count`, `ExcelLoader`/`CsvLoader`
    adding the `schema_json`-shaped column info `tabular-qa-engineer`'s
    stories consume).
    """

    content: str
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseLoader(ABC):
    """Strategy interface every file-type loader implements (plan §4.1).

    `LoaderFactory.get_loader(extension)` resolves which concrete subclass
    handles a given file extension; callers depend on this interface only,
    never on a concrete loader class directly (Dependency Inversion).
    """

    @abstractmethod
    def load(self, file: BinaryIO, *, filename: str) -> RawDocument:
        """Parse `file`'s content into a `RawDocument`.

        Args:
            file: a binary file-like object (supports `.read() -> bytes`),
                positioned at the start of the content to parse.
            filename: the original filename — used for metadata and, where
                relevant, extension-specific parsing hints.
        """

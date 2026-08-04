"""`TextLoader` — the `BaseLoader` for plain-text (`.txt`) files (STORY-011).

The simplest concrete loader: decodes the file's bytes as UTF-8 (tolerating
undecodable bytes rather than raising, since a `.txt` file's encoding isn't
guaranteed) and returns the content verbatim, with no cleaning/splitting —
that's `TextProcessingPipeline`'s job (STORY-015), not the loader's.
"""

from __future__ import annotations

from typing import BinaryIO

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument


class TextLoader(BaseLoader):
    """Loads `.txt` files as UTF-8 text."""

    def load(self, file: BinaryIO, *, filename: str) -> RawDocument:
        raw_bytes = file.read()
        content = raw_bytes.decode("utf-8", errors="replace")
        return RawDocument(
            content=content,
            metadata={
                "source": filename,
                "file_type": ".txt",
                "char_count": len(content),
            },
        )

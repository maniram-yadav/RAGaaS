"""`DocxLoader` — the `BaseLoader` for `.docx` files (STORY-013).

Uses `python-docx` to extract paragraph text, joining non-empty paragraphs
with newlines into `RawDocument.content` and recording the paragraph count
in metadata.

Liskov-substitutable with `TextLoader`/`PdfLoader`: same `BaseLoader.load(
file, *, filename=...) -> RawDocument` contract, no DOCX-specific parameters
leak into the public signature.
"""

from __future__ import annotations

from typing import BinaryIO

from docx import Document as DocxDocument

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument


class DocxLoader(BaseLoader):
    """Loads `.docx` files, extracting paragraph text."""

    def load(self, file: BinaryIO, *, filename: str) -> RawDocument:
        docx_document = DocxDocument(file)

        paragraph_texts = [paragraph.text for paragraph in docx_document.paragraphs]
        content = "\n".join(paragraph_texts)

        return RawDocument(
            content=content,
            metadata={
                "source": filename,
                "file_type": ".docx",
                "char_count": len(content),
                "paragraph_count": len(paragraph_texts),
            },
        )

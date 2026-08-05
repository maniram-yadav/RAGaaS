"""`PdfLoader` — the `BaseLoader` for `.pdf` files (STORY-012).

Uses `pypdf` to extract per-page text, joining pages with a form-feed
character (`\\f`) as a page boundary marker and recording each page's
1-indexed page number in `metadata["pages"]` — needed later for citation
`page` metadata per plan §6 (a retrieved chunk should be traceable back to
the PDF page it came from).

Liskov-substitutable with `TextLoader`: same `BaseLoader.load(file, *,
filename=...) -> RawDocument` contract, no PDF-specific parameters leak into
the public signature.
"""

from __future__ import annotations

from typing import Any, BinaryIO

from pypdf import PdfReader

from app.domain.ingestion.loaders.base import BaseLoader, RawDocument


class PdfLoader(BaseLoader):
    """Loads `.pdf` files, extracting text and page-number metadata."""

    def load(self, file: BinaryIO, *, filename: str) -> RawDocument:
        reader = PdfReader(file)

        page_texts: list[str] = []
        pages_metadata: list[dict[str, Any]] = []
        for index, page in enumerate(reader.pages):
            page_number = index + 1
            page_text = page.extract_text() or ""
            page_texts.append(page_text)
            pages_metadata.append({"page": page_number, "char_count": len(page_text)})

        content = "\f".join(page_texts)

        return RawDocument(
            content=content,
            metadata={
                "source": filename,
                "file_type": ".pdf",
                "char_count": len(content),
                "page_count": len(page_texts),
                "pages": pages_metadata,
            },
        )

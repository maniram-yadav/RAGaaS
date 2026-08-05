# Document loaders

## Overview

Implements the loader abstraction from plan §4.1 ("accept uploaded file → ... → dispatch to the correct
Loader Strategy"): a narrow `BaseLoader` Strategy interface, a `LoaderFactory` that resolves the correct
loader for a file extension via an Open/Closed registry, and concrete implementations `TextLoader`
(`.txt`, STORY-011), `PdfLoader` (`.pdf`, STORY-012), and `DocxLoader` (`.docx`, STORY-013). This is
purely the loader abstraction + registry + loaders — none of it is wired into the upload endpoint
(`app.api.documents`, STORY-010) or any background job; that wiring is `TextProcessingPipeline`/the
Celery dispatch in STORY-015. This doc accumulates further content as `ExcelLoader`/`CsvLoader`
(STORY-026) land.

## Interfaces / contracts

- `app.domain.ingestion.loaders.base.BaseLoader` — ABC with a single abstract method,
  `load(file: BinaryIO, *, filename: str) -> RawDocument`. `file` is any binary file-like object
  (`.read() -> bytes`) — loaders never touch the filesystem or `IStorageService` directly; sourcing the
  bytes is the caller's responsibility. Every concrete loader must be substitutable for any other
  (Liskov) via this exact signature.
- `app.domain.ingestion.loaders.base.RawDocument` — `@dataclass(slots=True)` value object:
  `content: str`, `metadata: dict[str, Any] = field(default_factory=dict)`. Loaders populate `metadata`
  with at least `source` (original filename) and `file_type` (lowercased extension); individual loaders
  may add more (e.g. a future `PdfLoader` adding `page_count`, `ExcelLoader`/`CsvLoader` adding the
  `schema_json`-shaped column info `tabular-qa-engineer`'s stories consume).
- `app.domain.ingestion.loaders.text_loader.TextLoader` — the first concrete `BaseLoader`. Decodes the
  file's bytes as UTF-8 (`errors="replace"`, so undecodable bytes don't raise) and returns the content
  verbatim — no cleaning or splitting, which is `TextProcessingPipeline`'s job (STORY-015), not the
  loader's. Metadata: `{"source": filename, "file_type": ".txt", "char_count": len(content)}`.
- `app.domain.ingestion.loaders.pdf_loader.PdfLoader` (STORY-012) — the `.pdf` `BaseLoader`, built on
  `pypdf.PdfReader`. Extracts text per page via `page.extract_text()` and joins every page's text with a
  form-feed character (`\f`) as a page-boundary marker into `RawDocument.content` — no cleaning or
  splitting, same division of responsibility as `TextLoader`. Metadata:
  `{"source": filename, "file_type": ".pdf", "char_count": len(content), "page_count": <int>,
  "pages": [{"page": <1-indexed int>, "char_count": <int>}, ...]}`. The `pages` list is what will back
  citation `page` metadata later (plan §6) once chunking/retrieval land.
- `app.domain.ingestion.loaders.docx_loader.DocxLoader` (STORY-013) — the `.docx` `BaseLoader`, built on
  `python-docx` (`docx.Document`). Extracts `paragraph.text` for every paragraph in
  `docx_document.paragraphs` and joins them with `\n` into `RawDocument.content` — no cleaning or
  splitting, same division of responsibility as `TextLoader`/`PdfLoader`. Metadata:
  `{"source": filename, "file_type": ".docx", "char_count": len(content), "paragraph_count": <int>}`.
- `app.domain.ingestion.loaders.factory.LoaderFactory` — `get_loader(file_type: str) -> BaseLoader`
  (`@staticmethod`), matching `file_type` case-insensitively against `_LOADER_REGISTRY`, a module-level
  `dict[str, type[BaseLoader]]` keyed by lowercased extension (mirrors the shape of
  `app.domain.ingestion.upload_validation._EXTENSION_SNIFFERS`). Open/Closed: adding a new file type is
  one new `BaseLoader` subclass (its own module under `app.domain.ingestion.loaders`) + one new entry in
  `_LOADER_REGISTRY` — `get_loader` itself never grows an `if/elif` branch. STORY-012 proved this in
  practice: registering `.pdf` was one import + one dict entry (`".pdf": PdfLoader`); `get_loader`'s body
  has zero diff. STORY-013 proved it again: registering `.docx` was one import + one dict entry
  (`".docx": DocxLoader`); `get_loader`'s body again has zero diff.
- Reuses `app.domain.ingestion.errors.UnsupportedFileTypeError` (introduced by STORY-010 for
  `validate_upload`'s "disallowed extension" case) for "no loader registered for this extension," per
  that error's own docstring, rather than introducing a second error type for the same underlying domain
  concept.
- All six names (`BaseLoader`, `RawDocument`, `LoaderFactory`, `TextLoader`, `PdfLoader`, `DocxLoader`) are
  re-exported from `app.domain.ingestion.loaders.__init__` and from `app.domain.ingestion.__init__`
  itself.

## Config knobs

None. STORY-011, STORY-012, and STORY-013 introduce no new `system_config` keys or env vars — extension
allow-listing and size limits are STORY-010's `system_config.ingestion.*` concern
(`upload_validation.py`), not the loader's; `LoaderFactory` only maps an already-validated extension to a
loader. `pypdf==4.3.1` and `python-docx==1.1.2` were already pinned in `backend/requirements.txt` by
STORY-001/plan §16 (they just hadn't been installed into `backend/.venv` yet — installing an
already-pinned dependency isn't a config change). See
[docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule if a
future loader story needs a knob (e.g. chunk size, which belongs to STORY-015).

## Testing

- `backend/tests/unit/domain/ingestion/loaders/test_base.py` — `BaseLoader` cannot be instantiated
  directly, declares exactly one abstract method (`load`), and `RawDocument` defaults/holds
  content+metadata correctly, including that its default-factory `metadata` dict isn't shared across
  instances.
- `backend/tests/unit/domain/ingestion/loaders/test_text_loader.py` — loads a real fixture file
  (`fixtures/sample.txt`) verbatim, returns correct metadata, decodes UTF-8 (including non-ASCII text),
  replaces (rather than raises on) undecodable bytes, and handles an empty file.
- `backend/tests/unit/domain/ingestion/loaders/test_factory.py` — `get_loader(".txt")` returns a
  `TextLoader` instance (case-insensitively, e.g. `.TXT`), returns a fresh instance per call;
  `get_loader(".pdf")`/`get_loader(".PDF")` return a `PdfLoader` instance (STORY-012);
  `get_loader(".docx")`/`get_loader(".DOCX")` return a `DocxLoader` instance (STORY-013); raises
  `UnsupportedFileTypeError` (carrying the offending extension) for an unregistered extension — now
  exercised with `.xlsx` (still unregistered until STORY-026), since STORY-013 registering `.docx` made
  the STORY-012-era `.docx`-as-unregistered-example test stale; that test was replaced with the two
  `DocxLoader`-resolution tests above plus a re-targeted unregistered-extension test, not weakened.
- `backend/tests/unit/domain/ingestion/loaders/test_pdf_loader.py` (STORY-012) — loads a real 2-page
  fixture PDF (`fixtures/sample.pdf`, hand-built minimal valid PDF bytes since no PDF-authoring library
  was available in the environment; round-trip-verified through `pypdf.PdfReader`), asserts text is
  extracted from every page in the correct order, correct `page_count`/`pages` metadata (1-indexed page
  numbers + per-page `char_count`), correct `source`/`file_type`/`char_count` metadata, and that pages
  are joined with `\f`.
- `backend/tests/unit/domain/ingestion/loaders/test_docx_loader.py` (STORY-013) — loads a real 4-paragraph
  fixture DOCX (`fixtures/sample.docx`, authored with `python-docx` itself at fixture-generation time,
  since `python-docx` was now available as a pinned dependency — no need to hand-build DOCX zip/XML
  bytes the way STORY-012 had to for PDF), asserts text is extracted from every paragraph in the correct
  order, correct `paragraph_count` metadata (including a blank paragraph), correct
  `source`/`file_type`/`char_count` metadata, and that paragraphs are joined with `\n`.
- 30 unit tests in `tests/unit/domain/ingestion/loaders/` (23 from STORY-011/012 + 6 new `DocxLoader`
  tests + 1 net new factory test for STORY-013); full `backend/tests/unit` suite (138 tests) green with
  no regressions; `ruff check` / `mypy` clean on `app/domain/ingestion`.

Run with (from `backend/`):

```
pytest tests/unit/domain/ingestion/loaders -q   # loader tests only
pytest tests/unit -q                            # full backend unit suite, no external dependencies
```

## Story references

- STORY-011 — `BaseLoader`/`RawDocument`, `LoaderFactory` (extension registry), `TextLoader`.
- STORY-012 — `PdfLoader` (`.pdf`, page-numbered text extraction via `pypdf`), registered in
  `LoaderFactory` with zero diff to `get_loader` itself.
- STORY-013 — `DocxLoader` (`.docx`, paragraph text extraction via `python-docx`), registered in
  `LoaderFactory` with zero diff to `get_loader` itself.

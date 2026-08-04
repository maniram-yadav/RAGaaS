# Document loaders

## Overview

Implements the loader abstraction from plan §4.1 ("accept uploaded file → ... → dispatch to the correct
Loader Strategy"): a narrow `BaseLoader` Strategy interface, a `LoaderFactory` that resolves the correct
loader for a file extension via an Open/Closed registry, and the first concrete implementation,
`TextLoader`, for `.txt` files. This is purely the loader abstraction + registry + `TextLoader` — it is
not yet wired into the upload endpoint (`app.api.documents`, STORY-010) or any background job; that
wiring is `TextProcessingPipeline`/the Celery dispatch in STORY-015. This doc accumulates further content
as `PdfLoader` (STORY-012), `DocxLoader` (STORY-013), and `ExcelLoader`/`CsvLoader` (STORY-026) land.

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
- `app.domain.ingestion.loaders.factory.LoaderFactory` — `get_loader(file_type: str) -> BaseLoader`
  (`@staticmethod`), matching `file_type` case-insensitively against `_LOADER_REGISTRY`, a module-level
  `dict[str, type[BaseLoader]]` keyed by lowercased extension (mirrors the shape of
  `app.domain.ingestion.upload_validation._EXTENSION_SNIFFERS`). Open/Closed: adding a new file type is
  one new `BaseLoader` subclass (its own module under `app.domain.ingestion.loaders`) + one new entry in
  `_LOADER_REGISTRY` — `get_loader` itself never grows an `if/elif` branch.
- Reuses `app.domain.ingestion.errors.UnsupportedFileTypeError` (introduced by STORY-010 for
  `validate_upload`'s "disallowed extension" case) for "no loader registered for this extension," per
  that error's own docstring, rather than introducing a second error type for the same underlying domain
  concept.
- All four names (`BaseLoader`, `RawDocument`, `LoaderFactory`, `TextLoader`) are re-exported from
  `app.domain.ingestion.loaders.__init__` and from `app.domain.ingestion.__init__` itself.

## Config knobs

None. This story introduces no new `system_config` keys or env vars — extension allow-listing and size
limits are STORY-010's `system_config.ingestion.*` concern (`upload_validation.py`), not the loader's;
`LoaderFactory` only maps an already-validated extension to a loader. See
[docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule if a future
loader story needs a knob (e.g. chunk size, which belongs to STORY-015).

## Testing

- `backend/tests/unit/domain/ingestion/loaders/test_base.py` — `BaseLoader` cannot be instantiated
  directly, declares exactly one abstract method (`load`), and `RawDocument` defaults/holds
  content+metadata correctly, including that its default-factory `metadata` dict isn't shared across
  instances.
- `backend/tests/unit/domain/ingestion/loaders/test_text_loader.py` — loads a real fixture file
  (`fixtures/sample.txt`) verbatim, returns correct metadata, decodes UTF-8 (including non-ASCII text),
  replaces (rather than raises on) undecodable bytes, and handles an empty file.
- `backend/tests/unit/domain/ingestion/loaders/test_factory.py` — `get_loader(".txt")` returns a
  `TextLoader` instance (case-insensitively, e.g. `.TXT`), returns a fresh instance per call, and raises
  `UnsupportedFileTypeError` (carrying the offending extension) for an unregistered extension.
- 15 new unit tests, all green; full `backend/tests/unit` suite (124 tests) green with no regressions;
  `ruff check` / `mypy` clean on `app/domain/ingestion`.

Run with (from `backend/`):

```
pytest tests/unit/domain/ingestion/loaders -q   # this story's tests only
pytest tests/unit -q                            # full backend unit suite, no external dependencies
```

## Story references

- STORY-011 — `BaseLoader`/`RawDocument`, `LoaderFactory` (extension registry), `TextLoader`.

# RaaS Implementation Backlog — Story-by-Story

## How to use this document (read this first)

This backlog turns `RAG_as_a_Service_Project_Plan.md` into a sequence of implementable stories for a coding agent.

**Numbering & dependency rule (strict):**
- Every story has a permanent `STORY-NNN` id, assigned in build order.
- A story may only depend on stories with a **lower** number. A lower-numbered story must never depend on a higher-numbered one. If while implementing STORY-N you find you need something from a not-yet-built higher-numbered story, that is a signal the plan needs re-sequencing — stop and flag it, don't silently reorder.
- "Depends on" means: must be merged/working before this story can start. Stories with no shared dependency chain (e.g., `STORY-012` and `STORY-013`) can be built in parallel by different agents/sessions.
- Each story is scoped to be completable and independently testable/reviewable in isolation, per Single Responsibility.

**Story template fields:**
- **Epic/Phase** — maps to the roadmap phase in the plan (§14).
- **Depends on** — hard prerequisites (story numbers only).
- **Goal** — one-sentence outcome.
- **Context** — why this exists / where it fits the architecture (§2, §4 of the plan).
- **Scope of work** — concrete implementation tasks.
- **Out of scope** — explicitly excluded so the agent doesn't over-build (do not add unrelated abstractions).
- **Interfaces/contracts touched** — exact class/interface names from the plan, so naming stays consistent project-wide.
- **Acceptance criteria** — checklist a reviewer/agent uses to call the story "done."
- **Design pattern(s)** — from §5 of the plan, so intent is explicit.

**Global conventions all stories must follow:**
- Python 3.11+, FastAPI, async everywhere in the backend; Next.js 15 App Router + React 19 + Tailwind on the frontend.
- All cross-module access goes through the interfaces defined in `app/domain/**` — never import a concrete provider/repo directly into API routers or other domains (Dependency Inversion).
- New capability = new class + factory/registry entry, not an edit to existing branching logic (Open/Closed).
- Every story that adds a class implementing a `Base*`/`I*` interface must include unit tests proving Liskov substitutability where a contract test base class already exists (see STORY-059).
- No secrets in `system_config` (Mongo) in plaintext — reference `.env`/secret manager only (§11).

---

## Epic index (phase → story range)

| Phase | Range | Theme |
|---|---|---|
| Phase 0 — Foundations | STORY-001 … STORY-008 | Repo, CI, config, base DB/storage, auth, app shell |
| Phase 1 — Core RAG | STORY-009 … STORY-025 | Ingestion (text/pdf/docx), processing, retrieval, generation, chat, chat UI |
| Phase 2 — Tabular Q&A | STORY-026 … STORY-034 | Excel/CSV, column profiling, column-selection, tabular answers |
| Phase 3 — Safety & Routing | STORY-035 … STORY-044 | Validation chain, PII masking, moderation, intent routing |
| Phase 4 — Multi-provider Configurability | STORY-045 … STORY-051 | Mongo repos, S3/GCS/Azure storage, more LLM providers, admin config |
| Phase 5 — Billing & Subscriptions | STORY-052 … STORY-058 | Plans, Stripe, webhooks, quota metering, billing UI |
| Phase 6 — Hardening | STORY-059 … STORY-066 | Contract tests, integration/e2e, observability, security, SEO, docs |

---

## Phase 0 — Foundations

### STORY-001 — Repository scaffolding & monorepo layout
**Epic/Phase:** Phase 0
**Depends on:** none

**Goal:** Create the empty but correctly structured `backend/` and `frontend/` trees so every later story has a fixed place to land code.

**Context:** §8 of the plan defines the target folder structure. Getting this right first avoids churn later.

**Scope of work:**
- Create `backend/app/{main.py,core,api,domain,infrastructure,workers}` with `domain/{ingestion,processing,retrieval,generation,safety,chat,billing,users}` and `infrastructure/{db/postgres,db/mongo,storage,vectorstore}` as empty packages (`__init__.py` in each).
- Create `backend/tests/{unit,integration,e2e}`.
- Create `frontend/` Next.js 15 app (App Router) with route groups `(marketing)`, `(auth)`, `(portal)`, plus `components/`, `features/`, `lib/`, `styles/`, `tests/`.
- Create `docs/` and top-level `docker-compose.yml` (placeholder, filled in STORY-008).
- Add root `.gitignore`, `backend/requirements.txt` + `backend/requirements-dev.txt` seeded from §16 of the plan, `frontend/package.json` with Next 15/React 19/Tailwind deps.

**Out of scope:** no business logic, no working endpoints yet.

**Interfaces/contracts touched:** none yet — this is the scaffold only.

**Acceptance criteria:**
- [ ] `backend/` runs `uvicorn app.main:app` and returns a 200 on a trivial health route.
- [ ] `frontend/` runs `npm run dev` and serves a placeholder page per route group.
- [ ] Folder structure matches §8 exactly (reviewer diffs against the plan).

**Design pattern(s):** N/A (structural).

---

### STORY-002 — CI pipeline (lint, type-check, test scaffolding)
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** GitHub Actions workflow that lints, type-checks, and runs (currently empty) test suites on every PR.

**Scope of work:**
- `.github/workflows/backend-ci.yml`: ruff, mypy, pytest (allow zero tests to pass).
- `.github/workflows/frontend-ci.yml`: eslint, `tsc --noEmit`, vitest (allow zero tests to pass).
- Add `Dockerfile` for backend and frontend (build-only check in CI, no push yet).

**Out of scope:** deployment, Lighthouse CI (that's STORY-065), coverage thresholds (add once real tests exist, STORY-059+).

**Acceptance criteria:**
- [ ] Opening a PR triggers both workflows and they pass on the scaffold from STORY-001.
- [ ] Docker images build successfully for both backend and frontend.

**Design pattern(s):** N/A.

---

### STORY-003 — Config service & system_config precedence
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** A single `ConfigService` in `app/core/` that resolves runtime settings using the precedence: MongoDB `system_config` collection → environment variables → `.env` defaults (§4.9, §11).

**Context:** Every later provider/repo/storage factory reads its active strategy from this service. This is the highest-leverage foundational piece besides the four core interfaces.

**Scope of work:**
- `pydantic-settings`-based `Settings` class for env/`.env` (bootstrap-level: DB connection strings, secret keys).
- `ConfigService` class that: connects to Mongo via Motor, reads/writes the `system_config` document (`{db, storage, llm, payment}` shape per §6), caches in-process with short TTL, exposes `get(section: str) -> dict` and `set(section: str, values: dict)`.
- Config change notification stub (Observer/pub-sub per §5) — in-process event emitter is sufficient for now; cross-process pub/sub can be a later hardening story if needed.
- Unit tests: precedence order is respected; TTL cache expires and refreshes.

**Out of scope:** admin API endpoints for editing config (STORY-050); actual DB/storage/LLM provider implementations (later stories only read the shape this defines).

**Interfaces/contracts touched:** `ConfigService` (new, `app/core/config.py`).

**Acceptance criteria:**
- [ ] `ConfigService.get("db")` returns Mongo value when present, else falls back to env, else `.env` default.
- [ ] Cache TTL is configurable and covered by a unit test with a fake clock.

**Design pattern(s):** Observer/Pub-Sub (config change), Singleton-via-DI (one instance wired at startup).

---

### STORY-004 — IDatabase/Repository interfaces + first Postgres repo (User)
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** Establish the repository abstraction pattern with one real implementation: `IUserRepository` / `PostgresUserRepository`.

**Context:** §4.9, §5 — Dependency Inversion is the load-bearing decision for the whole persistence layer. Get the interface shape right here since STORY-009, 022, 027, 045, 052, 054 all follow this same pattern.

**Scope of work:**
- Define `IUserRepository` ABC in `app/domain/users/` with methods: `create`, `get_by_id`, `get_by_email`, `update`, `delete`.
- SQLAlchemy 2.0 async `User` model + Alembic migration in `infrastructure/db/postgres/`.
- `PostgresUserRepository` implementing `IUserRepository`.
- `RepositoryFactory` skeleton (`app/core/`) that currently only knows `"postgres"` and reads active DB from `ConfigService` (STORY-003); Mongo branch added later in STORY-045 without editing this class's existing postgres branch logic (Open/Closed — use a registry dict, not if/else chains, so adding Mongo is a pure addition).
- Unit tests against a test Postgres (testcontainers or SQLite fallback for pure unit scope — use testcontainers here since integration-level DB tests start now).

**Out of scope:** other repositories (Document, Conversation, etc. — later stories, same pattern).

**Interfaces/contracts touched:** `IUserRepository`, `RepositoryFactory`.

**Acceptance criteria:**
- [ ] `RepositoryFactory.get_user_repository()` returns a working `PostgresUserRepository` when `system_config.db.active == "postgres"`.
- [ ] CRUD round-trip test passes against a real Postgres container.
- [ ] Adding a new repository type requires only a new registry entry, not a change to existing factory branches.

**Design pattern(s):** Repository, Factory, Dependency Inversion.

---

### STORY-005 — IStorageService interface + LocalFsStorage
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** File storage abstraction with local-disk implementation.

**Scope of work:**
- `IStorageService` ABC (`app/domain/` or a shared `core/ports.py`): `save(file) -> uri`, `read(uri) -> bytes`, `delete(uri)`, `get_presigned_url(uri)`.
- `LocalFsStorage` in `infrastructure/storage/` — writes under a configurable base path.
- `StorageFactory` reading active strategy from `ConfigService` (STORY-003), registry-based like `RepositoryFactory`.
- Unit tests: save/read/delete round-trip; presigned URL for local storage can return a local file:// or served-path stub — document the behavior clearly since S3/GCS/Azure (STORY-046/047) will implement real presigned URLs.

**Out of scope:** S3/GCS/Azure implementations (STORY-046/047).

**Interfaces/contracts touched:** `IStorageService`, `StorageFactory`.

**Acceptance criteria:**
- [ ] Round-trip save→read→delete test passes.
- [ ] Switching `system_config.storage.active` (even though only one impl exists) is read correctly by the factory.

**Design pattern(s):** Strategy, Factory.

---

### STORY-006 — Auth module: signup/login/JWT
**Epic/Phase:** Phase 0
**Depends on:** STORY-004

**Goal:** Working signup/login with hashed passwords and JWT access+refresh tokens, `get_current_user` FastAPI dependency.

**Scope of work:**
- `passlib[bcrypt]` password hashing.
- `python-jose` JWT issuance (access + refresh), refresh rotation, blacklist-on-logout (Redis set — Redis wiring itself can be a thin client here; full Celery/Redis infra lands in STORY-014, so keep this story's Redis usage minimal and self-contained, e.g. a small redis-py client).
- `POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/me` routers.
- `Role` enum (`admin`, `member`, `owner`) on `User`; RBAC dependency helper for later use.
- Unit + integration tests: signup rejects duplicate email, login rejects wrong password, refresh rotates token, expired/blacklisted token rejected.

**Out of scope:** OAuth2 social login (explicitly deferred in plan), org/tenant model beyond the `role`/`org_id` field placeholders.

**Interfaces/contracts touched:** none new beyond `IUserRepository` (consumes STORY-004).

**Acceptance criteria:**
- [ ] Full signup→login→authenticated `/api/me`→refresh flow passes in an integration test.
- [ ] Passwords never appear in logs (grep test or structured-log assertion).

**Design pattern(s):** Dependency Inversion (auth service depends on `IUserRepository` interface only).

---

### STORY-007 — Next.js app shell + SEO scaffolding
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** Base Next.js 15 shell with the three route groups rendering placeholder pages, plus SEO primitives wired.

**Scope of work:**
- `(marketing)` route group: home, pricing, about placeholders using `generateMetadata`, `sitemap.xml`, `robots.txt`.
- `(auth)` route group: login/signup page shells (no API wiring yet — that's STORY-024).
- `(portal)` route group: dashboard shell behind a placeholder auth guard.
- Tailwind config with design tokens (colors, spacing, typography) per §9; `components/ui` primitives: Button, Card, Modal, Table (empty-state versions).

**Out of scope:** any real data fetching, chat UI (STORY-025), billing UI (STORY-058).

**Acceptance criteria:**
- [ ] All three route groups render without runtime errors.
- [ ] `sitemap.xml`/`robots.txt` are generated and reachable in dev.
- [ ] Lighthouse SEO score sanity-checked locally (formal CI gate comes in STORY-065).

**Design pattern(s):** Feature-sliced modular architecture (§9).

---

### STORY-008 — Local dev environment (docker-compose: Postgres, Mongo, Redis, Qdrant)
**Epic/Phase:** Phase 0
**Depends on:** STORY-001

**Goal:** One-command local environment for all infra dependencies used from Phase 1 onward.

**Scope of work:**
- `docker-compose.yml`: `postgres`, `mongo`, `redis`, `qdrant` services with named volumes and healthchecks.
- `.env.example` documenting every variable `ConfigService` (STORY-003) reads at bootstrap.
- `docs/runbooks/local-dev-setup.md` (short) explaining `docker compose up` → migrate → run.

**Out of scope:** production/K8s deployment.

**Acceptance criteria:**
- [ ] `docker compose up -d` brings up all four services healthy.
- [ ] Backend from STORY-004/005/006 connects successfully against these containers.

**Design pattern(s):** N/A.

---

## Phase 1 — Core RAG

### STORY-009 — Document model + repository (Postgres)
**Epic/Phase:** Phase 1
**Depends on:** STORY-004

**Goal:** `Document` entity and `IDocumentRepository`/`PostgresDocumentRepository` following the exact pattern from STORY-004.

**Scope of work:**
- `Document(id, org_id, filename, file_type, storage_uri, schema_json[nullable], status, uploaded_by, created_at)` per §6.
- `IDocumentRepository`: `create`, `get_by_id`, `list_by_org`, `update_status`, `delete`.
- Alembic migration; CRUD tests via testcontainers (reuse STORY-004's test harness).

**Acceptance criteria:**
- [ ] CRUD round-trip test passes.
- [ ] `status` enum supports at least `uploaded`, `processing`, `ready`, `failed` (needed by STORY-015/018).

**Design pattern(s):** Repository.

---

### STORY-010 — Document upload endpoint
**Epic/Phase:** Phase 1
**Depends on:** STORY-005, STORY-006, STORY-009

**Goal:** `POST /api/documents/upload` accepting a file, validating type/size, persisting via `IStorageService`, recording metadata via `IDocumentRepository`, returning the document id.

**Scope of work:**
- Multipart upload handling (`python-multipart`), size/type allow-list validation (extension + MIME sniff).
- Wire to `StorageFactory` (STORY-005) and `RepositoryFactory`-provided `IDocumentRepository` (STORY-009).
- `GET /api/documents`, `GET /api/documents/{id}`, `DELETE /api/documents/{id}` (basic CRUD surface from §7).
- Auth-gated via `get_current_user` (STORY-006).
- Does **not** enqueue a background job yet — that wiring is STORY-015 once workers exist (STORY-014); for now status stays `uploaded`.

**Out of scope:** actual parsing/loading (STORY-011+), background job dispatch (STORY-015).

**Acceptance criteria:**
- [ ] Upload of an oversized/disallowed file type is rejected with a clear 4xx.
- [ ] Successful upload returns a document id retrievable via `GET /api/documents/{id}`.

**Design pattern(s):** Dependency Inversion (router depends on interfaces, not concrete storage/repo).

---

### STORY-011 — BaseLoader interface + LoaderFactory + TextLoader
**Epic/Phase:** Phase 1
**Depends on:** STORY-010

**Goal:** Establish the loader abstraction (§4.1) with the simplest concrete loader, `TextLoader`.

**Scope of work:**
- `BaseLoader` ABC: `load(file) -> RawDocument` (`RawDocument` = content + metadata dataclass).
- `LoaderFactory.get_loader(file_type) -> BaseLoader` using a registry dict keyed by extension/MIME (Open/Closed — new types register, no branch edits).
- `TextLoader` implementation for `.txt`.
- Unit tests: factory returns correct loader per type, unknown type raises a clear domain error.

**Acceptance criteria:**
- [ ] `LoaderFactory.get_loader(".txt")` returns `TextLoader`; unsupported extension raises `UnsupportedFileTypeError`.
- [ ] `TextLoader.load()` returns a `RawDocument` with correct content and metadata.

**Design pattern(s):** Strategy + Factory.

---

### STORY-012 — PdfLoader
**Epic/Phase:** Phase 1
**Depends on:** STORY-011

**Goal:** Add PDF support purely by registering a new loader (no edits to `LoaderFactory` branching logic).

**Scope of work:**
- `PdfLoader` using `pypdf`, extracting text + page numbers into `RawDocument` metadata (needed later for citation `page` metadata per §6).
- Register in `LoaderFactory` map.
- Unit tests with a small sample PDF fixture.

**Acceptance criteria:**
- [ ] Sample PDF loads with correct per-page text and page-number metadata.
- [ ] `LoaderFactory` core code has zero diff besides the new registry entry (proves Open/Closed).

**Design pattern(s):** Strategy (Liskov-substitutable with `TextLoader`).

---

### STORY-013 — DocxLoader
**Epic/Phase:** Phase 1
**Depends on:** STORY-011

**Goal:** Add DOCX support the same way as STORY-012 (can be built in parallel with STORY-012 — both only depend on STORY-011).

**Scope of work:**
- `DocxLoader` using `python-docx`, extracting text/paragraphs into `RawDocument`.
- Register in `LoaderFactory` map.
- Unit tests with a sample `.docx` fixture.

**Acceptance criteria:**
- [ ] Sample DOCX loads correctly.
- [ ] No changes to existing loader classes or factory branching.

**Design pattern(s):** Strategy.

---

### STORY-014 — Background worker infrastructure (Celery + Redis)
**Epic/Phase:** Phase 1
**Depends on:** STORY-008

**Goal:** Celery app wired to Redis broker/backend, ready to host ingestion/embedding tasks.

**Scope of work:**
- `app/workers/celery_app.py` — Celery app config (broker/result backend from `ConfigService`/env).
- Task retry/backoff conventions (tenacity or Celery's own retry) + dead-letter handling pattern per §12.
- A trivial `ping` task with an integration test proving worker executes it end-to-end via the compose Redis (STORY-008).

**Out of scope:** the actual ingestion/embedding task bodies (STORY-015+).

**Acceptance criteria:**
- [ ] `ping` task round-trips through Redis and returns a result in a test.
- [ ] Retry/backoff policy documented and demonstrated on a task that fails once then succeeds.

**Design pattern(s):** N/A (infra).

---

### STORY-015 — Chunking pipeline (Template Method ETL skeleton)
**Epic/Phase:** Phase 1
**Depends on:** STORY-011, STORY-014

**Goal:** The shared "extract → transform → load" processing skeleton (§4.2, §5 Template Method) with the text-cleaning + splitting step implemented for non-tabular docs, dispatched as a Celery task.

**Scope of work:**
- `BaseProcessingPipeline` Template Method class: `extract()` (calls the right `BaseLoader` via `LoaderFactory`), `transform()` (hook, overridden per doc type), `load()` (hook, overridden per destination).
- `TextProcessingPipeline` subclass: clean text, split via `RecursiveCharacterTextSplitter` with per-doc-type tunable chunk size/overlap.
- Celery task `process_document(document_id)` that runs the pipeline and updates `Document.status` via `IDocumentRepository` (STORY-009).
- Wire STORY-010's upload endpoint to enqueue this task after successful upload (only edit needed there: one `.delay()`/`.apply_async()` call).
- Unit tests for chunking correctness (chunk count/overlap) using `TextLoader`/`PdfLoader`/`DocxLoader` fixtures.

**Acceptance criteria:**
- [ ] Uploading a `.txt`/`.pdf`/`.docx` file transitions `Document.status` from `uploaded` → `processing` → `ready` (embedding step stubbed until STORY-016/018 land — status can pause at a `chunked` intermediate state if needed).
- [ ] Chunk boundaries respect configured size/overlap in a unit test.

**Design pattern(s):** Template Method, Chain of Responsibility (pipeline steps), Pipeline.

---

### STORY-016 — IEmbeddingProvider interface + OpenAI embeddings
**Epic/Phase:** Phase 1
**Depends on:** STORY-015

**Goal:** Embedding abstraction with one concrete implementation.

**Scope of work:**
- `IEmbeddingProvider` ABC: `embed_documents(texts: list[str]) -> list[vector]`, `embed_query(text: str) -> vector`.
- `OpenAIEmbeddingProvider` via `langchain-openai`.
- `EmbeddingProviderFactory` reading active provider from `ConfigService` (registry pattern, same as STORY-004/005).
- Unit tests with a mocked OpenAI client (no live API calls in CI).

**Acceptance criteria:**
- [ ] `EmbeddingProviderFactory.get()` returns `OpenAIEmbeddingProvider` per config.
- [ ] Interface is narrow (embeddings only — not merged with `ILLMProvider`, per Interface Segregation in §5).

**Design pattern(s):** Strategy, Factory, Interface Segregation.

---

### STORY-017 — IVectorStore interface + Qdrant implementation
**Epic/Phase:** Phase 1
**Depends on:** STORY-016

**Goal:** Vector store abstraction with Qdrant as the default concrete implementation (§3 default choice).

**Scope of work:**
- `IVectorStore` ABC: `upsert(chunks: list[DocumentChunk])`, `search(query_vector, top_k, filters) -> list[ScoredChunk]`, `delete(doc_id)`.
- `QdrantVectorStore` using `qdrant-client`, pointed at the compose Qdrant instance (STORY-008).
- `VectorStoreFactory` (same registry pattern).
- Integration test: upsert then search round-trip against real Qdrant container.

**Acceptance criteria:**
- [ ] Upsert + search round-trip test passes against live Qdrant.
- [ ] Metadata (`doc_id`, `chunk_id`, `source`, `page`) is preserved and filterable per §4.2.

**Design pattern(s):** Strategy, Factory.

---

### STORY-018 — Wire chunking → embedding → vector upsert
**Epic/Phase:** Phase 1
**Depends on:** STORY-015, STORY-016, STORY-017

**Goal:** Complete the ingestion-to-vector pipeline: chunks produced in STORY-015 are embedded (STORY-016) and upserted (STORY-017), then `Document.status` moves to `ready`.

**Scope of work:**
- Extend `TextProcessingPipeline.load()` hook to call `IEmbeddingProvider.embed_documents` then `IVectorStore.upsert`.
- End-to-end Celery task test: upload → process → chunks land in Qdrant with correct metadata → status `ready`.

**Acceptance criteria:**
- [ ] A `.txt` upload results in queryable vectors in Qdrant with correct `doc_id`/`chunk_id` metadata.
- [ ] Failure at any step (e.g., embedding API error) leaves `Document.status = failed` with an error reason, not stuck in `processing`.

**Design pattern(s):** Template Method (completes the skeleton from STORY-015).

---

### STORY-019 — ILLMProvider interface + OpenAI provider
**Epic/Phase:** Phase 1
**Depends on:** STORY-003

**Goal:** LLM generation abstraction with one concrete implementation (can be built in parallel with STORY-014–018 since it only depends on STORY-003).

**Scope of work:**
- `ILLMProvider` ABC: `generate(prompt, **params) -> str` (or async streaming variant), config-driven model name/temperature/max_tokens.
- `OpenAIProvider` via `langchain-openai`.
- `LLMProviderFactory` (registry pattern, config-driven per §4.4).
- Unit tests with mocked client.

**Acceptance criteria:**
- [ ] `LLMProviderFactory.get()` returns `OpenAIProvider` per `system_config.llm`.
- [ ] Interface kept separate from `IEmbeddingProvider` (Interface Segregation).

**Design pattern(s):** Factory, Interface Segregation.

---

### STORY-020 — Retrieval module: SemanticRetriever
**Epic/Phase:** Phase 1
**Depends on:** STORY-017

**Goal:** `IRetriever` interface with a `SemanticRetriever` wrapping `IVectorStore`.

**Scope of work:**
- `IRetriever` ABC: `retrieve(query: str, top_k: int, filters) -> list[RetrievedChunk]`.
- `SemanticRetriever` implementation using `IEmbeddingProvider.embed_query` (STORY-016) + `IVectorStore.search` (STORY-017).
- Unit tests with fake vector store returning canned results.

**Acceptance criteria:**
- [ ] `SemanticRetriever.retrieve()` returns ranked chunks with source metadata.

**Design pattern(s):** Strategy.

---

### STORY-021 — Generation chain (LCEL) + MarkdownOutputParser
**Epic/Phase:** Phase 1
**Depends on:** STORY-019, STORY-020

**Goal:** LCEL chain `Prompt → LLM → OutputParser` producing validated Markdown answers with citations.

**Scope of work:**
- Prompt template(s) instructing Markdown output + citing sources.
- `MarkdownOutputParser` validating/normalizing headings/lists/tables/code blocks.
- `GenerationChainBuilder` (Builder pattern per §5) assembling: retrieval context injection → LLM call → markdown parse → optional citation formatting step.
- Unit tests: parser rejects/fixes malformed markdown; chain composes correctly with fake retriever + fake LLM provider.

**Acceptance criteria:**
- [ ] Given a fixed retriever+LLM stub, chain output is valid Markdown containing a citation reference to the source chunk.

**Design pattern(s):** Builder, Factory (LLM selection).

---

### STORY-022 — Conversation/Message models + repository
**Epic/Phase:** Phase 1
**Depends on:** STORY-004, STORY-009

**Goal:** Persist every chat turn per §4.5/§6.

**Scope of work:**
- `Conversation(id, org_id, user_id, title, created_at, updated_at)`, `Message(id, conversation_id, role, content_markdown, intent, sources_json, masked_entities_json, tokens_used, latency_ms, created_at)`.
- `IConversationRepository`/`PostgresConversationRepository`: `create_conversation`, `add_message`, `get_conversation`, `list_conversations`, `delete_conversation`.
- Alembic migration; CRUD + ordering tests.

**Acceptance criteria:**
- [ ] Messages retrieved in chronological order for a conversation.
- [ ] `intent`/`sources_json`/`masked_entities_json` fields exist even though not populated until STORY-042/038 land (nullable now).

**Design pattern(s):** Repository.

---

### STORY-023 — Chat message endpoint (full pipeline wiring, v1)
**Epic/Phase:** Phase 1
**Depends on:** STORY-020, STORY-021, STORY-022

**Goal:** `POST /api/chat/{conversation_id?}/message` — the first working end-to-end RAG chat call, without the safety pipeline (added in Phase 3) or intent routing (added in Phase 3) yet.

**Scope of work:**
- Endpoint creates conversation if none given, persists user message, runs retrieval (STORY-020) + generation (STORY-021), persists assistant message with `tokens_used`/`latency_ms`, returns Markdown answer + sources.
- `GET /api/conversations`, `GET /api/conversations/{id}`, `DELETE /api/conversations/{id}`.
- Integration test: upload doc (STORY-018) → ask a question → get a sourced Markdown answer → conversation history correctly persisted.

**Out of scope:** validation/safety chain (Phase 3), intent-based routing to non-RAG handlers (Phase 3), tabular answers (Phase 2).

**Acceptance criteria:**
- [ ] Full upload→ask→answer→history flow passes as an integration test.

**Design pattern(s):** Dependency Inversion (router only knows interfaces).

---

### STORY-024 — Frontend: auth pages wired to API
**Epic/Phase:** Phase 1
**Depends on:** STORY-006, STORY-007

**Goal:** Working login/signup pages calling the real auth API.

**Scope of work:**
- `features/auth/`: API client functions, forms, client-side validation mirroring backend rules.
- Token storage strategy (httpOnly cookie preferred) + auth context/provider for the `(portal)` route group guard.

**Acceptance criteria:**
- [ ] Manual/Playwright-lite check: signup → redirected to portal → refresh persists session → logout clears it.

**Design pattern(s):** Feature-sliced architecture.

---

### STORY-025 — Frontend: chat UI with streaming + Markdown rendering
**Epic/Phase:** Phase 1
**Depends on:** STORY-023, STORY-024

**Goal:** Authenticated chat screen: file upload, message list, Markdown rendering, source display.

**Scope of work:**
- `features/chat/`: chat window client component, message list, upload widget (drag-drop, progress, client-side type/size pre-validation mirroring STORY-010).
- Response streaming (SSE or fetch streaming) rendered incrementally.
- Markdown rendering via `react-markdown` + `remark-gfm` + `rehype-highlight`.

**Acceptance criteria:**
- [ ] Manual test: upload a doc, ask a question, see a streamed Markdown answer with a visible source citation.

**Design pattern(s):** Feature-sliced architecture.

---

## Phase 2 — Tabular Q&A

### STORY-026 — ExcelLoader + CsvLoader with schema extraction
**Epic/Phase:** Phase 2
**Depends on:** STORY-011

**Goal:** Add tabular loaders that extract schema (column names, inferred types, sample rows) alongside content, per §4.1.

**Scope of work:**
- `ExcelLoader` (openpyxl/pandas), `CsvLoader` (pandas) — both return `RawDocument` with a `schema` payload: column name, dtype, sample values.
- Register both in `LoaderFactory`.
- Persist `schema_json` on `Document` (STORY-009 field already exists).
- Unit tests with sample `.xlsx`/`.csv` fixtures, including edge cases (empty columns, mixed types).

**Acceptance criteria:**
- [ ] Schema extraction correctly infers dtypes and captures sample values for a fixture with mixed column types.

**Design pattern(s):** Strategy.

---

### STORY-027 — TabularColumnProfile model + repository
**Epic/Phase:** Phase 2
**Depends on:** STORY-004, STORY-026

**Goal:** Persistence for per-column semantic profiles per §6.

**Scope of work:**
- `TabularColumnProfile(id, document_id, column_name, dtype, description, sample_values)`.
- `ITabularProfileRepository`/`PostgresTabularProfileRepository`: `bulk_create`, `get_by_document`.
- Migration + CRUD tests.

**Acceptance criteria:**
- [ ] Bulk insert/retrieve of column profiles for a document round-trips correctly.

**Design pattern(s):** Repository.

---

### STORY-028 — Column profiler service (LLM-generated descriptions)
**Epic/Phase:** Phase 2
**Depends on:** STORY-019, STORY-026, STORY-027

**Goal:** Generate a semantic description per column (e.g. "monthly revenue") using the LLM, then persist via STORY-027's repository.

**Scope of work:**
- `ColumnProfilerService`: takes extracted schema (STORY-026) + sample rows, prompts `ILLMProvider` (STORY-019) per column (or batched), stores results via `ITabularProfileRepository`.
- Runs as a Celery task (reusing STORY-014 infra) triggered after an Excel/CSV upload's ingestion step.
- Unit tests with a mocked LLM provider asserting correct prompt construction and result mapping.

**Acceptance criteria:**
- [ ] Uploading a sample spreadsheet produces persisted `TabularColumnProfile` rows with plausible descriptions (mocked LLM in tests, real LLM in manual smoke test).

**Design pattern(s):** Template Method (reuses ETL skeleton hooks from STORY-015 for tabular docs).

---

### STORY-029 — Tabular store (structured row persistence)
**Epic/Phase:** Phase 2
**Depends on:** STORY-026

**Goal:** Persist the actual table rows for later row-lookup queries, per §4.2 (Postgres table per dataset or Parquet in object storage).

**Scope of work:**
- Decide and implement one approach for v1 (recommendation: a dedicated Postgres table per dataset via dynamic table creation, OR a single `tabular_rows` JSONB table keyed by `document_id` — pick the simpler JSONB approach for v1 to avoid dynamic DDL complexity; document the tradeoff in an ADR, STORY-066).
- `ITabularStore` interface: `store_rows(document_id, rows)`, `query_rows(document_id, filters, aggregation)`.
- Integration tests: store then query with a filter and an aggregation (sum/avg/count).

**Acceptance criteria:**
- [ ] Rows from a sample CSV are stored and a filtered aggregation query returns correct results.

**Design pattern(s):** Repository.

---

### STORY-030 — Column-selection strategy
**Epic/Phase:** Phase 2
**Depends on:** STORY-027, STORY-028

**Goal:** Given a question + a document's column profiles, decide which column(s)/aggregation answer it, per §4.2.

**Scope of work:**
- `ColumnSelectionStrategy` interface with two implementations: `EmbeddingMatchColumnSelector` (deterministic keyword/embedding match between question and column descriptions) and `LLMFunctionCallColumnSelector` (LLM receives schema, returns target column(s)/aggregation via function-calling).
- Composite/fallback: try deterministic first, fall back to LLM on low confidence (per Risk mitigation in §15); log low-confidence picks for review.
- **Golden-file tests** per §10: fixed (schema, question) pairs with expected column output.

**Acceptance criteria:**
- [ ] Golden-file suite passes for at least 10 representative schema/question pairs.
- [ ] Low-confidence picks are logged with enough context for manual review.

**Design pattern(s):** Strategy, Chain of Responsibility (deterministic → LLM fallback).

---

### STORY-031 — Row-lookup answer mode
**Epic/Phase:** Phase 2
**Depends on:** STORY-029, STORY-030

**Goal:** Deterministic pandas-based filter/aggregate answer path for analytical questions (sum/avg/filter), per §4.2.

**Scope of work:**
- `RowLookupAnswerer`: takes column-selection result (STORY-030) + `ITabularStore.query_rows` (STORY-029), computes result via pandas, returns structured result (value/table).
- Unit tests: sum/avg/count/filter scenarios against fixture data.

**Acceptance criteria:**
- [ ] Analytical questions ("what's the total revenue in March?") return correct computed values against fixture data.

**Design pattern(s):** Strategy (paired with STORY-032 under a common `TabularAnswerer` interface).

---

### STORY-032 — RAG-over-serialized-rows answer mode
**Epic/Phase:** Phase 2
**Depends on:** STORY-016, STORY-017, STORY-029, STORY-030

**Goal:** Semantic-search answer path for descriptive tabular questions, per §4.2.

**Scope of work:**
- Row-to-text serialization (each row → a text chunk with column context).
- Embed (STORY-016) and upsert (STORY-017) these serialized rows into the vector store with tabular-specific metadata.
- `SerializedRowRetriever` implementing the same `TabularAnswerer`-family contract as STORY-031, chosen when the question is descriptive rather than analytical (decision comes from STORY-030's classification signal).

**Acceptance criteria:**
- [ ] Descriptive questions ("which rows mention late delivery?") return relevant rows via semantic search.

**Design pattern(s):** Strategy.

---

### STORY-033 — TabularRetriever + generation integration
**Epic/Phase:** Phase 2
**Depends on:** STORY-021, STORY-030, STORY-031, STORY-032

**Goal:** Wire tabular answering into the chat/generation pipeline so tabular questions produce a natural-language + Markdown-table answer, per §4.3/§4.4.

**Scope of work:**
- `TabularRetriever` implementing `IRetriever` (STORY-020's interface) that delegates to `RowLookupAnswerer` (STORY-031) or `SerializedRowRetriever` (STORY-032) based on STORY-030's mode decision.
- Extend the generation chain (STORY-021) to accept computed rows/aggregates and render a Markdown table + narrative answer.
- Integration test: upload a CSV → ask an analytical question → get a correct Markdown-table answer with narrative.

**Acceptance criteria:**
- [ ] End-to-end tabular Q&A integration test passes for both answer modes.

**Design pattern(s):** Strategy, Decorator (if re-ranking applies equally here), Builder (generation chain reuse).

---

### STORY-034 — Frontend: tabular source UI affordances
**Epic/Phase:** Phase 2
**Depends on:** STORY-025, STORY-033

**Goal:** Chat UI renders tabular answers distinctly (table rendering, source badges indicating "from spreadsheet X, column Y").

**Scope of work:**
- Extend `features/chat/` message renderer to detect tabular-sourced messages (via `sources_json`/`intent`) and render enhanced table components + provenance badges.

**Acceptance criteria:**
- [ ] Manual test: asking a tabular question shows a rendered table with a visible source/column badge.

**Design pattern(s):** Feature-sliced architecture.

---

## Phase 3 — Safety & Routing Pipeline

### STORY-035 — Validation pipeline framework (Chain of Responsibility runner)
**Epic/Phase:** Phase 3
**Depends on:** STORY-023

**Goal:** The pipeline runner that later handlers (STORY-036–042) plug into, per §4.6.

**Scope of work:**
- `PipelineHandler` ABC: `handle(context: MessageContext) -> MessageContext` (mutate/annotate and pass along, or short-circuit with a rejection).
- `SafetyPipelineRunner`: ordered list of handlers, executes in sequence, stops early on a rejecting handler, returns final context.
- Handlers are independently registered (list/array config), not hardcoded branching — new checks insert without changing the runner (Open/Closed, explicit requirement in §4.6).
- Unit tests with fake handlers proving ordering, short-circuit, and independent testability.

**Out of scope:** the actual handlers (each is its own story below, buildable in parallel once this exists).

**Acceptance criteria:**
- [ ] Runner executes a list of fake handlers in order and honors early rejection.

**Design pattern(s):** Chain of Responsibility.

---

### STORY-036 — Schema validation handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** First pipeline step — Pydantic-based length/encoding/required-field checks, per §4.6 step 1.

**Scope of work:**
- `SchemaValidationHandler` implementing `PipelineHandler`; rejects malformed input with a clear error code.
- Unit tests for valid/invalid payloads.

**Acceptance criteria:**
- [ ] Oversized/malformed messages are rejected before reaching later handlers.

**Design pattern(s):** Chain of Responsibility (one link).

---

### STORY-037 — Sanitization handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** Strip control chars, normalize unicode, HTML-escape where rendered, per §4.6 step 2. (Parallel-buildable with STORY-036/038–042 — all only depend on STORY-035.)

**Scope of work:**
- `SanitizationHandler` implementing `PipelineHandler`.
- Unit tests covering control-char stripping, unicode normalization, HTML-escape correctness.

**Acceptance criteria:**
- [ ] Known adversarial inputs (control chars, mixed unicode, raw HTML) are normalized/escaped correctly.

**Design pattern(s):** Chain of Responsibility.

---

### STORY-038 — PII/secret detection & masking handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** Detect and mask PII/secrets before logging or forwarding to the LLM, with an audit trail, per §4.6 step 3 / §11.

**Scope of work:**
- `PiiMaskingHandler` using Presidio (regex + NER) to detect emails, phones, card numbers, API keys/tokens, passwords.
- Masking format `sk-live-***MASKED***`; audit trail records *what category* was masked, never the raw value, written to `Message.masked_entities_json` (STORY-022 field).
- Unit tests with known PII fixtures asserting correct detection + masking + audit content (no raw secret leaks into audit).

**Acceptance criteria:**
- [ ] Fixture inputs with emails/API keys/card numbers are correctly masked; audit trail contains category, not raw value.

**Design pattern(s):** Chain of Responsibility.

---

### STORY-039 — Prompt-injection / jailbreak screening handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** Heuristic + classifier check against known injection patterns before reaching retrieval/generation, per §4.6 step 4.

**Scope of work:**
- `PromptInjectionHandler`: rule-based pattern list + lightweight classifier (can start heuristic-only, with a clear extension point for a trained classifier later).
- Unit tests against a curated set of known injection strings (should reject) and benign strings (should pass).

**Acceptance criteria:**
- [ ] Curated injection-pattern test set is correctly rejected; benign message set passes through.

**Design pattern(s):** Chain of Responsibility.

---

### STORY-040 — Content moderation handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** `IModerationProvider` abstraction + a handler that blocks disallowed content categories, per §4.6 step 5.

**Scope of work:**
- `IModerationProvider` ABC: `check(text) -> ModerationResult`.
- One concrete implementation (e.g., `OpenAIModerationProvider`).
- `ContentModerationHandler` implementing `PipelineHandler`, using the provider via factory (same registry pattern as other providers).
- Unit tests with mocked provider responses (allowed/blocked categories).

**Acceptance criteria:**
- [ ] Blocked-category mock response causes the pipeline to reject the message.

**Design pattern(s):** Strategy, Factory, Chain of Responsibility.

---

### STORY-041 — Rate limiting handler (Redis token bucket)
**Epic/Phase:** Phase 3
**Depends on:** STORY-014, STORY-035

**Goal:** Per-user/per-tenant token-bucket throttling, per §4.6 step 6.

**Scope of work:**
- `RateLimitHandler` using Redis (reuse STORY-014's Redis connection conventions) implementing a token-bucket or sliding-window limiter keyed by `user_id`/`org_id`.
- Config-driven limits (read via `ConfigService`, STORY-003).
- Unit/integration tests: burst within limit passes, burst over limit is rejected with a 429-equivalent pipeline rejection.

**Acceptance criteria:**
- [ ] Exceeding the configured rate returns a rejection; requests under the limit pass.

**Design pattern(s):** Chain of Responsibility.

---

### STORY-042 — Intent classification handler
**Epic/Phase:** Phase 3
**Depends on:** STORY-035

**Goal:** Tag each message with an intent (`qa_document`, `qa_tabular`, `chitchat`, `account_billing_query`, `unsupported`), per §4.6 step 7.

**Scope of work:**
- `IntentClassificationHandler`: rules-first classifier (keyword/heuristic), LLM fallback (via `ILLMProvider`, STORY-019) for ambiguous cases.
- Populates `Message.intent` (STORY-022 field).
- Unit tests: clear-cut examples per intent classified correctly by rules; ambiguous example correctly triggers LLM fallback (mocked).

**Acceptance criteria:**
- [ ] Rule-based classifier handles unambiguous cases without calling the LLM; ambiguous cases correctly fall back.

**Design pattern(s):** Chain of Responsibility, Strategy (rules vs LLM fallback).

---

### STORY-043 — MessageRouter (intent-based dispatch)
**Epic/Phase:** Phase 3
**Depends on:** STORY-023, STORY-033, STORY-042

**Goal:** Dispatch by intent to the correct downstream handler, per §4.6 step 8: document/tabular → retrieval+generation (STORY-023/STORY-033), billing → scoped FAQ handler, chitchat → direct LLM response without retrieval.

**Scope of work:**
- `MessageRouter` Strategy: maps intent → handler function/class.
- `ChitchatHandler` (direct `ILLMProvider` call, no retrieval).
- `BillingFaqHandler` (scoped, non-RAG assistant — simple canned/LLM-assisted FAQ responder, not the full billing module which is Phase 5; keep this minimal, e.g. a static knowledge snippet + LLM paraphrase).
- Unit tests: each intent routes to the expected handler (mocked downstream calls).

**Acceptance criteria:**
- [ ] Each of the five intents from STORY-042 routes to the correct handler in a test.

**Design pattern(s):** Strategy.

---

### STORY-044 — Wire full safety pipeline into chat endpoint
**Epic/Phase:** Phase 3
**Depends on:** STORY-036, STORY-037, STORY-038, STORY-039, STORY-040, STORY-041, STORY-043

**Goal:** Replace STORY-023's direct retrieval+generation call with: message → `SafetyPipelineRunner` (STORY-035, all handlers) → `MessageRouter` (STORY-043).

**Scope of work:**
- Update the chat endpoint to run the full ordered pipeline: schema validation → sanitization → PII masking → injection screening → moderation → rate limiting → intent classification → routing.
- End-to-end integration test covering: a clean document question (happy path), a message with PII (masked, still answered), an injection attempt (rejected), a rate-limit breach (rejected), a chitchat message (answered without retrieval), a billing question (routed to FAQ handler).

**Acceptance criteria:**
- [ ] All six scenarios above pass as integration tests against the real endpoint.

**Design pattern(s):** Chain of Responsibility, Strategy — this story is pure wiring, no new pattern logic.

---

## Phase 4 — Multi-provider Configurability

### STORY-045 — MongoDB repository implementations (Motor)
**Epic/Phase:** Phase 4
**Depends on:** STORY-004, STORY-009, STORY-022, STORY-027

**Goal:** Second concrete implementation for every repository interface defined so far, proving Liskov substitutability, per §4.9.

**Scope of work:**
- `MongoUserRepository`, `MongoDocumentRepository`, `MongoConversationRepository`, `MongoTabularProfileRepository` — all implementing the same interfaces as their Postgres counterparts (STORY-004/009/022/027).
- Extend `RepositoryFactory` registries to include `"mongo"` entries — additive only, no edits to existing postgres branches.
- **Contract tests**: a shared test base class run against both Postgres and Mongo implementations of each interface (this seeds STORY-059's broader contract-test story — build the base class here since it's needed to verify this story itself).

**Acceptance criteria:**
- [ ] Same contract-test suite passes against both Postgres and Mongo implementations for each repository interface.
- [ ] Switching `system_config.db.active` between `"postgres"`/`"mongo"` changes behavior with zero code changes elsewhere.

**Design pattern(s):** Repository, Liskov Substitution, Factory.

---

### STORY-046 — S3Storage implementation
**Epic/Phase:** Phase 4
**Depends on:** STORY-005

**Goal:** Second storage strategy implementation, per §4.10.

**Scope of work:**
- `S3Storage` implementing `IStorageService` (STORY-005): save/read/delete/presigned URL via boto3 (add to requirements).
- Extend `StorageFactory` registry additively.
- Contract test (reuse pattern from STORY-045) run against `LocalFsStorage` and `S3Storage` (S3 via moto or testcontainers-localstack).

**Acceptance criteria:**
- [ ] Contract test suite passes for both storage implementations.
- [ ] Presigned URL generation works against a mocked/local S3-compatible endpoint.

**Design pattern(s):** Strategy, Liskov Substitution.

---

### STORY-047 — GcsStorage + AzureBlobStorage implementations
**Epic/Phase:** Phase 4
**Depends on:** STORY-005

**Goal:** Remaining storage strategies (can be built in parallel with STORY-046 — both only depend on STORY-005).

**Scope of work:**
- `GcsStorage` and `AzureBlobStorage` implementing `IStorageService`.
- Extend `StorageFactory` registry additively.
- Contract tests against both (using respective SDK test doubles/emulators).

**Acceptance criteria:**
- [ ] Contract test suite passes for both new implementations.

**Design pattern(s):** Strategy, Liskov Substitution.

---

### STORY-048 — Additional ILLMProvider implementations
**Epic/Phase:** Phase 4
**Depends on:** STORY-019

**Goal:** `AnthropicProvider`, `AzureOpenAIProvider`, `OllamaProvider`, per §4.4.

**Scope of work:**
- Three new classes implementing `ILLMProvider` (STORY-019), each via the appropriate `langchain-*` integration.
- Extend `LLMProviderFactory` registry additively.
- Contract test suite (same pattern) run against all four LLM providers (OpenAI + these three) using mocked clients — asserting consistent `generate()` contract (markdown-compatible output, param handling).

**Acceptance criteria:**
- [ ] Contract tests pass for all four providers.
- [ ] Switching `system_config.llm.active` changes provider with no code changes in generation module.

**Design pattern(s):** Factory, Liskov Substitution.

---

### STORY-049 — Config-driven runtime switching (DI wiring)
**Epic/Phase:** Phase 4
**Depends on:** STORY-003, STORY-045, STORY-046, STORY-047, STORY-048

**Goal:** Ensure every factory built so far (`RepositoryFactory`, `StorageFactory`, `EmbeddingProviderFactory`, `VectorStoreFactory`, `LLMProviderFactory`) re-resolves correctly when `system_config` changes at runtime, not just at process startup, per §4.9/§4.10/§12.

**Scope of work:**
- Verify/adjust each factory to consult `ConfigService`'s TTL-cached value on each resolution rather than caching the concrete instance forever at startup.
- Integration test: flip `system_config.storage.active` from `local` to `s3` mid-test-run (via `ConfigService.set`) and confirm the next request uses the new strategy after cache TTL expiry.

**Acceptance criteria:**
- [ ] Runtime config flip test passes for at least one factory of each kind (DB, storage, LLM).

**Design pattern(s):** Dependency Inversion, Observer (config change → cache invalidation).

---

### STORY-050 — Admin config API
**Epic/Phase:** Phase 4
**Depends on:** STORY-006, STORY-049

**Goal:** `GET /api/admin/config`, `PUT /api/admin/config`, per §7.

**Scope of work:**
- Admin-only RBAC guard (reuse `Role` from STORY-006).
- Read/write through `ConfigService` (STORY-003); validate shape on write (reject invalid provider names, missing required fields per §15 config-drift risk).
- Audit log entry on every config write (who, what changed, when) — table/collection can be minimal (`AdminAuditLog`).
- Integration tests: non-admin is rejected; admin write is validated, persisted, and audited.

**Acceptance criteria:**
- [ ] Invalid config payload (e.g., unknown provider) is rejected with a clear validation error.
- [ ] Valid config write is persisted, visible in a subsequent `GET`, and produces an audit log entry.

**Design pattern(s):** Dependency Inversion.

---

### STORY-051 — Frontend: admin config UI
**Epic/Phase:** Phase 4
**Depends on:** STORY-024, STORY-050

**Goal:** Authenticated admin screen to view/edit active DB/storage/LLM/payment strategy.

**Scope of work:**
- `features/admin/`: form reading current config, diff/preview before submit (per §15 mitigation — "admin UI diff/preview before applying"), submit calls STORY-050's `PUT`.

**Acceptance criteria:**
- [ ] Manual test: admin changes active LLM provider via UI, sees a diff/preview, confirms, and the change is reflected in a subsequent chat request.

**Design pattern(s):** Feature-sliced architecture.

---

## Phase 5 — Billing & Subscriptions

### STORY-052 — Plan model + repository + GET /api/plans
**Epic/Phase:** Phase 5
**Depends on:** STORY-004, STORY-045

**Goal:** `Plan` entity exposed publicly, per §4.8/§6/§7.

**Scope of work:**
- `Plan(id, name, price_cents, currency, interval, quotas_json)`.
- `IPlanRepository` + Postgres and Mongo implementations (reuse STORY-045's dual-impl + contract-test pattern).
- `GET /api/plans` (public, no auth required).

**Acceptance criteria:**
- [ ] `GET /api/plans` returns seeded plans; contract tests pass for both DB backends.

**Design pattern(s):** Repository.

---

### STORY-053 — IPaymentProvider interface + StripeProvider
**Epic/Phase:** Phase 5
**Depends on:** STORY-006

**Goal:** Payment abstraction with Stripe as the default implementation, per §4.8.

**Scope of work:**
- `IPaymentProvider` ABC: `create_checkout_session`, `handle_webhook`, `cancel_subscription`, `get_invoice`.
- `StripeProvider` implementing all four methods via the `stripe` SDK.
- `PaymentProviderFactory` (registry pattern, config-driven).
- Unit tests with mocked Stripe client.

**Acceptance criteria:**
- [ ] Each interface method has a passing unit test against a mocked Stripe client.

**Design pattern(s):** Strategy, Factory.

---

### STORY-054 — Subscription & Invoice models + repository
**Epic/Phase:** Phase 5
**Depends on:** STORY-045, STORY-052

**Goal:** Persistence for subscription/billing state, per §6.

**Scope of work:**
- `Subscription(id, org_id, plan_id, provider, provider_subscription_id, status, current_period_end)`, `Invoice(id, subscription_id, provider_invoice_id, amount, status, issued_at)`.
- Repository interfaces + Postgres/Mongo implementations (dual-impl + contract tests, same pattern as STORY-045/052).

**Acceptance criteria:**
- [ ] CRUD + contract tests pass for both DB backends.

**Design pattern(s):** Repository.

---

### STORY-055 — Checkout session + webhook endpoints (Stripe)
**Epic/Phase:** Phase 5
**Depends on:** STORY-053, STORY-054

**Goal:** `POST /api/billing/checkout-session`, `POST /api/billing/webhook/{provider}`, `POST /api/billing/cancel`, per §7.

**Scope of work:**
- Checkout endpoint calls `StripeProvider.create_checkout_session`.
- Webhook endpoint verifies Stripe signature, uses an idempotency key to avoid double-processing, updates `Subscription`/`Invoice` via STORY-054's repositories.
- Cancel endpoint calls `StripeProvider.cancel_subscription`.
- Integration tests using Stripe's test-mode/mocked webhook payloads, including a duplicate-webhook-delivery idempotency test.

**Acceptance criteria:**
- [ ] Signature verification rejects tampered payloads.
- [ ] Duplicate webhook delivery does not double-apply the subscription update.

**Design pattern(s):** Strategy (provider-specific webhook verification behind common interface).

---

### STORY-056 — Usage metering / quota enforcement middleware
**Epic/Phase:** Phase 5
**Depends on:** STORY-041, STORY-052, STORY-054

**Goal:** Enforce plan quotas (max docs, max tokens/month, max seats) at the API-gateway layer, not just after-the-fact billing, per §4.8/§12/§15.

**Scope of work:**
- Middleware/dependency that checks current usage against `Plan.quotas_json` before allowing document upload (STORY-010) or chat message (STORY-023/044) — reuse STORY-041's Redis counting infra where possible.
- Integration tests: exceeding max-docs quota rejects further uploads; exceeding token quota rejects further chat calls.

**Acceptance criteria:**
- [ ] Quota-exceeding requests are rejected with a clear, actionable error (e.g., "upgrade plan").

**Design pattern(s):** Chain of Responsibility (can be inserted as a pipeline handler) or middleware.

---

### STORY-057 — RazorpayProvider + PayPalProvider
**Epic/Phase:** Phase 5
**Depends on:** STORY-053

**Goal:** Remaining payment provider implementations, per §4.8 (can be built in parallel — both only depend on STORY-053).

**Scope of work:**
- `RazorpayProvider`, `PayPalProvider` implementing `IPaymentProvider`.
- Extend `PaymentProviderFactory` registry additively.
- Contract test suite (same pattern as other providers) run against Stripe/Razorpay/PayPal with mocked clients.

**Acceptance criteria:**
- [ ] Contract tests pass for all three payment providers.

**Design pattern(s):** Strategy, Liskov Substitution.

---

### STORY-058 — Frontend: billing/subscription pages
**Epic/Phase:** Phase 5
**Depends on:** STORY-024, STORY-052, STORY-055

**Goal:** Plan selection, checkout redirect, subscription status, invoice history UI.

**Scope of work:**
- `features/billing/`: plan comparison page (public, uses STORY-052), checkout button (redirects to Stripe Checkout via STORY-055), account billing page showing subscription status + invoices.

**Acceptance criteria:**
- [ ] Manual test in Stripe test mode: select plan → checkout → webhook updates status → billing page reflects active subscription.

**Design pattern(s):** Feature-sliced architecture.

---

## Phase 6 — Hardening

### STORY-059 — Contract test suite consolidation for all interfaces
**Epic/Phase:** Phase 6
**Depends on:** STORY-045, STORY-048, STORY-053, STORY-057

**Goal:** Consolidate the per-story contract-test bases (introduced piecemeal in STORY-045/046/047/048/057) into one documented, reusable contract-test framework covering every `I*Provider`/`I*Repository`, per §10.

**Scope of work:**
- `tests/contract/` shared base classes per interface family; ensure every concrete implementation built so far is registered and run against its family's contract suite in CI.
- CI gate: contract suite must pass for all implementations on every PR touching `infrastructure/`.

**Acceptance criteria:**
- [ ] Single CI job runs all contract suites; adding a new concrete implementation without registering it in the contract runner fails CI (enforced via a discovery check).

**Design pattern(s):** Liskov Substitution (this story is the verification layer for it).

---

### STORY-060 — Integration tests with testcontainers (full sweep)
**Epic/Phase:** Phase 6
**Depends on:** STORY-059

**Goal:** Ensure repository/pipeline integration tests across the whole backend run against real Postgres/Mongo/Redis/Qdrant in CI, not just locally, per §10.

**Scope of work:**
- CI job spinning up all four containers via testcontainers; run the full integration test suite accumulated from STORY-004 onward.
- Fix any tests that were previously only exercised locally.

**Acceptance criteria:**
- [ ] CI green on the full integration suite against real containers.

**Design pattern(s):** N/A.

---

### STORY-061 — E2E API test: upload → ingest → chat → answer
**Epic/Phase:** Phase 6
**Depends on:** STORY-044

**Goal:** Formalize the golden end-to-end backend flow as a standing E2E suite via `httpx.AsyncClient` against a running FastAPI test app, per §10.

**Scope of work:**
- Cover: signup → login → upload each supported file type → ask a document question → ask a tabular question → verify markdown answer + sources → export conversation → delete conversation → delete document.
- Add to CI as a dedicated (slower) job, separate from unit/integration.

**Acceptance criteria:**
- [ ] Full E2E suite passes in CI end to end.

**Design pattern(s):** N/A.

---

### STORY-062 — Frontend Playwright E2E suite
**Epic/Phase:** Phase 6
**Depends on:** STORY-034, STORY-058

**Goal:** Browser-level E2E covering the full user journey, per §10.

**Scope of work:**
- Playwright suite: signup → upload doc → ask question → see markdown answer → subscribe to plan (mocked payment provider in test mode).
- Add to CI as its own job.

**Acceptance criteria:**
- [ ] Playwright suite passes in CI against a locally-served build.

**Design pattern(s):** N/A.

---

### STORY-063 — Observability (OpenTelemetry, Prometheus, structured logs)
**Epic/Phase:** Phase 6
**Depends on:** STORY-023

**Goal:** Cross-cutting tracing/metrics/logging per §2/§12.

**Scope of work:**
- `structlog` structured JSON logging across the backend (ensure STORY-006's "no passwords in logs" constraint holds project-wide, and STORY-038's masking is applied before any logging of user content).
- OpenTelemetry tracing spans around ingestion, retrieval, generation, and the safety pipeline; Prometheus metrics (request latency, token usage, queue depth).
- Grafana dashboard config (basic) checked into `docs/runbooks/`.

**Acceptance criteria:**
- [ ] A traced request through chat shows spans for validation, retrieval, and generation.
- [ ] Prometheus metrics endpoint exposes latency/token/queue metrics.

**Design pattern(s):** N/A (cross-cutting).

---

### STORY-064 — Security review & audit logging completeness
**Epic/Phase:** Phase 6
**Depends on:** STORY-050, STORY-056

**Goal:** Close out the §11 security checklist end-to-end.

**Scope of work:**
- Verify: JWT secret rotation path, refresh-token rotation/blacklist (STORY-006) is enforced project-wide; secrets never stored in `system_config` plaintext (audit STORY-050's validation rules to reject secret-shaped values); audit log (STORY-050) covers all admin config changes AND data deletions (documents, conversations — extend to STORY-010/STORY-023's delete endpoints if not already logged).
- Produce a short security review write-up in `docs/`.

**Acceptance criteria:**
- [ ] Every item in §11's checklist has a corresponding test or documented manual verification.

**Design pattern(s):** N/A.

---

### STORY-065 — SEO / performance audit + Lighthouse CI gate
**Epic/Phase:** Phase 6
**Depends on:** STORY-007, STORY-025

**Goal:** Enforce the Core Web Vitals budget from §9 in CI.

**Scope of work:**
- Lighthouse CI integrated into the frontend CI workflow (STORY-002) with a defined performance/SEO budget; fix any regressions found on marketing + portal pages.

**Acceptance criteria:**
- [ ] Lighthouse CI gate is active and passing in the frontend workflow.

**Design pattern(s):** N/A.

---

### STORY-066 — Documentation: ADRs, runbooks, module READMEs
**Epic/Phase:** Phase 6
**Depends on:** STORY-004, STORY-005, STORY-019, STORY-029, STORY-053 *(the stories whose decisions most need an ADR — see below)*

**Goal:** Close out §13 documentation plan.

**Scope of work:**
- ADRs in `docs/adr/` for: DB strategy pattern (references STORY-004/045), storage strategy pattern (STORY-005/046/047), LLM provider strategy (STORY-019/048), tabular storage approach decision deferred from STORY-029, payment provider strategy (STORY-053/057).
- Runbooks in `docs/runbooks/`: rotating LLM provider, adding a new file loader, adding a new payment provider (each should be a short, concrete walkthrough referencing the actual story/interface names above so it stays accurate).
- Per-module `README.md` in each `backend/app/domain/*/` explaining that module's contract.
- `pydocstyle` lint rule enabled in CI (extends STORY-002) enforcing docstrings on public classes/functions.

**Acceptance criteria:**
- [ ] All five ADRs exist and reflect the actual implemented decision (not just the plan's proposal).
- [ ] `pydocstyle` gate is active in CI.

**Design pattern(s):** N/A.

---

## Parallelization quick-reference

Stories with no dependency on each other can be worked simultaneously by different agents/sessions. Notable parallel tracks:

- **STORY-012 / STORY-013** (Pdf/Docx loaders) — both only need STORY-011.
- **STORY-014 / STORY-019** — worker infra vs. LLM provider, independent tracks that later converge at STORY-021+.
- **STORY-036 through STORY-042** — all seven safety handlers only need STORY-035; assign to separate agents and merge into STORY-044.
- **STORY-046 / STORY-047** — S3 vs GCS/Azure storage, both only need STORY-005.
- **STORY-057** can run alongside Phase 5's other stories once STORY-053 lands.

## What to do if a dependency looks wrong

If, while implementing story N, you find you need a capability that only a higher-numbered story provides: do not reach ahead and implement it inline. Stop, note the missing capability and which story should own it, and either (a) renumber by inserting it earlier if it's foundational, or (b) descope the current story to stub that capability behind the existing interface until the later story lands. Never let a lower-numbered story's tests depend on a higher-numbered story's code.

# Story status board

One line per `STORY-NNN`. `- [ ]` = todo, `- [~]` = in_progress, `- [!]` = blocked, `- [x]` = done.

**Do not hand-edit the depends/owner columns** — they're generated from
`.claude/rules/story-routing.md` and `implementation_task.md`. Only the checkbox and the trailing note
change as work progresses. `/work-story` and `/story-status` read this file; agents update their own
story's row when they finish (see `.claude/rules/story-workflow.md`'s Definition of Done).

Format: `- [ ] STORY-NNN — Title — depends: ... — owner: agent-name — note: ...`

## Phase 0 — Foundations

- [x] STORY-001 — Repository scaffolding & monorepo layout — depends: none — owner: devops-observability-engineer — note: backend/frontend trees match plan §8; uvicorn health route + Next dev route-group pages verified live (200s), tests green, docker-compose.yml left as placeholder for STORY-008.
- [x] STORY-002 — CI pipeline (lint, type-check, test scaffolding) — depends: STORY-001 — owner: devops-observability-engineer — note: backend-ci.yml (ruff/mypy/pytest + docker build) and frontend-ci.yml (eslint/tsc/vitest + docker build) added; both Dockerfiles build and backend image verified live via /health; fixed a real tenacity/langchain pin conflict and added a working ESLint 9 flat config (STORY-001's .eslintrc.json was unreadable by ESLint 9).
- [x] STORY-003 — Config service & system_config precedence — depends: STORY-001 — owner: platform-core-engineer — note: `ConfigService`/`Settings` in `backend/app/core/` resolve system_config(Mongo)->env->.env via a registry of per-section default builders, TTL cache (fake-clock tested), and an in-process Observer stub for `set()`; 20 new unit tests green, mypy/ruff clean. Added `DB_ACTIVE`/`STORAGE_ACTIVE`/`LLM_*`/`PAYMENT_ACTIVE`/`VECTORSTORE_ACTIVE`/`SAFETY_*`/`CONFIG_CACHE_TTL_SECONDS` to `.env.example` as the layer-2/3 fallback for each system_config section (via add-config-key), plus `pydantic-settings`/`motor` installed into `backend/.venv`.
- [x] STORY-004 — IDatabase/Repository interfaces + first Postgres repo (User) — depends: STORY-001 — owner: platform-core-engineer — note: `IUserRepository`/`User`/errors in `app/domain/users/`; `UserModel` + async engine/session + `PostgresUserRepository` + Alembic migration `0001_create_users_table` in `app/infrastructure/db/postgres/`; registry-based `RepositoryFactory` (`app/core/repository_factory.py`) reads `system_config.db.active` via `ConfigService`. 45 tests green (unit + testcontainers Postgres integration incl. CRUD round-trip and factory end-to-end), ruff/mypy clean. Bumped `sqlalchemy[asyncio]` pin to 2.0.36 (fixes a real `str | None` stringified-annotation crash under newer CPython typing internals) — flagged since `requirements.txt` is shared infra.
- [x] STORY-005 — IStorageService interface + LocalFsStorage — depends: STORY-001 — owner: platform-core-engineer — note: `IStorageService`/`StorageObjectNotFoundError` in `app/domain/storage/`; `LocalFsStorage` in `app/infrastructure/storage/local.py` (uuid-keyed files under a configurable base path, path-traversal-safe, `get_presigned_url` documented as a `file://` URI stub pending STORY-046/047's real presigned URLs); registry-based `StorageFactory` (`app/core/storage_factory.py`) reads `system_config.storage.active` via `ConfigService`, mirroring `RepositoryFactory`. 17 new unit tests green (round-trip save/read/delete, registry Open/Closed, active-backend dispatch), ruff/mypy clean. No new config keys needed — `storage.active`/`storage.local.base_path` were already scaffolded by STORY-003.
- [x] STORY-006 — Auth module: signup/login/JWT — depends: STORY-004 — owner: platform-core-engineer — note: `Role` enum (admin/member/owner) on `User`; `AuthService` (signup/login/refresh-rotation/logout/get_current_user) in `app/domain/users/auth_service.py` depending only on `IUserRepository`; `app/core/security.py` (passlib bcrypt hashing + python-jose access/refresh JWTs); `RedisTokenBlacklist` thin client in `app/infrastructure/auth/`; `POST /api/auth/{signup,login,refresh,logout}` + `GET /api/me` routers and `get_current_user`/`require_role` RBAC dependency in `app/api/`. 100 tests green (unit + testcontainers Postgres+Redis integration incl. full signup→login→/api/me→refresh flow, dup-email, wrong-password, rotation-reuse-rejection, expired/blacklisted-token rejection, password-never-logged), ruff/mypy clean. Added `JWT_ALGORITHM` config key via `add-config-key`; pinned `bcrypt==4.0.1` (passlib 1.7.4 breaks on bcrypt>=4.1's removed `__about__`) and added `email-validator` to `requirements.txt`; added a narrow ruff `flake8-bugbear` allowlist for `fastapi.Depends`/`Query`/`Path`/`Body` (first FastAPI router in the app). Added `POST /api/auth/logout` beyond the plan's literal 4-route list — required to exercise the scope's explicit "blacklist-on-logout" capability — flagged as the one deliberate scope addition.
- [x] STORY-007 — Next.js app shell + SEO scaffolding — depends: STORY-001 — owner: frontend-engineer — note: `(marketing)` (home/pricing/about, each with `generateMetadata`), `(auth)` (login/signup shells, disabled submits, no API wiring), and `(portal)` (dashboard behind a placeholder `isAuthenticatedPlaceholder()` guard, always-allow until STORY-024) route groups built on STORY-001's scaffold; `app/sitemap.ts`/`app/robots.ts` metadata routes (new `NEXT_PUBLIC_SITE_URL` env var for absolute URLs, added via `add-config-key`); Tailwind design tokens (`tailwind.config.ts`) + `components/ui` primitives (Button/Card/Modal/Table, Table has an empty-state). 33 Vitest+RTL tests green, `tsc --noEmit`/`eslint .` clean; also fixed a test-infra gap (`tests/setup.ts` was missing RTL's `afterEach(cleanup)`, since `vitest.config.ts` doesn't set `test.globals`). Manually verified via `npm run dev`: all three route groups + `/sitemap.xml` + `/robots.txt` return 200, home page HTML carries title/description/OG/Twitter tags (Lighthouse CI gate itself is STORY-065).
- [ ] STORY-008 — Local dev environment (docker-compose) — depends: STORY-001 — owner: devops-observability-engineer — note:

## Phase 1 — Core RAG

- [x] STORY-009 — Document model + repository (Postgres) — depends: STORY-004 — owner: ingestion-engineer — note: `Document`/`DocumentStatus` (uploaded/processing/ready/failed) in `app/domain/ingestion/entities.py`; `IDocumentRepository` (create/get_by_id/list_by_org/update_status/delete) + `DocumentNotFoundError` in `app/domain/ingestion/`; `DocumentModel` (added to the shared `models.py`, FK `uploaded_by -> users.id`) + `PostgresDocumentRepository` + Alembic migration `0002_create_documents_table` (depends on `0001`) in `app/infrastructure/db/postgres/`, following STORY-004's exact pattern. 19 tests green (10 unit + 9 testcontainers Postgres integration incl. CRUD round-trip, `schema_json` persistence, and `list_by_org` multi-tenant scoping), ruff/mypy clean. Deliberately did not touch `RepositoryFactory` (no `get_document_repository`/registry) — that wiring is STORY-010's scope, not this story's four bullets.
- [ ] STORY-010 — Document upload endpoint — depends: STORY-005, STORY-006, STORY-009 — owner: ingestion-engineer — note:
- [ ] STORY-011 — BaseLoader interface + LoaderFactory + TextLoader — depends: STORY-010 — owner: ingestion-engineer — note:
- [ ] STORY-012 — PdfLoader — depends: STORY-011 — owner: ingestion-engineer — note:
- [ ] STORY-013 — DocxLoader — depends: STORY-011 — owner: ingestion-engineer — note:
- [ ] STORY-014 — Background worker infrastructure (Celery + Redis) — depends: STORY-008 — owner: devops-observability-engineer — note:
- [ ] STORY-015 — Chunking pipeline (Template Method ETL skeleton) — depends: STORY-011, STORY-014 — owner: ingestion-engineer — note:
- [ ] STORY-016 — IEmbeddingProvider interface + OpenAI embeddings — depends: STORY-015 — owner: retrieval-generation-engineer — note:
- [ ] STORY-017 — IVectorStore interface + Qdrant implementation — depends: STORY-016 — owner: retrieval-generation-engineer — note:
- [ ] STORY-018 — Wire chunking → embedding → vector upsert — depends: STORY-015, STORY-016, STORY-017 — owner: retrieval-generation-engineer — note:
- [ ] STORY-019 — ILLMProvider interface + OpenAI provider — depends: STORY-003 — owner: retrieval-generation-engineer — note:
- [ ] STORY-020 — Retrieval module: SemanticRetriever — depends: STORY-017 — owner: retrieval-generation-engineer — note:
- [ ] STORY-021 — Generation chain (LCEL) + MarkdownOutputParser — depends: STORY-019, STORY-020 — owner: retrieval-generation-engineer — note:
- [ ] STORY-022 — Conversation/Message models + repository — depends: STORY-004, STORY-009 — owner: retrieval-generation-engineer — note:
- [ ] STORY-023 — Chat message endpoint (full pipeline wiring, v1) — depends: STORY-020, STORY-021, STORY-022 — owner: retrieval-generation-engineer — note:
- [ ] STORY-024 — Frontend: auth pages wired to API — depends: STORY-006, STORY-007 — owner: frontend-engineer — note:
- [ ] STORY-025 — Frontend: chat UI with streaming + Markdown rendering — depends: STORY-023, STORY-024 — owner: frontend-engineer — note:

## Phase 2 — Tabular Q&A

- [ ] STORY-026 — ExcelLoader + CsvLoader with schema extraction — depends: STORY-011 — owner: ingestion-engineer — note:
- [ ] STORY-027 — TabularColumnProfile model + repository — depends: STORY-004, STORY-026 — owner: tabular-qa-engineer — note:
- [ ] STORY-028 — Column profiler service (LLM-generated descriptions) — depends: STORY-019, STORY-026, STORY-027 — owner: tabular-qa-engineer — note:
- [ ] STORY-029 — Tabular store (structured row persistence) — depends: STORY-026 — owner: tabular-qa-engineer — note:
- [ ] STORY-030 — Column-selection strategy — depends: STORY-027, STORY-028 — owner: tabular-qa-engineer — note:
- [ ] STORY-031 — Row-lookup answer mode — depends: STORY-029, STORY-030 — owner: tabular-qa-engineer — note:
- [ ] STORY-032 — RAG-over-serialized-rows answer mode — depends: STORY-016, STORY-017, STORY-029, STORY-030 — owner: tabular-qa-engineer — note:
- [ ] STORY-033 — TabularRetriever + generation integration — depends: STORY-021, STORY-030, STORY-031, STORY-032 — owner: tabular-qa-engineer — note:
- [ ] STORY-034 — Frontend: tabular source UI affordances — depends: STORY-025, STORY-033 — owner: frontend-engineer — note:

## Phase 3 — Safety & Routing Pipeline

- [ ] STORY-035 — Validation pipeline framework (Chain of Responsibility runner) — depends: STORY-023 — owner: safety-pipeline-engineer — note:
- [ ] STORY-036 — Schema validation handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-037 — Sanitization handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-038 — PII/secret detection & masking handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-039 — Prompt-injection / jailbreak screening handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-040 — Content moderation handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-041 — Rate limiting handler (Redis token bucket) — depends: STORY-014, STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-042 — Intent classification handler — depends: STORY-035 — owner: safety-pipeline-engineer — note:
- [ ] STORY-043 — MessageRouter (intent-based dispatch) — depends: STORY-023, STORY-033, STORY-042 — owner: safety-pipeline-engineer — note:
- [ ] STORY-044 — Wire full safety pipeline into chat endpoint — depends: STORY-036, STORY-037, STORY-038, STORY-039, STORY-040, STORY-041, STORY-043 — owner: safety-pipeline-engineer — note:

## Phase 4 — Multi-provider Configurability

- [ ] STORY-045 — MongoDB repository implementations (Motor) — depends: STORY-004, STORY-009, STORY-022, STORY-027 — owner: platform-core-engineer — note:
- [ ] STORY-046 — S3Storage implementation — depends: STORY-005 — owner: platform-core-engineer — note:
- [ ] STORY-047 — GcsStorage + AzureBlobStorage implementations — depends: STORY-005 — owner: platform-core-engineer — note:
- [ ] STORY-048 — Additional ILLMProvider implementations — depends: STORY-019 — owner: retrieval-generation-engineer — note:
- [ ] STORY-049 — Config-driven runtime switching (DI wiring) — depends: STORY-003, STORY-045, STORY-046, STORY-047, STORY-048 — owner: platform-core-engineer — note:
- [ ] STORY-050 — Admin config API — depends: STORY-006, STORY-049 — owner: platform-core-engineer — note:
- [ ] STORY-051 — Frontend: admin config UI — depends: STORY-024, STORY-050 — owner: frontend-engineer — note:

## Phase 5 — Billing & Subscriptions

- [ ] STORY-052 — Plan model + repository + GET /api/plans — depends: STORY-004, STORY-045 — owner: billing-engineer — note:
- [ ] STORY-053 — IPaymentProvider interface + StripeProvider — depends: STORY-006 — owner: billing-engineer — note:
- [ ] STORY-054 — Subscription & Invoice models + repository — depends: STORY-045, STORY-052 — owner: billing-engineer — note:
- [ ] STORY-055 — Checkout session + webhook endpoints (Stripe) — depends: STORY-053, STORY-054 — owner: billing-engineer — note:
- [ ] STORY-056 — Usage metering / quota enforcement middleware — depends: STORY-041, STORY-052, STORY-054 — owner: billing-engineer — note:
- [ ] STORY-057 — RazorpayProvider + PayPalProvider — depends: STORY-053 — owner: billing-engineer — note:
- [ ] STORY-058 — Frontend: billing/subscription pages — depends: STORY-024, STORY-052, STORY-055 — owner: frontend-engineer — note:

## Phase 6 — Hardening

- [ ] STORY-059 — Contract test suite consolidation for all interfaces — depends: STORY-045, STORY-048, STORY-053, STORY-057 — owner: devops-observability-engineer — note:
- [ ] STORY-060 — Integration tests with testcontainers (full sweep) — depends: STORY-059 — owner: devops-observability-engineer — note:
- [ ] STORY-061 — E2E API test: upload → ingest → chat → answer — depends: STORY-044 — owner: devops-observability-engineer — note:
- [ ] STORY-062 — Frontend Playwright E2E suite — depends: STORY-034, STORY-058 — owner: frontend-engineer — note:
- [ ] STORY-063 — Observability (OpenTelemetry, Prometheus, structured logs) — depends: STORY-023 — owner: devops-observability-engineer — note:
- [ ] STORY-064 — Security review & audit logging completeness — depends: STORY-050, STORY-056 — owner: devops-observability-engineer — note:
- [ ] STORY-065 — SEO / performance audit + Lighthouse CI gate — depends: STORY-007, STORY-025 — owner: devops-observability-engineer — note:
- [ ] STORY-066 — Documentation: ADRs, runbooks, module READMEs — depends: STORY-004, STORY-005, STORY-019, STORY-029, STORY-053 — owner: docs-writer — note:

## Totals

66 stories tracked (STORY-001…STORY-066). Owner distribution: platform-core-engineer 9,
ingestion-engineer 7, retrieval-generation-engineer 9, tabular-qa-engineer 7, safety-pipeline-engineer
10, billing-engineer 6, frontend-engineer 7, devops-observability-engineer 10, docs-writer 1.

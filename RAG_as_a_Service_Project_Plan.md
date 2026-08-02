# RAG-as-a-Service (RaaS) — Complete Project Plan

## 0. Document Purpose
This is a full engineering plan for a multi-tenant **RAG-as-a-Service** platform: ingestion, processing, retrieval, generation, chat history, auth, payments/subscriptions, and a Next.js frontend — all built around configurable, swappable strategies (DB, storage, LLM provider, payment provider) with SOLID principles and standard design patterns applied throughout.

Stack: **Python 3.11+, FastAPI, LangChain, PostgreSQL + MongoDB (configurable), Next.js 15, React, Tailwind CSS**.

---

## 1. Goals & Non-Goals

**Goals**
- Ingest PDF, DOCX, XLSX, CSV, TXT (extensible to new types without touching core code).
- Column-aware Q&A for tabular files (XLSX/CSV); direct RAG for unstructured text (TXT/PDF/DOCX).
- Fully configurable persistence: relational (Postgres) or document (MongoDB), switchable via config.
- Fully configurable file storage: local disk / S3 / GCS / Azure Blob — strategy read from MongoDB config collection.
- Fully configurable LLM provider: OpenAI / Anthropic / Azure OpenAI / local (Ollama) — switchable per tenant/config.
- Fully configurable payment provider: Stripe / Razorpay / PayPal — switchable via strategy.
- Chat history persisted for every conversation, replayable, exportable.
- Multi-layer input validation, prompt-injection defense, PII/secret masking, intent classification & routing.
- Markdown-capable generation output.
- Auth (signup/login, password hashing, JWT/session), subscription plans stored in DB and exposed via API.
- SEO-optimized public marketing pages + authenticated product portal.
- Full test suite (unit/integration/e2e), and thorough documentation.

**Non-Goals (v1)**
- Real-time collaborative editing of documents.
- On-prem GPU fine-tuning pipeline (v1 uses hosted/inference LLM providers only).
- Mobile native apps (responsive web only).

---

## 2. High-Level Architecture

```
                        ┌───────────────────────────────────────────┐
                        │              Next.js 15 Frontend            │
                        │  Marketing (SEO) | Auth | Chat | Billing     │
                        └───────────────────┬───────────────────────┘
                                            │ HTTPS / REST (OpenAPI)
                        ┌───────────────────▼───────────────────────┐
                        │                FastAPI Gateway              │
                        │  AuthN/AuthZ | Rate limit | Input Pipeline   │
                        └───┬───────┬────────┬─────────┬─────────┬───┘
                            │       │        │         │         │
                 ┌──────────▼┐ ┌────▼────┐ ┌─▼───────┐ ┌▼───────┐ ┌▼────────┐
                 │ Ingestion │ │Processing│ │Retrieval│ │Generation│ │Billing │
                 │  Module   │ │  Module  │ │ Module  │ │ Module  │ │ Module │
                 └─────┬─────┘ └────┬─────┘ └────┬────┘ └────┬────┘ └───┬────┘
                       │            │            │            │          │
              ┌────────▼────────────▼────────────▼────────────▼──────────▼───┐
              │              Core Abstraction Layer (Ports)                   │
              │  IDatabase | IStorage | ILLMProvider | IPaymentProvider        │
              │  IVectorStore | IEmbeddingProvider                            │
              └────────┬─────────────────┬───────────────┬────────────────────┘
                       │                 │               │
             ┌─────────▼───┐   ┌─────────▼────┐   ┌──────▼───────┐
             │ Postgres /  │   │ Local FS / S3 │   │ OpenAI /     │
             │ MongoDB     │   │ / GCS / Azure │   │ Anthropic /  │
             │ (config-    │   │ (config-      │   │ Azure /      │
             │  driven)    │   │  driven)      │   │ Ollama       │
             └─────────────┘   └───────────────┘   └──────────────┘
                       │
             ┌─────────▼────────────┐
             │ Vector DB (Qdrant /  │
             │ pgvector / Chroma)   │
             └──────────────────────┘
```

Cross-cutting: Config Service (backed by MongoDB `system_config` collection), Observability (structured logs, tracing, metrics), Background Workers (Celery/RQ + Redis) for ingestion/embedding jobs.

---

## 3. Tech Stack

| Layer | Choice | Notes |
|---|---|---|
| API Framework | FastAPI | async, OpenAPI auto-docs, pydantic validation |
| Orchestration | LangChain (LCEL) | chains for ingestion, retrieval, generation |
| Relational DB | PostgreSQL (+ pgvector optional) | via SQLAlchemy 2.0 (async) + Alembic migrations |
| Document DB | MongoDB | via Motor (async driver) |
| Vector Store | Qdrant (default), pluggable | abstracted behind `IVectorStore` |
| Cache/Queue | Redis + Celery | background ingestion, rate limiting, session cache |
| Object Storage | Local FS / S3 / GCS / Azure Blob | abstracted behind `IStorageService` |
| Auth | JWT (access+refresh) via `python-jose`, `passlib[bcrypt]` | optional OAuth2 social login later |
| Payments | Stripe (default), Razorpay, PayPal | abstracted behind `IPaymentProvider` |
| Frontend | Next.js 15 (App Router), React 19, Tailwind CSS | SSR/SSG for SEO, CSR for chat app |
| Testing (BE) | pytest, pytest-asyncio, httpx, factory_boy, testcontainers | |
| Testing (FE) | Jest/Vitest + React Testing Library, Playwright (e2e) | |
| Docs | MkDocs (or Docusaurus) + auto-generated OpenAPI + ADRs | |
| CI/CD | GitHub Actions, Docker, Docker Compose, (optional) K8s Helm charts | |
| Observability | OpenTelemetry, Prometheus, Grafana, structured JSON logs | |

---

## 4. Domain Module Breakdown

### 4.1 Ingestion Module
Responsibilities: accept uploaded file → validate type/size → detect file type → dispatch to the correct **Loader Strategy** → persist raw file via `IStorageService` → persist metadata via `IDatabase` → enqueue background processing job.

- **Design pattern:** Strategy + Factory. `LoaderFactory.get_loader(file_type) -> BaseLoader`.
- Loaders: `PdfLoader`, `DocxLoader`, `ExcelLoader`, `CsvLoader`, `TextLoader`, each implementing `BaseLoader.load(file) -> RawDocument`.
- Adding a new file type = add one new `BaseLoader` subclass + register in factory map (Open/Closed Principle — no existing code touched).
- Tabular files (XLSX/CSV): loader extracts **schema** (column names, inferred types, sample rows) and stores this schema alongside the document metadata — needed later for column-aware Q&A.

### 4.2 Processing Module
Responsibilities: chunking, cleaning, embedding, and (for tabular files) column-mapping.

- **Text/PDF/DOCX pipeline:** clean → split (`RecursiveCharacterTextSplitter`, tunable per doc type) → embed (`IEmbeddingProvider`) → upsert into `IVectorStore` with metadata (`doc_id`, `chunk_id`, `source`, `page`).
- **Tabular pipeline (XLSX/CSV):**
  - Store the table as structured rows in a dedicated `tabular_store` (Postgres table per dataset, or a DataFrame cached in object storage as Parquet).
  - Build a lightweight **column profiler**: column name, dtype, sample values, and an LLM-generated semantic description of each column (e.g. "this column represents monthly revenue").
  - At query time this profile is used by the **Column Selection strategy** (see 4.4) to decide which column(s) answer the question — via either (a) a deterministic keyword/embedding match between question and column descriptions, or (b) an LLM function-call that receives the schema and returns the target column(s)/aggregation.
  - Two answer modes: **row-lookup** (filter/aggregate with pandas, deterministic) or **RAG-over-serialized-rows** (rows converted to text chunks for semantic search) — chosen based on whether the question is analytical (sum/avg/filter) vs descriptive.
- **Design pattern:** Pipeline/Chain-of-Responsibility for the processing steps; Template Method for the shared "extract → transform → load" skeleton with per-file-type hooks.

### 4.3 Retrieval Module
- Wraps `IVectorStore` + optional `IKeywordSearch` (BM25/Elastic) → **Hybrid Retriever**.
- Retrieval Strategy interface: `SemanticRetriever`, `HybridRetriever`, `TabularRetriever` (delegates to processing module's row-lookup for tabular sources).
- Re-ranking step (optional cross-encoder) before hand-off to Generation.
- **Design pattern:** Strategy (retriever type chosen by document type / tenant config) + Decorator (re-ranking wraps base retriever).

### 4.4 Generation Module
- LangChain LCEL chain: `Prompt → LLM (via ILLMProvider) → OutputParser`.
- `ILLMProvider` implementations: `OpenAIProvider`, `AnthropicProvider`, `AzureOpenAIProvider`, `OllamaProvider` — chosen via Factory based on tenant/system config (model name, temperature, max_tokens all config-driven).
- Output always requested/parsed as Markdown (headings, lists, tables, code blocks) — a `MarkdownOutputParser` validates/normalizes.
- For tabular questions: generation chain receives the column-selection result + computed aggregate/rows and produces a natural-language + Markdown-table answer.
- **Design pattern:** Factory (provider selection), Builder (assembling the LCEL chain with optional steps: citations, safety post-filter, markdown formatting).

### 4.5 Chat/Conversation Module
- Every user message + assistant response + retrieved sources + intent + latency + token usage stored (Postgres `conversations`/`messages` tables, or Mongo `conversations` collection depending on active DB strategy).
- Conversation history retrievable for context-window construction (windowed + summarized long-term memory using LangChain memory abstractions).
- Endpoints: list conversations, get conversation, export conversation (Markdown/PDF), delete conversation.

### 4.6 Input Validation, Safety & Routing Pipeline
A **Chain of Responsibility** pipeline every inbound chat message passes through, in order:
1. **Schema validation** (Pydantic) — length limits, encoding, required fields.
2. **Sanitization** — strip control chars, normalize unicode, HTML-escape if rendered.
3. **PII / secret detection & masking** — regex + NER (e.g. Microsoft Presidio or custom) detects emails, phone numbers, card numbers, API keys/tokens, passwords; masks them (`sk-live-***MASKED***`) before logging or forwarding to the LLM, with an audit trail of what was masked (not the raw value).
4. **Prompt-injection / jailbreak screening** — heuristic + classifier check against known injection patterns before the message reaches retrieval/generation.
5. **Content moderation** — moderation endpoint (provider-specific, abstracted behind `IModerationProvider`) blocks disallowed content categories.
6. **Rate limiting / abuse throttling** — per-user/per-tenant token bucket (Redis).
7. **Intent classification** — lightweight classifier (rules first, LLM fallback) tags message as e.g. `qa_document`, `qa_tabular`, `chitchat`, `account_billing_query`, `unsupported`.
8. **Routing** — a `MessageRouter` (Strategy) dispatches by intent: document/tabular intents → Retrieval+Generation pipeline; billing intents → a scoped, non-RAG assistant/FAQ handler; chitchat → direct lightweight LLM response without retrieval.
- Every step is a small, independently testable, independently swappable `Handler` — new checks can be inserted without changing the pipeline runner (Open/Closed).

### 4.7 Auth & User Module
- Signup/login with hashed passwords (bcrypt via passlib), JWT access + refresh tokens, optional email verification.
- `User`, `Role`, `Session` models; RBAC (`admin`, `member`, `owner`) for multi-tenant orgs.
- Endpoints behind FastAPI dependency-injected `get_current_user`.

### 4.8 Subscription & Payment Module
- `Plan` entity (name, price, quota — e.g. max docs, max tokens/month, max seats) stored in DB, exposed via `GET /api/plans`.
- `IPaymentProvider` interface: `create_checkout_session`, `handle_webhook`, `cancel_subscription`, `get_invoice`. Implementations: `StripeProvider`, `RazorpayProvider`, `PayPalProvider` — each isolated in its own module implementing the same interface; active provider chosen via config (Factory + Strategy).
- Webhook endpoint per provider verifies signature, updates `Subscription` + `Invoice` tables, and enforces plan quotas at the API-gateway layer (usage metering middleware).

### 4.9 Configurable Persistence Layer
- `IDatabase`/repository interfaces defined per aggregate (`IUserRepository`, `IConversationRepository`, `IDocumentRepository`, ...).
- Two concrete implementations per repository: `PostgresXRepository` (SQLAlchemy) and `MongoXRepository` (Motor).
- `RepositoryFactory` reads `active_db = "postgres" | "mongo"` from the **system config** and returns the correct implementation — rest of the app codes only against the interface (Dependency Inversion Principle).
- Config precedence: `system_config` collection in MongoDB (single source of truth for runtime-tunable settings) → environment variables (bootstrap/infra-level settings, e.g. DB connection strings) → `.env` defaults for local dev.

### 4.10 Configurable Storage Layer
- `IStorageService`: `save(file) -> uri`, `read(uri) -> bytes`, `delete(uri)`, `get_presigned_url(uri)`.
- Implementations: `LocalFsStorage`, `S3Storage`, `GcsStorage`, `AzureBlobStorage`.
- Active strategy + bucket/path settings pulled from MongoDB `system_config.storage` document, cached in-process with a short TTL and refreshed on config change (via pub/sub or polling).

---

## 5. Design Principles & Patterns Map

| Principle/Pattern | Where Applied |
|---|---|
| Single Responsibility | Each loader/handler/provider does exactly one job |
| Open/Closed | New file types, DBs, LLMs, payment providers added via new classes, no core edits |
| Liskov Substitution | All `Base*` interfaces are strictly substitutable (loaders, providers, repositories) |
| Interface Segregation | Narrow interfaces (`IEmbeddingProvider` separate from `ILLMProvider`, not one giant `IAIProvider`) |
| Dependency Inversion | FastAPI dependency-injection wires concrete implementations behind interfaces at startup, from config |
| Factory | `LoaderFactory`, `LLMProviderFactory`, `PaymentProviderFactory`, `RepositoryFactory` |
| Strategy | Retrieval strategy, DB strategy, storage strategy, column-selection strategy |
| Chain of Responsibility | Input validation/safety pipeline |
| Template Method | Shared ETL skeleton for ingestion across file types |
| Builder | LCEL generation chain assembly |
| Decorator | Retriever re-ranking wrapper, caching wrapper around LLM calls |
| Repository | All persistence access abstracted from business logic |
| Observer/Pub-Sub | Config change notifications, webhook event fan-out |

---

## 6. Core Data Models (logical, DB-agnostic)

- **User**(id, email, hashed_password, name, role, org_id, created_at)
- **Organization/Tenant**(id, name, active_plan_id, storage_strategy, db_strategy, llm_provider, payment_provider)
- **Document**(id, org_id, filename, file_type, storage_uri, schema_json[nullable], status, uploaded_by, created_at)
- **DocumentChunk** (in vector store, metadata: doc_id, chunk_id, page, text_hash)
- **TabularColumnProfile**(id, document_id, column_name, dtype, description, sample_values)
- **Conversation**(id, org_id, user_id, title, created_at, updated_at)
- **Message**(id, conversation_id, role, content_markdown, intent, sources_json, masked_entities_json, tokens_used, latency_ms, created_at)
- **Plan**(id, name, price_cents, currency, interval, quotas_json)
- **Subscription**(id, org_id, plan_id, provider, provider_subscription_id, status, current_period_end)
- **Invoice**(id, subscription_id, provider_invoice_id, amount, status, issued_at)
- **SystemConfig** (Mongo doc): `{ db: {active}, storage: {active, ...}, llm: {active, model, ...}, payment: {active, ...} }`

---

## 7. API Surface (high level)

```
POST   /api/auth/signup
POST   /api/auth/login
POST   /api/auth/refresh
GET    /api/me

POST   /api/documents/upload
GET    /api/documents
GET    /api/documents/{id}
DELETE /api/documents/{id}

POST   /api/chat/{conversation_id?}/message      # runs full pipeline
GET    /api/conversations
GET    /api/conversations/{id}
DELETE /api/conversations/{id}

GET    /api/plans
POST   /api/billing/checkout-session
POST   /api/billing/webhook/{provider}
POST   /api/billing/cancel

GET    /api/admin/config           # system_config (admin only)
PUT    /api/admin/config
```

All endpoints documented automatically via FastAPI's OpenAPI schema; hand-written docs supplement with "why", not just "what".

---

## 8. Suggested Repository / Folder Structure

```
raas/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── core/                # config loader, security, DI container
│   │   ├── api/                 # routers per domain (auth, documents, chat, billing, admin)
│   │   ├── domain/
│   │   │   ├── ingestion/       # loaders, LoaderFactory
│   │   │   ├── processing/      # chunkers, embedders, column_profiler
│   │   │   ├── retrieval/       # retrievers
│   │   │   ├── generation/      # chains, prompt templates, providers
│   │   │   ├── safety/          # validation pipeline handlers
│   │   │   ├── chat/            # conversation/message services
│   │   │   ├── billing/         # payment providers, plan service
│   │   │   └── users/           # auth/user service
│   │   ├── infrastructure/
│   │   │   ├── db/postgres/     # SQLAlchemy models, session, repos
│   │   │   ├── db/mongo/        # Motor models, repos
│   │   │   ├── storage/         # local/s3/gcs/azure implementations
│   │   │   └── vectorstore/     # qdrant/pgvector implementations
│   │   └── workers/             # Celery tasks (ingestion, embedding)
│   ├── tests/
│   │   ├── unit/
│   │   ├── integration/
│   │   └── e2e/
│   ├── alembic/                 # postgres migrations
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app/                     # Next.js 15 App Router
│   │   ├── (marketing)/         # SEO landing, pricing, blog
│   │   ├── (auth)/              # login, signup
│   │   ├── (portal)/            # dashboard, chat, documents, billing
│   │   └── api/                 # (only if BFF routes needed)
│   ├── components/              # shared, modular, atomic-design structure
│   ├── features/                # feature-sliced: chat/, documents/, billing/, auth/
│   ├── lib/                     # api client, hooks, utils
│   ├── styles/
│   ├── tests/
│   ├── package.json
│   └── next.config.js
├── docs/                        # architecture docs, ADRs, runbooks
└── docker-compose.yml
```

---

## 9. Frontend Plan (Next.js 15 + React + Tailwind)

- **App Router with route groups**: `(marketing)` for SEO pages (SSG/ISR, metadata API for title/description/OG tags, sitemap.xml + robots.txt generated), `(auth)`, `(portal)` for the authenticated app (CSR-heavy, client components for chat streaming).
- **Feature-sliced modular architecture**: each feature (`chat`, `documents`, `billing`, `auth`) owns its components, hooks, API calls, and types — avoids a god-level `components/` folder.
- Server Components by default; Client Components only where interactivity/state is required (chat window, file upload, forms).
- Streaming chat responses via server-sent events / fetch streaming, rendered with a Markdown renderer (`react-markdown` + `remark-gfm` for tables/task lists, `rehype-highlight` for code blocks).
- File upload widget: drag-drop, progress bar, client-side type/size pre-validation mirroring backend validation.
- Design system: Tailwind config with design tokens (colors, spacing, typography) centralized; reusable primitives (Button, Card, Modal, Table) in `components/ui`.
- SEO: `generateMetadata` per page, JSON-LD structured data for pricing/organization, dynamic OG images, Core Web Vitals budget enforced in CI (Lighthouse CI).

---

## 10. Testing Strategy

- **Backend**
  - Unit tests per loader, per provider, per handler in the safety pipeline (mock external calls).
  - Contract tests: each `I*Provider`/`I*Repository` implementation runs the same test suite (shared test base class) to guarantee interchangeability (Liskov compliance verified in CI).
  - Integration tests with `testcontainers` spinning real Postgres/Mongo/Redis for repository and pipeline tests.
  - E2E API tests via `httpx.AsyncClient` against a running FastAPI test app, covering upload → ingest → chat → answer.
  - Golden-file tests for tabular column-selection logic (given schema+question, assert expected column chosen).
- **Frontend**
  - Component/unit tests (Vitest + React Testing Library) per feature.
  - Playwright e2e: signup → upload doc → ask question → see markdown answer → subscribe to plan (mocked payment provider in test mode).
- **CI Gates**: lint (ruff/eslint), type-check (mypy/ts), unit+integration tests, coverage threshold, Lighthouse budget, Docker image build.

---

## 11. Security & Compliance Checklist

- Passwords: bcrypt, never logged; JWT secrets rotated via config, short-lived access tokens + refresh tokens with rotation/blacklist.
- Secrets (API keys, DB creds) via environment/secret manager, never in MongoDB `system_config` in plaintext — store references/encrypted values (e.g. via KMS) if provider secrets must live in config.
- All PII masked before persisting logs and before sending to third-party LLM providers where feasible (configurable masking policy).
- Payment webhooks: signature verification per provider, idempotency keys on webhook processing.
- Rate limiting + WAF-style input checks at gateway.
- Principle of least privilege for org/role-based access (RBAC).
- Audit log for admin config changes and data deletions.

---

## 12. Scalability Considerations

- Stateless FastAPI instances behind a load balancer; horizontal scaling.
- Heavy ingestion/embedding work offloaded to Celery workers (separate scaling group from API).
- Vector store and relational/document DB scaled independently; read replicas for Postgres if needed.
- Config caching (short TTL) to avoid hammering MongoDB `system_config` on every request.
- Multi-tenant isolation at the data layer (org_id scoping on every query) to allow future sharding.
- Idempotent, retryable background jobs (Celery + dead-letter queue) for ingestion resilience.

---

## 13. Documentation Plan

- `docs/architecture.md` — this plan, kept current.
- `docs/adr/` — Architecture Decision Records for each major choice (e.g. "why Strategy pattern for DB", "why Qdrant").
- Auto-generated OpenAPI docs (`/docs`, `/redoc`) plus a curated `docs/api-guide.md` with real request/response examples.
- `docs/runbooks/` — operational runbooks (rotating LLM provider, adding a new file loader, adding a new payment provider).
- Docstrings enforced via lint rule (pydocstyle) on all public classes/functions.
- README per package (`backend/app/domain/ingestion/README.md`, etc.) explaining the module's contract.

---

## 14. Phased Delivery Roadmap

**Phase 0 — Foundations (1–2 wks)**
Repo scaffolding, CI/CD, config service, `IDatabase`/`IStorage` interfaces + one concrete impl each (Postgres + Local FS), auth module, base Next.js app shell with SEO shell pages.

**Phase 1 — Core RAG (2–3 wks)**
Ingestion for TXT/PDF/DOCX, processing/embedding, vector store integration, retrieval + generation chain with one LLM provider, chat endpoint + persisted history, basic chat UI with markdown rendering.

**Phase 2 — Tabular Q&A (1–2 wks)**
Excel/CSV loaders, column profiler, column-selection strategy, row-lookup + tabular RAG answer modes, UI affordances for tabular sources.

**Phase 3 — Safety & Routing Pipeline (1–2 wks)**
Full validation chain: sanitization, PII/secret masking, injection screening, moderation, rate limiting, intent classification + routing.

**Phase 4 — Multi-provider Configurability (1–2 wks)**
Second DB impl (Mongo), second/third storage impl (S3), multiple LLM providers, config-driven switching + admin config UI.

**Phase 5 — Billing & Subscriptions (1–2 wks)**
Plans in DB + API, Stripe integration first, webhook handling, billing/subscription frontend pages, usage metering against plan quotas.

**Phase 6 — Hardening (ongoing)**
Additional payment providers, full test coverage, load testing, security review, docs polish, SEO/performance audit.

---

## 15. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| Tabular column-selection picks wrong column | Combine deterministic schema-embedding match + LLM function-calling fallback; log low-confidence picks for human review |
| Vendor lock-in on LLM/payment/storage | Strict interface boundaries from day 1; contract tests ensure any new provider is drop-in |
| PII leakage to third-party LLM | Mask before sending; keep an allow-list of what may leave the perimeter, configurable per tenant |
| Config drift (Mongo config vs env) | Config precedence clearly documented; validation on config write; admin UI diff/preview before applying |
| Runaway costs from unmetered usage | Enforce plan quotas at gateway middleware, not just billing after the fact |

---

## 16. Sample `requirements.txt` (backend, pinned)

```
fastapi==0.115.0
uvicorn[standard]==0.30.6
pydantic==2.9.2
pydantic-settings==2.5.2
sqlalchemy==2.0.35
alembic==1.13.3
asyncpg==0.29.0
motor==3.5.1
redis==5.0.8
celery==5.4.0
langchain==0.3.1
langchain-community==0.3.1
langchain-openai==0.2.1
langchain-anthropic==0.2.1
qdrant-client==1.11.2
pgvector==0.3.4
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4
python-multipart==0.0.9
stripe==10.10.0
pandas==2.2.2
openpyxl==3.1.5
pypdf==4.3.1
python-docx==1.1.2
presidio-analyzer==2.2.355
presidio-anonymizer==2.2.355
httpx==0.27.2
tenacity==9.0.0
structlog==24.4.0
opentelemetry-sdk==1.27.0
pytest==8.3.3
pytest-asyncio==0.24.0
testcontainers==4.8.1
factory-boy==3.3.1
mypy==1.11.2
ruff==0.6.9
```

*(Exact versions should be re-verified against latest stable releases at implementation time; pin via `pip freeze` into `requirements.txt` once the venv is finalized, and split into `requirements.txt` + `requirements-dev.txt`.)*

---

## 17. Next Steps

1. Confirm default choices where you have no strong preference (e.g. Qdrant vs pgvector, Stripe-first).
2. Set up repo skeleton (Phase 0) and the four core interfaces (`IDatabase`, `IStorage`, `ILLMProvider`, `IPaymentProvider`) with one implementation each — this is the highest-leverage foundational work since everything else plugs into it.
3. Write ADRs for each of the four abstraction decisions before writing implementation code, so the contracts are settled first.

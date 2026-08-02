# Story → agent routing table

Source of truth for which `.claude/agents/*.md` subagent owns each `STORY-NNN`. Used by `/work-story` to
resolve the agent, and to generate `docs/progress/STORY_STATUS.md`. If a routing decision here ever
looks wrong for a specific story, fix it here first, then re-generate the status board — don't just
route around it one-off in a command.

Routing is by **domain skill**, not strictly by backlog phase — frontend, infra/CI, and hardening
stories are pulled out cross-cutting even though the backlog numbers them alongside other phases.

## `platform-core-engineer`
STORY-003, STORY-004, STORY-005, STORY-006, STORY-045, STORY-046, STORY-047, STORY-049, STORY-050

Config service & precedence; `IUserRepository`/Postgres pattern; `IStorageService`/LocalFs; auth/JWT;
Mongo repo implementations (all interfaces); S3/GCS/Azure storage implementations; runtime config-switch
wiring; admin config API. This agent effectively owns `app/core/`, the repository/storage/config
interfaces in `app/domain/**` + `infrastructure/db/**` + `infrastructure/storage/**`, and their registry
factories.

## `ingestion-engineer`
STORY-009, STORY-010, STORY-011, STORY-012, STORY-013, STORY-015, STORY-026

`Document` model/repo; upload endpoint; `BaseLoader`/`LoaderFactory`; Text/Pdf/Docx loaders; chunking
pipeline (Template Method ETL skeleton); Excel/Csv loaders with schema extraction. Owns
`app/domain/ingestion/**`.

## `retrieval-generation-engineer`
STORY-016, STORY-017, STORY-018, STORY-019, STORY-020, STORY-021, STORY-022, STORY-023, STORY-048

`IEmbeddingProvider`/OpenAI; `IVectorStore`/Qdrant; wiring chunks→embeddings→vectors; `ILLMProvider`/
OpenAI + later Anthropic/Azure/Ollama; `IRetriever`/`SemanticRetriever`; LCEL generation chain +
`MarkdownOutputParser`; `Conversation`/`Message` models; the v1 chat endpoint. Owns
`app/domain/{processing,retrieval,generation,chat}/**` (excluding the safety pipeline and tabular
answer modes, which are their own agents).

## `tabular-qa-engineer`
STORY-027, STORY-028, STORY-029, STORY-030, STORY-031, STORY-032, STORY-033

`TabularColumnProfile` model/repo; `ColumnProfilerService`; tabular row store; column-selection
strategy; row-lookup answerer; RAG-over-serialized-rows answerer; `TabularRetriever` +
generation integration. Consumes `ingestion-engineer`'s Excel/Csv loaders (STORY-026) and
`retrieval-generation-engineer`'s `ILLMProvider`/`IVectorStore`, but owns everything downstream of
schema extraction.

## `safety-pipeline-engineer`
STORY-035, STORY-036, STORY-037, STORY-038, STORY-039, STORY-040, STORY-041, STORY-042, STORY-043,
STORY-044

The entire Chain-of-Responsibility validation/safety/routing pipeline: runner, schema validation,
sanitization, PII masking, prompt-injection screening, content moderation, rate limiting, intent
classification, `MessageRouter`, and wiring it all into the chat endpoint. Owns `app/domain/safety/**`.

## `billing-engineer`
STORY-052, STORY-053, STORY-054, STORY-055, STORY-056, STORY-057

`Plan` model/repo + public endpoint; `IPaymentProvider`/Stripe; `Subscription`/`Invoice` models;
checkout/webhook/cancel endpoints; usage metering/quota middleware; Razorpay/PayPal providers. Owns
`app/domain/billing/**`. (Billing *frontend* pages are `frontend-engineer`'s, STORY-058.)

## `frontend-engineer`
STORY-007, STORY-024, STORY-025, STORY-034, STORY-051, STORY-058, STORY-062

Every `frontend/` story regardless of which backlog phase it's numbered under: app shell/SEO, auth
pages, chat UI, tabular source UI, admin config UI, billing UI, Playwright e2e. Owns `frontend/**`.

## `devops-observability-engineer`
STORY-001, STORY-002, STORY-008, STORY-014, STORY-059, STORY-060, STORY-061, STORY-063, STORY-064,
STORY-065

Repo/monorepo scaffolding; CI pipelines; docker-compose local dev; Celery/Redis worker infra; contract
test suite consolidation; testcontainers integration-test CI job; backend E2E API suite; observability
(OpenTelemetry/Prometheus/structured logs); security review & audit-log completeness; Lighthouse
CI/SEO budget. Owns `.github/workflows/**`, `docker-compose.yml`, `app/workers/**`, and cross-cutting
CI/test-infra config.

## `docs-writer`
STORY-066

Formal Phase-6 documentation consolidation: ADRs in `docs/adr/`, runbooks in `docs/runbooks/`, a
per-module `README.md` in each `backend/app/domain/*/`, and the `pydocstyle` CI gate. (Per-feature docs
for every other story are written by the implementing agent itself via the `feature-doc-writer` skill —
not routed here — so this agent isn't a bottleneck for routine stories.)

## Coverage check

9 + 7 + 9 + 7 + 10 + 6 + 7 + 10 + 1 = 66 — every `STORY-001`…`STORY-066` appears exactly once above.

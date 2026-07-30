# Story status board

One line per `STORY-NNN`. `- [ ]` = todo, `- [~]` = in_progress, `- [!]` = blocked, `- [x]` = done.

**Do not hand-edit the depends/owner columns** — they're generated from
`.claude/rules/story-routing.md` and `implementation_task.md`. Only the checkbox and the trailing note
change as work progresses. `/work-story` and `/story-status` read this file; agents update their own
story's row when they finish (see `.claude/rules/story-workflow.md`'s Definition of Done).

Format: `- [ ] STORY-NNN — Title — depends: ... — owner: agent-name — note: ...`

## Phase 0 — Foundations

- [ ] STORY-001 — Repository scaffolding & monorepo layout — depends: none — owner: devops-observability-engineer — note:
- [ ] STORY-002 — CI pipeline (lint, type-check, test scaffolding) — depends: STORY-001 — owner: devops-observability-engineer — note:
- [ ] STORY-003 — Config service & system_config precedence — depends: STORY-001 — owner: platform-core-engineer — note:
- [ ] STORY-004 — IDatabase/Repository interfaces + first Postgres repo (User) — depends: STORY-001 — owner: platform-core-engineer — note:
- [ ] STORY-005 — IStorageService interface + LocalFsStorage — depends: STORY-001 — owner: platform-core-engineer — note:
- [ ] STORY-006 — Auth module: signup/login/JWT — depends: STORY-004 — owner: platform-core-engineer — note:
- [ ] STORY-007 — Next.js app shell + SEO scaffolding — depends: STORY-001 — owner: frontend-engineer — note:
- [ ] STORY-008 — Local dev environment (docker-compose) — depends: STORY-001 — owner: devops-observability-engineer — note:

## Phase 1 — Core RAG

- [ ] STORY-009 — Document model + repository (Postgres) — depends: STORY-004 — owner: ingestion-engineer — note:
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

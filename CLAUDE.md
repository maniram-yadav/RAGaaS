# RAGaaS — Project Memory

RAGaaS (Retrieval-Augmented Generation as a Service) connects private data to LLMs: ingestion, vector
storage, retrieval, and generation behind a configurable, multi-tenant backend.

- Full architecture/design spec: [RAG_as_a_Service_Project_Plan.md](RAG_as_a_Service_Project_Plan.md)
- Story-by-story backlog (66 stories, `STORY-001`…`STORY-066`): [implementation_task.md](implementation_task.md)
- Live progress board: [docs/progress/STORY_STATUS.md](docs/progress/STORY_STATUS.md)
- Config reference: [docs/reference/configuration.md](docs/reference/configuration.md)

No application code exists yet — the repo currently holds the plan, the backlog, and the Claude Code
team infrastructure described below. Stories are implemented one at a time, on request.

## The team

Work is picked up **by story number**, never by vague area. Each agent below owns a fixed slice of the
backlog and must not touch stories outside its list. The full routing table (with per-story rationale)
lives in [.claude/rules/story-routing.md](.claude/rules/story-routing.md).

| Agent | Owns | Domain |
|---|---|---|
| `platform-core-engineer` | 003,004,005,006,045,046,047,049,050 | Config service, DB/storage interfaces+factories, auth, Mongo/S3/GCS/Azure swap-ins, admin config API |
| `ingestion-engineer` | 009,010,011,012,013,015,026 | Document model/upload, loaders, chunking pipeline |
| `retrieval-generation-engineer` | 016,017,018,019,020,021,022,023,048 | Embeddings, vector store, LLM providers, retriever, generation chain, chat endpoint |
| `tabular-qa-engineer` | 027,028,029,030,031,032,033 | Column profiling, tabular store, column-selection, tabular answerers |
| `safety-pipeline-engineer` | 035,036,037,038,039,040,041,042,043,044 | Validation chain, PII masking, injection screening, moderation, rate limit, intent routing |
| `billing-engineer` | 052,053,054,055,056,057 | Plans, payment providers, subscriptions/invoices, webhooks, quota metering |
| `frontend-engineer` | 007,024,025,034,051,058,062 | All Next.js work, Playwright e2e |
| `devops-observability-engineer` | 001,002,008,014,059,060,061,063,064,065 | Repo scaffold, CI, docker-compose, worker infra, contract/integration/e2e test infra, observability, security review, Lighthouse |
| `docs-writer` | 066 | ADRs, runbooks, module READMEs, pydocstyle gate |

To start a story: `/work-story STORY-NNN`. To see what's done/blocked: `/story-status`.

## Non-negotiable rules

1. **One story at a time.** An agent implements only the `STORY-NNN` it was given — never adjacent or
   future scope, even if convenient. If a dependency turns out to be missing, stop and flag it; do not
   reach ahead and implement it inline (see the backlog's own "What to do if a dependency looks wrong").
2. **Dependency Inversion.** All cross-module access goes through `app/domain/**` interfaces. Routers
   and other domains never import a concrete provider/repo directly.
3. **Open/Closed.** New capability = new class + a registry/factory entry. Never add branching
   (`if/elif`) to an existing factory to support a new type.
4. **Liskov.** Every class implementing a `Base*`/`I*` interface gets contract tests run against the
   shared base test suite where one already exists.
5. **Config is never hardcoded and never touches real secrets files.** Runtime-tunable config lives in
   `system_config` (Mongo) → env vars → `.env` defaults, in that precedence. The shape is documented in
   `config/system_config.example.json`. **No agent ever reads, writes, or edits a real `.env`** — only
   `.env.example`. See [.claude/rules/config-management.md](.claude/rules/config-management.md) and use
   the `add-config-key` skill to add a new key.
6. **Tests are mandatory and are never weakened to pass.** Every story ships with tests proving its
   acceptance criteria. If a test fails, fix the implementation and re-run — never delete, skip, or
   loosen a failing test to force green. See
   [.claude/rules/testing-standards.md](.claude/rules/testing-standards.md).
7. **Every completed feature gets a doc.** `docs/features/<name>.md`, written by the implementing agent
   from `docs/features/_TEMPLATE.md`.
8. **No secrets in `system_config` plaintext.** Reference `.env`/secret manager only.
9. **Commits stay human-gated.** Agents implement and test; they do not `git commit`/`git push` unless
   explicitly asked.

Full detail: [.claude/rules/](.claude/rules/) (`coding-standards.md`, `config-management.md`,
`testing-standards.md`, `story-workflow.md`, `story-routing.md`, `git-workflow.md`,
`documentation-standards.md`).

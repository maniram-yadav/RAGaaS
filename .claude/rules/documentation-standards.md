# Documentation standards

## Per-feature docs (every story)

Every completed feature/module gets exactly one file at `docs/features/<name>.md`, generated from
`docs/features/_TEMPLATE.md` by the `feature-doc-writer` skill, with these fixed sections:

1. **Overview** — one paragraph: what this feature does and why it exists (tie back to the plan
   section it implements).
2. **Interfaces / contracts** — exact class/interface names introduced or extended (must match the
   names used in `implementation_task.md`'s "Interfaces/contracts touched" for the story).
3. **Config knobs** — any `system_config` keys or env vars this feature reads, with a pointer to
   `docs/reference/configuration.md`.
4. **Testing** — where the tests live and what they cover (unit/integration/e2e/contract), and how to
   run them.
5. **Story references** — which `STORY-NNN`(s) this doc covers.

`<name>` is the module/feature name (e.g. `document-ingestion.md`, `pii-masking.md`,
`tabular-column-profiling.md`) — not the story id, since one doc often accumulates content across
several related stories (e.g. STORY-011/012/013 all land in `document-loaders.md`).

## ADRs and runbooks (STORY-066, `docs-writer`)

- `docs/adr/NNNN-title.md` — one ADR per major architectural decision (DB strategy, storage strategy,
  LLM provider strategy, tabular storage approach, payment provider strategy at minimum, per the
  backlog). Standard ADR shape: Context, Decision, Consequences, Alternatives considered.
- `docs/runbooks/*.md` — short, concrete walkthroughs referencing real class/story names (e.g.
  "rotating the active LLM provider", "adding a new file loader", "adding a new payment provider").
- Per-module `README.md` in each `backend/app/domain/*/` explaining that module's contract (what
  interfaces it exposes, what depends on it).

## General rule

Docs describe the *implemented* decision, not the plan's proposal — if reality diverged from
`RAG_as_a_Service_Project_Plan.md` during implementation, the doc reflects what was actually built and
notes the divergence.

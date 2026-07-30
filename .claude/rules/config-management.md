# Config management — the never-touch-real-`.env` rule

## Precedence (plan §4.9/§11)

1. `system_config` collection in MongoDB — single source of truth for **runtime-tunable** settings
   (which DB/storage/LLM/payment provider is active, model name, temperature, rate limits, ...). Read
   through `ConfigService.get(section)`, never queried directly by feature code.
2. Environment variables — bootstrap/infra-level settings (connection strings, ports).
3. `.env` defaults — local-dev fallback for the above.

`ConfigService` (STORY-003) is the only thing that resolves this chain. Everything downstream — every
factory (`RepositoryFactory`, `StorageFactory`, `LLMProviderFactory`, ...) — asks `ConfigService` for the
active strategy; it never reads env vars or files itself.

## The hard rule

**No agent, in any story, ever opens, reads, writes, or edits a real `.env` file (or any
`.env.local` / `.env.production` / secrets file).** This is enforced by `.claude/settings.json`
permission denies, but don't rely on that alone — it's a standing rule regardless of what the
permission layer allows.

The only files you touch when config needs to change:

- `.env.example` (root) — documents every bootstrap env var, with a comment. Add new keys here,
  never with real values.
- `config/system_config.example.json` — documents the shape of the `system_config` Mongo document.
  Add new keys/sections here when a story introduces a new runtime-tunable setting.
- `docs/reference/configuration.md` — human-readable explanation of every key in both files above.

Use the `add-config-key` skill to make this change consistently across all three files in one pass.

## Why this matters

`.env` (without `.example`) is git-ignored and, in any real deployment, holds live secrets (API keys, DB
passwords, JWT signing keys, Stripe keys). An agent reading it could leak a secret into a transcript,
log, or generated file; an agent editing it could silently break a running local environment or
overwrite a teammate's uncommitted values. The `.example` files carry 100% of the *shape* information a
story needs (which keys exist, what they're for) without any of the risk.

## Secrets never go in `system_config`

`system_config` (and therefore `config/system_config.example.json`) holds which provider is active and
its tunables — never the credential itself. If a provider needs a secret, it's read by that provider's
factory from an env var (bootstrap layer), not from `system_config`.

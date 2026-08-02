---
name: add-config-key
description: The only sanctioned way to add or change a configuration key in RAGaaS. Use whenever a story needs a new env var or a new system_config field. Updates config/system_config.example.json, .env.example, and docs/reference/configuration.md together — never touches a real .env.
---

# add-config-key

Keeps the three config-documentation files in sync whenever a story introduces a new configurable
setting. See `.claude/rules/config-management.md` for the full precedence/rationale.

## Hard rule, first

**Never open, read, or edit a real `.env` file (or `.env.local`, `.env.production`, any non-`.example`
variant).** This skill only ever touches `.env.example`. If a real `.env` exists in the working tree,
do not read it "just to check" — it is out of scope regardless of what it might contain.

## Procedure

1. **Decide which layer the new setting belongs to:**
   - Runtime-tunable (can change without a redeploy, e.g. active provider, model name, a limit) →
     `config/system_config.example.json`, under the appropriate section (`db`, `storage`, `llm`,
     `payment`, `vectorstore`, `safety`, or a new section if the story introduces a new domain).
   - Bootstrap/infra-level (connection string, secret, anything needed before `ConfigService` can even
     start) → `.env.example` only.
   - If it's a secret or credential of any kind, it is **always** `.env.example` (bootstrap layer) —
     never `config/system_config.example.json`, even if the surrounding setting is otherwise
     runtime-tunable. Store a reference/placeholder there instead if the two need to correlate.

2. **Edit `config/system_config.example.json` and/or `.env.example`** accordingly:
   - In the JSON file, add the key under its section with a placeholder/default value; add or extend the
     `_active_options`/inline documentation style already used in that file.
   - In `.env.example`, add the var under the relevant `# --- Section ---` comment block, with a short
     inline comment explaining it.

3. **Update `docs/reference/configuration.md`** — add the new key to the relevant table with: name,
   layer (system_config / env), purpose, default.

4. **Do not** create or modify a real `.env`, and do not assume one exists — your job ends at the
   `.example` templates and the reference doc. The human copies `.env.example` to `.env` and fills real
   values themselves.

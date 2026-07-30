# &lt;Feature name&gt;

<!-- Filled in by the feature-doc-writer skill when the owning agent completes a story. See
     .claude/rules/documentation-standards.md for the rules behind each section. -->

## Overview

One paragraph: what this feature does, why it exists, and which section of
`RAG_as_a_Service_Project_Plan.md` it implements.

## Interfaces / contracts

- `IExample` — ...
- `ExampleFactory` — ...

(Exact class/interface names, matching the story's "Interfaces/contracts touched.")

## Config knobs

- `system_config.<section>.<key>` — ...
- `EXAMPLE_ENV_VAR` — ...

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.

## Testing

- Location: `backend/tests/...` or `frontend/tests/...`
- Run with: `pytest ...` / `npm run test -- ...`
- Covers: ...

## Story references

- STORY-NNN — ...

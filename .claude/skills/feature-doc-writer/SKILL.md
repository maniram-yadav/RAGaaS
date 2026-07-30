---
name: feature-doc-writer
description: Use when a story reaches "done" (acceptance criteria met, tests green) to write or update that feature's doc under docs/features/. Fills docs/features/_TEMPLATE.md's fixed sections consistently so every feature is documented the same way.
---

# feature-doc-writer

Writes/updates the one `docs/features/<name>.md` file for a completed feature, per
`.claude/rules/documentation-standards.md`.

## Procedure

1. **Pick `<name>`** — the module/feature name, not the story id (e.g. `document-loaders`,
   `pii-masking`, `tabular-column-profiling`). Check `docs/features/` first: if a doc for this module
   already exists from an earlier related story, update it in place (append to "Story references",
   revise "Interfaces / contracts" and "Config knobs" if this story extended them) rather than creating
   a duplicate file.

2. **Read `docs/features/_TEMPLATE.md`** for the exact section structure to follow.

3. **Fill in every section**, sourced from what was actually built (read the code you just wrote, don't
   paraphrase the plan):
   - **Overview** — one paragraph, what and why, tying back to the relevant plan section.
   - **Interfaces / contracts** — exact class/interface names, matching
     `implementation_task.md`'s "Interfaces/contracts touched" for the story.
   - **Config knobs** — any `system_config` keys / env vars this feature reads; link to
     `docs/reference/configuration.md` rather than re-explaining precedence here.
   - **Testing** — where the tests live, what they cover, the exact command to run them.
   - **Story references** — the `STORY-NNN`(s) this doc covers (append new ones on updates).

4. **Write the file** to `docs/features/<name>.md`.

## What this skill does not do

It does not write ADRs, runbooks, or per-module domain `README.md` files — those are `docs-writer`'s
STORY-066 scope. It does not update `docs/progress/STORY_STATUS.md` — that's a separate step in the
calling agent's workflow.

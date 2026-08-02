---
description: Summarize the backlog progress board — counts by phase/status, and which stories are blocked or in progress.
---

Read `docs/progress/STORY_STATUS.md` and produce a concise summary for the user:

1. Overall counts: how many of the 66 stories are `done`, `in_progress`, `blocked`, and `todo`.
2. Per-phase breakdown (Phase 0–6), same counts, so the user can see which phase is furthest along.
3. List every story currently `in_progress` or `blocked`, with its one-line status note.
4. If any `todo` story's dependencies are now all `done` (i.e. it's newly unblocked and ready to pick up
   with `/work-story`), call those out as "ready to start."

Keep the summary tight — a table or short bullet list, not a restatement of the whole file.

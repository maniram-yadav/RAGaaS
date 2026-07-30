---
description: Pick up a single backlog story by number and dispatch it to the agent that owns it.
argument-hint: STORY-NNN
---

The user wants to start work on story `$ARGUMENTS`. Follow this procedure exactly — do not skip the
dependency check, and do not implement anything yourself in this command; your job here is routing and
verification, the actual implementation happens in the dispatched subagent.

1. **Normalize the id.** Accept `STORY-011`, `011`, or `11` and normalize to `STORY-0NN` (3-digit,
   zero-padded) form.

2. **Read the story.** Grep `implementation_task.md` for `### STORY-0NN` and read that section through
   to the next `---` — you need Goal, Context, Scope of work, Out of scope, Interfaces/contracts
   touched, Acceptance criteria, and Design pattern(s).

3. **Check dependencies.** Read `docs/progress/STORY_STATUS.md`, find this story's row, and read its
   `Depends on` list. For each dependency story, confirm its row's status is `done`. If any dependency
   is not `done`:
   - Stop. Do not dispatch any agent.
   - Report to the user exactly which dependency is missing and its current status.
   - If it looks like the backlog's own sequencing is off (a lower-numbered story secretly needs
     something from this one), say so explicitly per `implementation_task.md`'s own guidance — don't
     silently reorder anything.

4. **Resolve the owning agent.** Look up the story number in `.claude/rules/story-routing.md`'s table
   to find which of the 9 agents owns it.

5. **Dispatch.** Use the Agent tool with `subagent_type` set to the owning agent's name. Build a
   self-contained prompt containing: the full story text from step 2, an explicit instruction to work
   *only* this story, and reminders of the config rule (never touch a real `.env`) and the testing rule
   (write tests, use `test-and-refactor`, never weaken a test to pass). The agent already has its own
   system prompt covering its domain and the shared rules — you don't need to re-explain the whole
   ruleset, just anchor it to this specific story.

6. **After the agent reports back:** verify it actually updated `docs/progress/STORY_STATUS.md` for this
   story to `done` (or left it as `blocked`/`in_progress` with a clear reason if it didn't finish) and
   that a feature doc was written/updated. Relay the agent's summary and test results to the user. Do not
   commit anything yourself.

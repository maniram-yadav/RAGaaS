# Story workflow — how a story gets picked up and closed out

This is the procedure `/work-story` follows and that every agent must also self-check before and after
doing any work.

## Before starting STORY-NNN

1. Read the full story section for `STORY-NNN` from `implementation_task.md` (Goal, Context, Scope of
   work, Out of scope, Interfaces/contracts touched, Acceptance criteria, Design pattern(s)).
2. Read `docs/progress/STORY_STATUS.md`. Find `STORY-NNN`'s row and its `Depends on` list.
3. **Every** story in the `Depends on` list must show `done` in the status board. If any is `todo`,
   `in_progress`, or `blocked`, stop — do not start, do not implement the missing dependency inline.
   Report which dependency is missing and, per `implementation_task.md`'s own guidance, whether it looks
   like a sequencing problem worth flagging to the human.
4. Confirm the story is on **your** agent's ownership list (`story-routing.md`). If it isn't, stop and
   say which agent owns it instead.

## While working

- Implement **only** the "Scope of work" for this story. Anything under "Out of scope" is exactly
  that — do not build it even if it would be convenient to do now.
- Follow `coding-standards.md` for pattern choice and `config-management.md` for anything
  configuration-shaped.
- Write tests per `testing-standards.md` covering every line of "Acceptance criteria". Use the
  `test-and-refactor` skill to drive to green.
- If you discover, mid-story, that you need a capability only a **higher-numbered** story provides:
  stop. Do not reach ahead. Either stub the capability behind the existing interface (if the current
  story can be honestly completed that way) or report that the backlog's sequencing needs a look — never
  silently reorder or implement out of turn.

## Definition of done

A story is only `done` when **all** of the following hold:
- Every acceptance-criteria checkbox in `implementation_task.md` is genuinely satisfiable by the code
  (don't check a box you haven't verified).
- Tests exist for the story and pass.
- `docs/features/<name>.md` exists/updated via the `feature-doc-writer` skill.
- `docs/progress/STORY_STATUS.md`'s row for this story is updated to `done` with a one-line note (what
  was built, any follow-up flagged).
- No real `.env` file was read, written, or edited at any point (see `config-management.md`).

Do not `git commit` or `git push` as part of closing out a story unless the human explicitly asked for
that in this request — leave the working tree for human review (see `git-workflow.md`).

# Git workflow

- One story per branch: `story/STORY-NNN-short-slug` (e.g. `story/STORY-011-baseloader-textloader`).
- Commit messages reference the story id, e.g. `STORY-011: add BaseLoader interface, LoaderFactory, TextLoader`.
- A story's branch touches only files within that story's declared scope. If implementing STORY-NNN
  requires an incidental change outside that scope (e.g. a typo fix in an unrelated file you happened to
  open), call it out separately rather than folding it in silently.
- **Never commit or push automatically.** Implement, test, and report — the human decides when and how
  to commit. This holds even when a story reaches "done" per `story-workflow.md`; finishing a story is
  not, by itself, authorization to commit.
- Never force-push, rewrite history, or skip hooks (`--no-verify`) without the human explicitly asking.
- Parallel stories (see `implementation_task.md`'s "Parallelization quick-reference") are expected to
  live on separate branches worked by separate agent invocations; don't assume you own the whole repo
  tree when your story is one of a parallel set.

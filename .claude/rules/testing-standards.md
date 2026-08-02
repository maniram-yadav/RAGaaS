# Testing standards

Every story's acceptance criteria are proven by tests, not by manual reasoning. Plan §10 is the source
of truth for layout; this file is the operating discipline.

## Layout

- Backend: `backend/tests/{unit,integration,e2e}` (+ `backend/tests/contract/` for shared `I*`
  contract-test base classes, seeded in STORY-045/STORY-059).
  - `unit/` — one loader/provider/handler in isolation, external calls mocked (pytest, pytest-asyncio).
  - `integration/` — real Postgres/Mongo/Redis/Qdrant via `testcontainers`.
  - `e2e/` — `httpx.AsyncClient` against a running FastAPI test app, full flows.
  - `contract/` — a shared test base class per interface family, run against **every** concrete
    implementation of that interface (proves Liskov substitutability).
- Frontend: `frontend/tests` — Vitest + React Testing Library for components/hooks, Playwright for
  browser e2e (`frontend/tests/e2e` or top-level per project convention already in place).

## The red-green-refactor loop (use the `test-and-refactor` skill)

1. Write tests that encode the story's acceptance criteria *before or alongside* the implementation.
2. Run the relevant test command for the changed scope.
3. If a test fails: read the failure, fix the **implementation**, re-run.
4. Repeat until green, or until you've made a bounded number of attempts (see the skill) without
   progress — at which point stop and report the specific failure, don't keep guessing.

**Never** make a failing test pass by deleting it, skipping it (`@pytest.mark.skip`, `.skip()`,
commenting it out), or loosening its assertion to match broken behavior. If, on reflection, the test
itself encodes the wrong expectation (contradicts the story's stated acceptance criteria), fix the test
to match the acceptance criteria and say so explicitly — don't silently soften it.

## Contract tests are mandatory for Liskov claims

If your story adds a second (or later) implementation of an existing `I*`/`Base*` interface, it must
pass the existing shared contract-test suite for that interface. If your story is the *first*
implementation of a new interface, you don't need to invent a contract-test base yet (that's added when
the second implementation lands) — but do keep the interface narrow enough that one is easy to add
later.

## Golden-file tests

Where the plan calls for them explicitly (e.g. STORY-030 column-selection), use fixed
(input, expected-output) pairs checked into the repo, not fuzzy/approximate assertions.

## CI gates

Don't weaken an existing CI gate (coverage threshold, lint, type-check) to make your story's PR pass.
If a gate is genuinely wrong for your story's scope, that's a `devops-observability-engineer` concern —
flag it rather than editing CI config from an unrelated story.

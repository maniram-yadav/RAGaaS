---
name: test-and-refactor
description: Use after implementing (or changing) any story's code, before declaring it done. Runs the relevant test suite, and on failure fixes the implementation and re-runs — bounded iterations, never weakens a test to force a pass. Applies to both backend (pytest) and frontend (Vitest/Playwright) changes.
---

# test-and-refactor

Drives a change to a genuinely passing test suite without cheating the tests.

## Procedure

1. **Identify the narrowest relevant test command** for what changed:
   - Backend unit: `pytest backend/tests/unit/<path> -q`
   - Backend integration (needs real Postgres/Mongo/Redis/Qdrant via testcontainers):
     `pytest backend/tests/integration/<path> -q`
   - Backend contract suite (Liskov proof across implementations): `pytest backend/tests/contract -q`
   - Backend e2e: `pytest backend/tests/e2e/<path> -q`
   - Frontend unit/component: `npm run test -- <path>` (Vitest + RTL) from `frontend/`
   - Frontend e2e: `npx playwright test <path>` from `frontend/`
   Prefer the narrowest command that covers the change first; run the broader suite once the narrow one
   is green, to catch regressions.

2. **Run it.** Read the actual failure output, not just pass/fail — assertion diffs, tracebacks, which
   fixture/case failed.

3. **On failure, fix the implementation**, not the test — unless you can point to the specific
   acceptance-criteria line in the story that shows the test's expectation itself is wrong, in which
   case fix the test to match that acceptance criteria and state why in your report.

4. **Re-run.** Repeat steps 2–3.

5. **Bound it.** After ~5 fix-and-rerun cycles without reaching green, stop looping. Report exactly
   which test still fails, the actual vs. expected output, and your best diagnosis of the root cause —
   don't keep guessing indefinitely, and don't paper over it.

## Forbidden shortcuts

Never do any of the following to make a suite report green:
- Deleting or commenting out a failing test.
- Adding `@pytest.mark.skip` / `.skip()` / `xfail` to a test that should pass per the story's acceptance
  criteria.
- Loosening an assertion (e.g. widening a tolerance, removing a check) without a stated, acceptance-
  criteria-backed reason.
- Mocking out the exact thing the test was written to verify.

## Definition of "green"

The test command's own exit code is 0 for the suite(s) relevant to the story, and you have actually read
the output (not just trusted a cached/previous run).

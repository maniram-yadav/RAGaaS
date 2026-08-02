# CI pipeline

## Overview

GitHub Actions workflows that lint, type-check, and run the (currently near-empty) backend and frontend
test suites on every PR and on pushes to `main`, plus a build-only Docker image check for both apps, per
plan §8/§16 and `implementation_task.md`'s STORY-002. This is the first automated gate in the repo: it
doesn't enforce a coverage threshold or deploy anything (both are explicitly out of scope until
STORY-059+ and a later deployment story) — it only proves that the STORY-001 scaffold lints clean,
type-checks clean, its (currently trivial) tests pass, and both `Dockerfile`s produce a working image.

## Interfaces / contracts

No new classes — this story is CI/Docker configuration only:

- `.github/workflows/backend-ci.yml` — two jobs: `lint-type-test` (ruff → mypy → pytest, on Python 3.11)
  and `docker-build` (build-only, `docker/build-push-action` with `push: false`).
- `.github/workflows/frontend-ci.yml` — mirrors the backend workflow: `lint-type-test` (eslint → tsc
  --noEmit → vitest, on Node 20) and `docker-build` (build-only).
- `backend/Dockerfile` + `backend/.dockerignore` — multi-stage-free, `python:3.11-slim` base, installs
  only `requirements.txt` (runtime deps; dev/test tooling is deliberately excluded from the image).
- `frontend/Dockerfile` + `frontend/.dockerignore` — three-stage (`deps` → `builder` → `runner`) build on
  `node:20-slim`, producing a `next build` output served by `next start`.
- `backend/pyproject.toml` — `[tool.ruff]` / `[tool.mypy]` config (target/python version 3.11, line
  length 100, `E,F,I,UP,B,ASYNC` rule set for ruff; `mypy` checks `app/`).
- `frontend/eslint.config.mjs` — flat ESLint config (ESLint 9 requires flat config; `eslint-config-next`
  doesn't ship one natively yet for this version, so it's bridged via `@eslint/eslintrc`'s `FlatCompat`,
  the same mechanism `next lint` uses internally). Replaces the STORY-001 `.eslintrc.json`, which ESLint
  9's plain `eslint` CLI silently refuses to load (removed as dead config).

Two incidental fixes were required, within STORY-002's own scope, to make these gates actually pass
rather than just exist:

1. `backend/requirements.txt`: `tenacity==9.0.0` conflicted with `langchain==0.3.1`'s
   `tenacity!=8.4.0,<9.0.0,>=8.1.0` constraint, making `pip install -r requirements.txt` — and therefore
   the Docker build — fail with `ResolutionImpossible`. Pinned down to `tenacity==8.5.0`.
2. `frontend/public/.gitkeep` was added: the Next.js `public/` directory didn't exist yet in the
   STORY-001 scaffold, but `frontend/Dockerfile`'s runner stage needs to `COPY --from=builder /app/public
   ./public`, which fails on a missing source path. An empty, gitkept `public/` matches the same "empty
   scaffold directory" convention already used for `components/`, `features/`, `lib/`.

## Config knobs

None. No new env var or `system_config` key is introduced by this story. See
[docs/reference/configuration.md](../reference/configuration.md) for the existing precedence rule.

## Testing

Per `testing-standards.md`, for an infra story the CI job itself is the test. Verified by running every
step each workflow performs, locally, against the actual scaffold:

- Backend (`backend/`):
  ```
  pip install -r requirements-dev.txt
  ruff check .        # All checks passed!
  mypy                # Success: no issues found in 20 source files
  pytest              # 1 passed (tests/e2e/test_health.py)
  ```
- Frontend (`frontend/`):
  ```
  npm ci
  npm run lint         # clean
  npm run type-check   # clean
  npm test             # 3 passed (tests/route-groups.test.tsx)
  npm run build        # next build succeeds
  ```
- Docker: `docker build` run locally for both `backend/Dockerfile` and `frontend/Dockerfile` — both
  complete successfully. The backend image was additionally run
  (`docker run -p 18000:8000 ragaas-backend:ci-check`) and `curl localhost:18000/health` returned
  `{"status":"ok"}`, confirming the image is not just buildable but runnable.

## Story references

- STORY-002 — CI pipeline (lint, type-check, test scaffolding)

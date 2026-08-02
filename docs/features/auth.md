# Auth (signup/login/JWT)

## Overview

Signup/login with bcrypt-hashed passwords (`passlib[bcrypt]`) and JWT access+refresh tokens
(`python-jose`), plus refresh-token rotation, logout-time revocation via a thin Redis-backed blacklist,
and the `get_current_user` FastAPI dependency every later authenticated router builds on. Implements
plan §4.9 ("Auth: JWT (access+refresh) via `python-jose`, `passlib[bcrypt]`") and the route list in §7
(`POST /api/auth/signup`, `POST /api/auth/login`, `POST /api/auth/refresh`, `GET /api/me`), plus a
`POST /api/auth/logout` route added to actually exercise the scope's explicit "blacklist-on-logout"
requirement — the plan's literal route list has no logout endpoint, but revocation is meaningless without
one, so this is the one deliberate scope addition beyond the plan's four routes.

## Interfaces / contracts

- `app.domain.users.entities.Role` — `str`-subclassing enum (`ADMIN`, `MEMBER`, `OWNER`). `User.role` is
  now typed `Role` (default `Role.MEMBER`); because it subclasses `str`, existing code comparing
  `role == "member"` and the Postgres `String(32)` column both keep working unchanged.
- `app.domain.users.auth_service.AuthService` — the story's core business logic: `signup`,
  `authenticate`, `login`, `refresh` (rotation), `logout` (blacklist), `get_current_user`. Its only
  domain-layer dependency is `IUserRepository` (STORY-004) — Dependency Inversion, this story's stated
  design pattern. Password hashing/JWT encode-decode (`app.core.security`) are imported directly as
  stable library calls rather than hidden behind another interface (Interface Segregation: don't add an
  abstraction the story doesn't need).
  - `AuthService._TokenBlacklistPort` — a narrow `typing.Protocol` (`blacklist`, `is_blacklisted`), used
    purely so `AuthService` is unit-testable against an in-memory fake. It is *not* a registered domain
    contract like `IUserRepository`/`IStorageService` — no factory/registry, since it isn't meant to be a
    swappable backend, just an injectable collaborator.
- `app.domain.users.errors` — added `InvalidCredentialsError` (unknown email or wrong password, one
  message either way so login can't be used to enumerate registered emails) and `TokenRejectedError`
  (expired/malformed/wrong-type/blacklisted/orphaned token), alongside STORY-004's existing
  `UserAlreadyExistsError`/`UserNotFoundError`.
- `app.core.security` — framework-free password/JWT primitives: `hash_password`/`verify_password`
  (passlib `CryptContext`, bcrypt scheme); `TokenType` (`ACCESS`/`REFRESH`); `TokenPayload`/`TokenPair`
  value objects; `create_access_token`/`create_refresh_token`/`create_token_pair`; `decode_token`
  (validates signature, expiry, and the `type` claim — an access token can never be accepted where a
  refresh token is required, or vice versa); `InvalidTokenError`/`TokenExpiredError`.
- `app.infrastructure.auth.redis_token_blacklist.RedisTokenBlacklist` — thin `redis.asyncio` client
  wrapper; each blacklisted `jti` is its own key with a TTL equal to the token's remaining lifetime, so
  entries self-expire. `get_redis_client()`/`get_token_blacklist()` are cached process-wide singletons
  (`lru_cache`, same pattern as `get_postgres_sessionmaker`). Deliberately minimal per this story's
  scope note — full Celery/Redis worker infrastructure is STORY-014.
- `app.api.deps` — `oauth2_scheme` (`OAuth2PasswordBearer(tokenUrl="/api/auth/login")`, wires Swagger's
  "Authorize" flow); `get_auth_service` (builds `AuthService` from `RepositoryFactory` +
  `get_token_blacklist()`); `get_current_user` (the story's headline FastAPI dependency — resolves the
  bearer token to a `User` or raises `401`); `require_role(*roles)` — an RBAC dependency *factory*
  (`Depends(require_role(Role.ADMIN, Role.OWNER))` → `403` if the caller's role doesn't match). Not
  consumed by any router yet; STORY-050's admin config API is the first expected consumer.
- `app.api.auth` router — `POST /api/auth/signup` (`201`, rejects duplicate email with `409`),
  `POST /api/auth/login` (accepts `OAuth2PasswordRequestForm` — email passed as `username` — so Swagger
  UI's "Authorize" button works against this endpoint out of the box; `401` on bad credentials),
  `POST /api/auth/refresh` (`401` on any rejected token), `POST /api/auth/logout` (`204`, blacklists the
  given refresh token), `GET /api/me` (requires `get_current_user`).

## Design notes

- **Dependency Inversion**: `AuthService` never imports SQLAlchemy/Motor/Redis directly — only
  `IUserRepository` and the `_TokenBlacklistPort` Protocol. `app.api.deps` is the one place concrete
  infrastructure (`RepositoryFactory`, `RedisTokenBlacklist`) gets wired in.
- **A real bcrypt/passlib pin conflict was found and fixed**: `passlib==1.7.4`'s bcrypt backend-init
  code reads `bcrypt.__about__.__version__`, which `bcrypt>=4.1` removed — every `hash()`/`verify()`
  call crashed with the installed latest bcrypt. Fixed by pinning `bcrypt==4.0.1` in
  `backend/requirements.txt` (below passlib 1.7.4's compatibility ceiling), flagged here since
  `requirements.txt` is shared infra (same category of fix as STORY-004's SQLAlchemy pin bump).
- `email-validator` was added to `requirements.txt` — pydantic's `EmailStr` (used by the signup request
  schema) raises an `ImportError` at model-definition time without it.
- `pyproject.toml`'s ruff config gained a narrow `[tool.ruff.lint.flake8-bugbear] extend-immutable-calls`
  allowlist for `fastapi.Depends`/`Query`/`Path`/`Body` — this is the first FastAPI router in the app,
  and the standard `Depends(...)` default-argument idiom otherwise trips bugbear's `B008`. This mirrors
  ruff's own documented recommendation for FastAPI projects; it doesn't weaken `B008`'s actual
  mutable-default-argument check.

## Config knobs

- `JWT_ALGORITHM` (new this story, via the `add-config-key` skill) — bootstrap-only env var, default
  `HS256`, the `python-jose` signing algorithm paired with `APP_SECRET_KEY`. Deliberately *not* a
  `system_config` key: algorithm choice is tied to how the secret is generated/rotated, a bootstrap
  concern, not something an admin should be able to flip at runtime.
- Reused from STORY-003's scaffolding: `APP_SECRET_KEY` (JWT signing secret — bootstrap layer only,
  **never** written to `system_config`, per `.claude/rules/config-management.md`),
  `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` (default `15`), `JWT_REFRESH_TOKEN_EXPIRE_DAYS` (default `30`),
  `REDIS_URL` (blacklist backing store).

See [docs/reference/configuration.md](../reference/configuration.md) for the full precedence rule.

## Testing

- `backend/tests/unit/core/test_security.py` — password hashing round-trip, JWT encode/decode
  round-trip (access and refresh), rejection of: wrong token type, malformed token, wrong signing
  secret, expired token. No I/O.
- `backend/tests/unit/domain/users/test_auth_service.py` — `AuthService` against an in-memory fake
  `IUserRepository` + fake blacklist: signup duplicate-email rejection, login wrong-password/
  unknown-email rejection, successful login → working access token, refresh rotation (new pair issued,
  old refresh token rejected on reuse), refresh rejects wrong token type and an expired refresh token,
  logout blacklists the refresh token, `get_current_user` rejects a refresh token presented as access, a
  deleted user's token, and a blacklisted access token.
- `backend/tests/unit/domain/users/test_auth_service_logging.py` — the "passwords never appear in logs"
  acceptance criterion: wraps `structlog.testing.capture_logs()` around signup/login (success and a
  rejected wrong-password attempt) and asserts the plaintext password string is absent from every
  captured log event.
- `backend/tests/unit/api/test_deps.py` — `require_role`'s allow/deny decision.
- `backend/tests/unit/domain/users/test_entities.py` / `test_errors.py` — extended with `Role` enum
  coverage and the two new error types.
- `backend/tests/integration/auth/` — real Postgres + real Redis via `testcontainers`
  (`postgres:16-alpine`, `redis:latest`), driving the real `app.main:app` through
  `httpx.AsyncClient`/`ASGITransport` with only `get_auth_service` overridden (mirrors
  `tests/integration/db/postgres/test_repository_factory.py`'s approach of sidestepping
  `ConfigService`'s Mongo dependency for a test that isn't about config resolution):
  - `test_full_signup_login_me_refresh_flow` — the story's headline acceptance criterion: signup →
    login → authenticated `/api/me` → refresh, plus proving the rotated-out refresh token is rejected on
    reuse.
  - Duplicate-email signup → `409`; wrong-password login → `401`; logout blacklists the refresh token
    (`204`, then `401` on reuse); an already-expired access token → `401`; a blacklisted (revoked) access
    token → `401` even though it hasn't naturally expired.

Run from `backend/`:

```
pytest tests/unit -q          # no external dependencies
pytest tests/integration -q   # requires Docker (testcontainers: postgres:16-alpine, redis:latest)
```

All 100 backend tests pass (83 unit/e2e + 17 integration); `ruff check app tests` and `mypy app` are
clean.

## Story references

- STORY-006 — signup/login/JWT auth module (this doc). Depends on STORY-004
  (`IUserRepository`/`PostgresUserRepository`/`RepositoryFactory`, already `done`). `require_role` is not
  yet consumed by any router — STORY-050 (admin config API) is the first expected consumer.

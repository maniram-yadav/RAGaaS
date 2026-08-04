# Configuration reference

RAGaaS resolves every runtime setting through one precedence chain (plan §4.9/§11), implemented by
`ConfigService` (STORY-003):

1. **`system_config` collection in MongoDB** — single source of truth for runtime-tunable settings
   (which provider is active, model params, limits). Can change without a redeploy.
2. **Environment variables** — bootstrap/infra-level settings (connection strings, secrets).
3. **`.env` defaults** — local-dev fallback for the above.

Two files document the *shape* of this configuration without holding any real values:
`config/system_config.example.json` (layer 1) and `.env.example` (layers 2/3). **Neither file is loaded
by the application at runtime** — they exist so a human or agent can see every configurable key in one
place. The real `.env` (git-ignored, never read/edited by an agent — see
[.claude/rules/config-management.md](../../.claude/rules/config-management.md)) and the real Mongo
`system_config` document are what the app actually reads.

To add a new key, use the `add-config-key` skill (or `/add-config-key`) — it keeps this doc and both
template files in sync in one pass.

## `system_config` sections (`config/system_config.example.json`)

| Section | Key | Purpose | Default |
|---|---|---|---|
| `db` | `active` | Which `IDatabase`/repository backend is active | `postgres` (`postgres` \| `mongo`) |
| `storage` | `active` | Which `IStorageService` backend is active | `local` (`local` \| `s3` \| `gcs` \| `azure`) |
| `storage` | `local.base_path` | Local filesystem storage root | `./var/storage` |
| `storage` | `s3.bucket`, `s3.region` | S3 target (STORY-046) | empty |
| `storage` | `gcs.bucket` | GCS target (STORY-047) | empty |
| `storage` | `azure.container` | Azure Blob target (STORY-047) | empty |
| `llm` | `active` | Which `ILLMProvider` is active | `openai` (`openai` \| `anthropic` \| `azure_openai` \| `ollama`) |
| `llm` | `model` | Model name passed to the active provider | `gpt-4o-mini` |
| `llm` | `temperature` | Generation temperature | `0.2` |
| `llm` | `max_tokens` | Generation max tokens | `1024` |
| `llm` | `embedding_model` | Model name for `IEmbeddingProvider` | `text-embedding-3-small` |
| `payment` | `active` | Which `IPaymentProvider` is active | `stripe` (`stripe` \| `razorpay` \| `paypal`) |
| `vectorstore` | `active` | Which `IVectorStore` is active | `qdrant` |
| `safety` | `rate_limit.requests_per_minute` | Token-bucket limit (STORY-041) | `60` |
| `safety` | `moderation.active` | Which `IModerationProvider` is active | `openai` |
| `ingestion` | `max_upload_size_bytes` | Max accepted size for `POST /api/documents/upload` (STORY-010) | `20971520` (20 MiB) |
| `ingestion` | `allowed_extensions` | Allow-listed file extensions the upload endpoint accepts (STORY-010) | `[".txt", ".pdf", ".docx", ".xlsx", ".csv"]` |
| — | `config_cache_ttl_seconds` | `ConfigService` in-process cache TTL | `30` |

Credentials/secrets are **never** stored here, even for an "active" provider — see below.

## Env vars (`.env.example`)

| Var | Purpose |
|---|---|
| `APP_ENV`, `APP_SECRET_KEY`, `APP_LOG_LEVEL` | App bootstrap + JWT signing key |
| `DB_ACTIVE`, `STORAGE_ACTIVE`, `LLM_ACTIVE`, `PAYMENT_ACTIVE`, `VECTORSTORE_ACTIVE`, `SAFETY_MODERATION_ACTIVE` | `ConfigService` layer-2/3 fallback for the matching `system_config` `*.active` key when the Mongo document has no value for that section (STORY-003) |
| `LLM_MODEL`, `LLM_TEMPERATURE`, `LLM_MAX_TOKENS`, `LLM_EMBEDDING_MODEL` | `ConfigService` fallback for `llm.*` tunables |
| `SAFETY_RATE_LIMIT_RPM` | `ConfigService` fallback for `safety.rate_limit.requests_per_minute` |
| `INGESTION_MAX_UPLOAD_SIZE_BYTES`, `INGESTION_ALLOWED_EXTENSIONS` | `ConfigService` fallback for `ingestion.max_upload_size_bytes`/`ingestion.allowed_extensions` (STORY-010) |
| `CONFIG_CACHE_TTL_SECONDS` | `ConfigService` in-process cache TTL (seconds) — also documented as `system_config.config_cache_ttl_seconds`'s default |
| `POSTGRES_HOST/PORT/DB/USER/PASSWORD` | Postgres connection (SQLAlchemy async) |
| `MONGO_URI`, `MONGO_DB` | Mongo connection (Motor) — also where `system_config` itself lives |
| `REDIS_URL` | Celery broker/result backend, rate limiting, token blacklist |
| `QDRANT_URL`, `QDRANT_API_KEY` | Default vector store |
| `JWT_ALGORITHM` | python-jose signing algorithm (STORY-006), paired with `APP_SECRET_KEY` |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES`, `JWT_REFRESH_TOKEN_EXPIRE_DAYS` | Token lifetimes |
| `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `AZURE_OPENAI_API_KEY`/`_ENDPOINT`, `OLLAMA_BASE_URL` | LLM/embedding provider credentials |
| `LOCAL_STORAGE_BASE_PATH`, `AWS_*`, `GCS_BUCKET`, `GOOGLE_APPLICATION_CREDENTIALS`, `AZURE_STORAGE_*` | Storage provider credentials/targets |
| `STRIPE_*`, `RAZORPAY_*`, `PAYPAL_*` | Payment provider credentials |
| `OPENAI_MODERATION_API_KEY` | Moderation provider credential |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend API base URL |
| `NEXT_PUBLIC_SITE_URL` | Canonical frontend origin used to build absolute URLs in `frontend/app/sitemap.ts`/`robots.ts` (STORY-007) |

## Why the split

`system_config` holds *which strategy is active and its non-secret tunables* — it's meant to be changed
at runtime by an admin (STORY-050) without touching infrastructure. Env vars hold *how to physically
connect* to something, including anything secret — those require a redeploy/restart and must never be
written to Mongo in plaintext (plan §11).

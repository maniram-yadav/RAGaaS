# Coding standards

Applies to every story, every agent. Backed by plan §3/§5.

## Stack

- Backend: Python 3.11+, FastAPI, **async everywhere**. SQLAlchemy 2.0 (async) + Alembic for Postgres.
  Motor for MongoDB. LangChain (LCEL) for chains.
- Frontend: Next.js 15 App Router, React 19, Tailwind CSS.

## Pattern map (use the named pattern, don't invent a new shape for the same problem)

| Pattern | Where |
|---|---|
| Strategy | Retrieval strategy, DB strategy, storage strategy, column-selection strategy, loaders |
| Factory | `LoaderFactory`, `LLMProviderFactory`, `EmbeddingProviderFactory`, `VectorStoreFactory`, `PaymentProviderFactory`, `RepositoryFactory`, `StorageFactory` |
| Repository | All persistence access — business logic never touches SQLAlchemy/Motor directly |
| Chain of Responsibility | The safety/validation pipeline (`PipelineHandler` sequence) |
| Template Method | Shared ETL "extract → transform → load" skeleton (`BaseProcessingPipeline`) |
| Builder | LCEL generation chain assembly (`GenerationChainBuilder`) |
| Decorator | Retriever re-ranking wrapper, LLM-call caching wrapper |
| Observer/Pub-Sub | Config-change notifications, webhook event fan-out |

## The four SOLID rules that are load-bearing here

- **Dependency Inversion**: never `import` a concrete provider/repo/storage class into an API router or
  another domain. Depend on the `I*`/`Base*` interface in `app/domain/**`; the concrete instance is
  resolved via a factory reading `ConfigService`.
- **Open/Closed**: a new file type, DB backend, LLM provider, payment provider, or safety handler is
  **one new class + one registry entry** (a dict keyed by type/name). If you find yourself editing an
  `if/elif` chain in an existing factory to add a type, stop — convert it to a registry first, in the
  same story only if that factory belongs to your story's scope, otherwise flag it.
- **Interface Segregation**: keep interfaces narrow. `IEmbeddingProvider` is not merged into
  `ILLMProvider`. Don't add a method to an interface "for later" — add it when a story needs it.
- **Liskov Substitution**: every concrete `Base*`/`I*` implementation must be substitutable for its
  siblings. Where a shared contract-test base class already exists for that interface (see
  `tests/contract/`, seeded in STORY-045), your new implementation must pass it. If none exists yet and
  your story is the first implementation, that's fine — a later story adds the second implementation +
  contract tests.

## Multi-tenancy

Every query that touches tenant data is scoped by `org_id`. Don't write a query that could leak across
tenants even if the current story doesn't yet have a multi-tenant UI in front of it.

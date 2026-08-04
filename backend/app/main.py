"""FastAPI application entrypoint for the RAGaaS backend.

This module wires the ASGI `app` instance consumed by `uvicorn app.main:app`.
Business routers are mounted here story-by-story (see `app/api/`).
"""

from fastapi import FastAPI

from app.api.auth import router as auth_router
from app.api.documents import router as documents_router

app = FastAPI(title="RAGaaS API")
app.include_router(auth_router)
app.include_router(documents_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Trivial liveness probe.

    Returns:
        A static payload confirming the ASGI process is up and serving
        requests. Real readiness checks (Postgres/Mongo/Redis/Qdrant
        connectivity) are added by the stories that introduce those
        dependencies.
    """
    return {"status": "ok"}

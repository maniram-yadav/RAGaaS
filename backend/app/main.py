"""FastAPI application entrypoint for the RAGaaS backend.

This module wires the ASGI `app` instance consumed by `uvicorn app.main:app`.
Business routers are mounted here story-by-story (see `app/api/`); at this
stage of the scaffold only a trivial liveness route exists.
"""

from fastapi import FastAPI

app = FastAPI(title="RAGaaS API")


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

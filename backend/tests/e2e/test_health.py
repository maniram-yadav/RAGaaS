"""E2E smoke test proving STORY-001's acceptance criterion.

`backend/` runs `uvicorn app.main:app` and returns a 200 on a trivial health
route. This test exercises the same ASGI `app` instance uvicorn serves, via
an in-process httpx.AsyncClient, rather than shelling out to a live server.
"""

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_health_returns_200_ok() -> None:
    """GET /health responds with 200 and a status payload."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

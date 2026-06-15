"""Integration test placeholders requiring the Docker Compose stack."""

import os

import httpx
import pytest


@pytest.mark.skipif(
    os.getenv("RUN_COMPOSE_INTEGRATION") != "1", reason="requires running Docker Compose stack"
)
@pytest.mark.asyncio
async def test_health_ready_contract() -> None:
    """Verify the API readiness endpoint against a running local stack."""

    async with httpx.AsyncClient(base_url="http://localhost:8080", timeout=5) as client:
        response = await client.get("/health/ready")
    assert response.status_code == 200

"""Integration tests for health check endpoints."""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
class TestHealthEndpoints:
    """Tests for liveness and readiness probes."""

    async def test_health_check(self, client: AsyncClient) -> None:
        """Liveness probe should always return OK."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "version" in data

    async def test_readiness_check(self, client: AsyncClient) -> None:
        """Readiness probe should check dependencies."""
        response = await client.get("/api/v1/ready")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "redis" in data
        assert "models" in data

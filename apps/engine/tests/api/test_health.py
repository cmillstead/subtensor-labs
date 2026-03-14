"""Tests for the health endpoint."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_endpoint_healthy(client: AsyncClient) -> None:
    """Health endpoint returns 200 with healthy status when all services are up."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "healthy"
    assert data["data"]["engine"] == "running"
    assert data["data"]["database"] == "connected"
    assert data["data"]["redis"] == "connected"
    assert data["meta"]["service"] == "subtensor-labs-engine"
    assert data["meta"]["version"] == "0.1.0"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_no_db(client: AsyncClient) -> None:
    """Health endpoint returns degraded when database is down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=False),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "disconnected"
    assert data["data"]["redis"] == "connected"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_no_redis(client: AsyncClient) -> None:
    """Health endpoint returns degraded when Redis is down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=False),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "connected"
    assert data["data"]["redis"] == "disconnected"


@pytest.mark.asyncio
async def test_health_endpoint_degraded_both_down(client: AsyncClient) -> None:
    """Health endpoint returns degraded when both services are down."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=False),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=False),
    ):
        response = await client.get("/engine/health")

    assert response.status_code == 200
    data = response.json()
    assert data["data"]["status"] == "degraded"
    assert data["data"]["database"] == "disconnected"
    assert data["data"]["redis"] == "disconnected"


@pytest.mark.asyncio
async def test_health_response_matches_schema(client: AsyncClient) -> None:
    """Health endpoint response matches the documented envelope format."""
    with (
        patch("engine.api.health.check_db_health", new_callable=AsyncMock, return_value=True),
        patch("engine.api.health.check_redis_health", new_callable=AsyncMock, return_value=True),
    ):
        response = await client.get("/engine/health")

    data = response.json()
    assert "data" in data
    assert "meta" in data
    assert set(data["data"].keys()) == {"status", "engine", "database", "redis"}
    assert set(data["meta"].keys()) == {"service", "version"}

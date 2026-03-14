"""Tests that CatchAllMiddleware error responses include CORS headers."""

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from engine.main import app


@pytest.fixture(autouse=True)
def _register_crash_route() -> Generator[None, None, None]:
    """Register a route that raises an unhandled exception."""
    from fastapi import APIRouter

    crash_router = APIRouter(prefix="/engine/cors-test")

    @crash_router.get("/crash")
    async def raise_crash() -> None:
        raise RuntimeError("boom")

    original_routes = list(app.routes)
    app.include_router(crash_router)
    yield
    app.routes[:] = original_routes


@pytest.mark.asyncio
async def test_500_error_includes_cors_header(client: AsyncClient) -> None:
    """Unhandled exception responses include Access-Control-Allow-Origin for allowed origins."""
    response = await client.get(
        "/engine/cors-test/crash",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 500
    assert response.headers.get("access-control-allow-origin") == "http://localhost:3000"


@pytest.mark.asyncio
async def test_500_error_no_cors_for_unknown_origin(client: AsyncClient) -> None:
    """Unhandled exception responses omit CORS header for unknown origins."""
    response = await client.get(
        "/engine/cors-test/crash",
        headers={"Origin": "http://evil.example.com"},
    )
    assert response.status_code == 500
    assert "access-control-allow-origin" not in response.headers

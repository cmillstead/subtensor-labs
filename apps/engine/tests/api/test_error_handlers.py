"""Tests for exception handlers in main.py."""

from collections.abc import Generator

import pytest
from httpx import AsyncClient

from engine.core.exceptions import NotFoundError
from engine.main import app


@pytest.fixture(autouse=True)
def _register_test_routes() -> Generator[None, None, None]:
    """Register temporary test routes that raise exceptions, then clean up."""
    from fastapi import APIRouter

    test_router = APIRouter(prefix="/engine/test")

    @test_router.get("/engine-error")
    async def raise_engine_error() -> None:
        raise NotFoundError("test resource not found")

    @test_router.get("/unhandled-error")
    async def raise_unhandled() -> None:
        raise RuntimeError("unexpected failure")

    # Snapshot routes before adding test routes
    original_routes = list(app.routes)
    app.include_router(test_router)
    yield
    # Restore original routes
    app.routes[:] = original_routes


@pytest.mark.asyncio
async def test_engine_error_returns_json_envelope(client: AsyncClient) -> None:
    """EngineError subclasses return the standard error envelope."""
    response = await client.get("/engine/test/engine-error")
    assert response.status_code == 404
    data = response.json()
    assert data["error"]["type"] == "not_found"
    assert data["error"]["message"] == "test resource not found"
    assert data["error"]["code"] == 404


@pytest.mark.asyncio
async def test_unhandled_error_returns_sanitized_500(client: AsyncClient) -> None:
    """Unhandled exceptions return a generic 500 without leaking internals."""
    response = await client.get("/engine/test/unhandled-error")
    assert response.status_code == 500
    data = response.json()
    assert data["error"]["type"] == "internal_error"
    assert data["error"]["message"] == "An unexpected error occurred"
    assert data["error"]["code"] == 500
    assert "RuntimeError" not in data["error"]["message"]

"""Shared test fixtures."""

import os
import sys
from collections.abc import AsyncGenerator
from unittest.mock import MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

# Stub bittensor before importing app (avoids ModuleNotFoundError in CI/local)
if "bittensor" not in sys.modules:
    sys.modules["bittensor"] = MagicMock()

# Set debug mode before importing app to bypass encryption key validation
os.environ.setdefault("ENGINE_DEBUG", "true")

from engine.main import app  # noqa: E402


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Create an async test client for the FastAPI app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

"""Integration test fixtures — real database, no mocks.

Overrides the parent conftest's mock session. Provides shared DB setup
for all test files in this directory.
"""

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

os.environ.setdefault("ENGINE_DEBUG", "true")

import engine.models  # noqa: E402, F401
from engine.core.database import Base, get_session  # noqa: E402
from engine.main import app  # noqa: E402

TEST_DB_URL = "postgresql+asyncpg://tao:tao@localhost:5432/subtensor_labs_test"


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _init_tables():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()


async def _drop_tables():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


# Create tables once when this conftest is loaded
_run(_init_tables())


def teardown_module():
    _run(_drop_tables())


@pytest.fixture
async def db_engine():
    """Fresh engine per test — avoids connection conflicts."""
    eng = create_async_engine(TEST_DB_URL, pool_size=5, max_overflow=0)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def _override_and_clean(db_engine):
    """Override app session with real DB, truncate tables after each test."""

    async def _test_session():
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = _test_session
    yield
    app.dependency_overrides.clear()

    async with db_engine.begin() as conn:
        await conn.execute(text("TRUNCATE users, password_reset_tokens, user_addresses CASCADE"))


@pytest.fixture
async def client():
    """Async test client backed by the real app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

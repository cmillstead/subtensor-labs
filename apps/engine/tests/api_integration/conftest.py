"""Integration test fixtures — real database and real Redis, no mocks.

Overrides the parent conftest's mock session. Provides shared DB setup
for all test files in this directory. Engine functions that call
get_session_factory() directly also use the test database.
"""

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

os.environ.setdefault("ENGINE_DEBUG", "true")

import engine.core.database as db_module  # noqa: E402
import engine.core.redis as redis_module  # noqa: E402
import engine.models  # noqa: E402, F401
from engine.core.database import Base, get_session  # noqa: E402
from engine.main import app  # noqa: E402

TEST_DB_URL = "postgresql+asyncpg://tao:tao@localhost:5432/subtensor_labs_test"

# All tables to truncate between tests (add new tables here as they're used)
_ALL_TABLES = (
    "user_addresses, password_reset_tokens, alert_history, alert_configs,"
    " saved_screeners, portfolio_snapshots, metagraph_entries,"
    " alpha_prices, emission_records, subnet_snapshots,"
    " ingestion_cursors, users"
)


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
    """Override app session AND module-level session factory with test DB.

    This ensures both FastAPI dependency-injected sessions (get_session)
    and engine functions that call get_session_factory() directly
    all hit the test database.
    """
    test_factory = async_sessionmaker(db_engine, expire_on_commit=False)

    # Override FastAPI dependency
    async def _test_session():
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = _test_session

    # Override module-level engine and factory used by engine functions
    original_engine = db_module._engine
    original_factory = db_module._session_factory
    db_module._engine = db_engine
    db_module._session_factory = test_factory

    yield

    # Restore originals
    app.dependency_overrides.clear()
    db_module._engine = original_engine
    db_module._session_factory = original_factory

    # Truncate all tables
    async with db_engine.begin() as conn:
        await conn.execute(text(f"TRUNCATE {_ALL_TABLES} CASCADE"))

    # Reset Redis client (prevents event loop mismatch between tests)
    # and flush any cached keys from this test run
    try:
        if redis_module._redis_client is not None:
            await redis_module._redis_client.flushdb()
            await redis_module._redis_client.aclose()
            redis_module._redis_client = None
    except Exception:
        redis_module._redis_client = None


@pytest.fixture
async def client():
    """Async test client backed by the real app."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def seed_subnets(db_engine):
    """Seed subnet_snapshots with test data. Returns the seeded netuids."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Insert subnet snapshots for netuid 1 and 3
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES
                    (NOW(), 1, 100, 50, 0.05, 1.5, 0.12, 1200.0, 500.0, 4000.0, 0.78, 0.18),
                    (NOW(), 3, 80, 30, 0.03, 2.0, 0.08, 800.0, 300.0, 3000.0, 0.65, 0.10),
                    (NOW() - INTERVAL '1 day', 1, 98, 49,
                     0.048, 1.5, 0.11, 1100, 490, 3900, 0.77, 0.18),
                    (NOW() - INTERVAL '2 days', 1, 96, 48,
                     0.046, 1.4, 0.10, 1000, 480, 3800, 0.76, 0.18)
            """)
        )
        await session.commit()
    return [1, 3]

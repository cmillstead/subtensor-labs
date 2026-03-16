"""Tests for screener computed metrics — real database, no mocks."""

import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from engine.core.database import Base
from engine.screener.metrics import (
    IMMUNITY_THRESHOLD_DAYS,
    compute_immunity_status,
    compute_net_tao_inflow,
    compute_price_changes,
)

TEST_DB_URL = os.environ.get(
    "ENGINE_DATABASE_URL",
    "postgresql+asyncpg://tao:tao@localhost:5432/subtensor_labs_test",
)


@pytest.fixture
async def db_session():
    """Provide a clean database session for each test."""
    engine = create_async_engine(TEST_DB_URL, pool_size=2, max_overflow=0)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session

    # Clean up
    async with engine.begin() as conn:
        await conn.execute(text("TRUNCATE subnet_snapshots, emission_records CASCADE"))
    await engine.dispose()


class TestComputePriceChanges:
    async def test_returns_correct_percentages(self, db_session: AsyncSession) -> None:
        """With historical data at 24h, 7d, 30d ago, returns correct % changes."""
        now = datetime.now(UTC)
        current_price = 0.12

        # Seed historical snapshots at known offsets
        await db_session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES
                    (:now, 1, 100, 50, 0.05, 1.5, :current, 1200, 500, 4000, 0.78, 0.18),
                    (:t24h, 1, 100, 50, 0.05, 1.5, 0.10, 1000, 490, 3900, 0.77, 0.18),
                    (:t7d, 1, 100, 50, 0.05, 1.5, 0.08, 800, 480, 3800, 0.76, 0.18),
                    (:t30d, 1, 100, 50, 0.05, 1.5, 0.06, 600, 470, 3700, 0.75, 0.18)
            """),
            {
                "now": now,
                "current": current_price,
                "t24h": now - timedelta(hours=24),
                "t7d": now - timedelta(days=7),
                "t30d": now - timedelta(days=30),
            },
        )
        await db_session.commit()

        result = await compute_price_changes(db_session, [1], {1: current_price}, now)

        assert 1 in result
        pc = result[1]
        # 0.10 -> 0.12 = +20%
        assert pc.change_24h == 20.0
        # 0.08 -> 0.12 = +50%
        assert pc.change_7d == 50.0
        # 0.06 -> 0.12 = +100%
        assert pc.change_30d == 100.0

    async def test_returns_none_for_insufficient_history(self, db_session: AsyncSession) -> None:
        """When no historical snapshot exists for a period, returns None."""
        now = datetime.now(UTC)

        # Only seed a current snapshot — no historical data
        await db_session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES (:now, 1, 100, 50, 0.05, 1.5, 0.12, 1200, 500, 4000, 0.78, 0.18)
            """),
            {"now": now},
        )
        await db_session.commit()

        result = await compute_price_changes(db_session, [1], {1: 0.12}, now)

        assert 1 in result
        pc = result[1]
        assert pc.change_24h is None
        assert pc.change_7d is None
        assert pc.change_30d is None

    async def test_empty_netuids_returns_empty(self, db_session: AsyncSession) -> None:
        result = await compute_price_changes(db_session, [], {}, None)
        assert result == {}

    async def test_partial_history(self, db_session: AsyncSession) -> None:
        """When only some periods have data, returns None for missing periods."""
        now = datetime.now(UTC)

        await db_session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES
                    (:now, 1, 100, 50, 0.05, 1.5, 0.12, 1200, 500, 4000, 0.78, 0.18),
                    (:t24h, 1, 100, 50, 0.05, 1.5, 0.10, 1000, 490, 3900, 0.77, 0.18)
            """),
            {
                "now": now,
                "t24h": now - timedelta(hours=24),
            },
        )
        await db_session.commit()

        result = await compute_price_changes(db_session, [1], {1: 0.12}, now)
        pc = result[1]
        assert pc.change_24h == 20.0
        assert pc.change_7d is None
        assert pc.change_30d is None

    async def test_picks_closest_snapshot_not_most_recent(self, db_session: AsyncSession) -> None:
        """When multiple snapshots exist in the window, pick the one closest
        to the target time, not the most recent one."""
        now = datetime.now(UTC)

        # Seed two snapshots near the 24h target:
        # - One at exactly 24h ago (price 0.10) — should be picked
        # - One at 13h ago (price 0.20) — more recent but farther from target
        await db_session.execute(
            text("""
                INSERT INTO subnet_snapshots (time, netuid, miner_count, validator_count,
                    emission_share, registration_cost, alpha_price, alpha_market_cap,
                    tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES
                    (:now, 1, 100, 50, 0.05, 1.5, 0.12, 1200, 500, 4000, 0.78, 0.18),
                    (:t_exact, 1, 100, 50, 0.05, 1.5, 0.10, 1000, 490, 3900, 0.77, 0.18),
                    (:t_recent, 1, 100, 50, 0.05, 1.5, 0.20, 2000, 510, 4100, 0.79, 0.18)
            """),
            {
                "now": now,
                "t_exact": now - timedelta(hours=24),
                "t_recent": now - timedelta(hours=13),
            },
        )
        await db_session.commit()

        result = await compute_price_changes(db_session, [1], {1: 0.12}, now)
        pc = result[1]
        # Should use 0.10 (at exactly 24h), giving +20%
        # NOT 0.20 (at 13h), which would give -40%
        assert pc.change_24h == 20.0


class TestComputeNetTaoInflow:
    async def test_returns_latest_value(self, db_session: AsyncSession) -> None:
        now = datetime.now(UTC)
        await db_session.execute(
            text("""
                INSERT INTO emission_records
                    (time, netuid, emission_tao, emission_share_pct,
                     net_tao_inflow, cumulative_stake)
                VALUES
                    (:t1, 1, 10.0, 0.05, 150.5, 1000),
                    (:t2, 1, 10.0, 0.05, 200.0, 1200),
                    (:t1, 3, 8.0, 0.03, -50.0, 800)
            """),
            {
                "t1": now - timedelta(days=1),
                "t2": now,
            },
        )
        await db_session.commit()

        result = await compute_net_tao_inflow(db_session, [1, 3])

        # Netuid 1: most recent is 200.0
        assert result[1] == 200.0
        # Netuid 3: only one record, -50.0
        assert result[3] == -50.0

    async def test_returns_none_for_missing_netuid(self, db_session: AsyncSession) -> None:
        """When no emission_records exist for a netuid, return None."""
        result = await compute_net_tao_inflow(db_session, [99])
        assert result[99] is None

    async def test_empty_netuids_returns_empty(self, db_session: AsyncSession) -> None:
        result = await compute_net_tao_inflow(db_session, [])
        assert result == {}


class TestComputeImmunityStatus:
    def test_young_subnet_is_immune(self) -> None:
        result = compute_immunity_status({1: 0, 2: 1})
        assert result[1] is True
        assert result[2] is True

    def test_old_subnet_not_immune(self) -> None:
        result = compute_immunity_status({1: 2, 2: 30, 3: 365})
        assert result[1] is False
        assert result[2] is False
        assert result[3] is False

    def test_threshold_boundary(self) -> None:
        result = compute_immunity_status(
            {1: IMMUNITY_THRESHOLD_DAYS - 1, 2: IMMUNITY_THRESHOLD_DAYS}
        )
        assert result[1] is True
        assert result[2] is False

    def test_empty_input(self) -> None:
        assert compute_immunity_status({}) == {}

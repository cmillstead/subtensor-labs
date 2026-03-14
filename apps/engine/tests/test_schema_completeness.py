"""Schema completeness tests — verify all tables, hypertables, indexes, and aggregates.

These tests require a real TimescaleDB database. They run in CI (which has a
TimescaleDB service container) and skip gracefully when no DB is available.
"""

import os
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

# Skip entire module if explicitly disabled
DATABASE_URL = os.environ.get(
    "ENGINE_DATABASE_URL",
    "postgresql+asyncpg://postgres:postgres@localhost:5432/subtensor_labs",
)

pytestmark = pytest.mark.skipif(
    os.environ.get("SKIP_DB_TESTS", "0") == "1",
    reason="SKIP_DB_TESTS=1 — no TimescaleDB available",
)


@pytest.fixture
async def db_engine() -> Any:
    """Create a test engine, skipping if DB is unreachable."""
    engine = create_async_engine(DATABASE_URL, echo=False)
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
    except Exception:
        await engine.dispose()
        pytest.skip("TimescaleDB not available")
    yield engine
    await engine.dispose()


@pytest.fixture
async def db_session(db_engine: AsyncEngine) -> Any:
    """Create a fresh session per test."""
    session_factory = async_sessionmaker(db_engine, expire_on_commit=False)
    async with session_factory() as session:
        yield session


EXPECTED_HYPERTABLES = [
    "subnet_snapshots",
    "alpha_prices",
    "emission_records",
    "metagraph_entries",
    "portfolio_snapshots",
]


class TestHypertables:
    """Verify TimescaleDB hypertables exist with correct configuration."""

    async def test_hypertables_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("SELECT hypertable_name FROM timescaledb_information.hypertables")
        )
        hypertable_names = {row[0] for row in result.fetchall()}
        for name in EXPECTED_HYPERTABLES:
            assert name in hypertable_names, f"Hypertable {name} not found"

    async def test_compression_enabled(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT DISTINCT hypertable_name
                FROM timescaledb_information.compression_settings
            """)
        )
        compressed = {row[0] for row in result.fetchall()}
        for name in EXPECTED_HYPERTABLES:
            assert name in compressed, f"Compression not enabled on {name}"


class TestStandardTables:
    """Verify standard tables exist with expected columns."""

    async def test_users_table_columns(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'users'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0] for row in result.fetchall()}
        expected = {
            "id",
            "email",
            "password_hash",
            "created_at",
            "premium_status",
            "premium_expires_at",
            "stripe_customer_id",
            "updated_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    async def test_user_addresses_table_columns(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'user_addresses'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0] for row in result.fetchall()}
        expected = {
            "id",
            "user_id",
            "coldkey_address",
            "label",
            "is_watch_only",
            "created_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"

    async def test_ingestion_cursors_table(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'ingestion_cursors'
                ORDER BY ordinal_position
            """)
        )
        columns = {row[0] for row in result.fetchall()}
        expected = {
            "source",
            "last_processed_at",
            "last_block_number",
            "metadata_json",
            "updated_at",
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"


class TestIndexes:
    """Verify FK indexes and hypertable indexes exist."""

    async def test_fk_indexes_exist(self, db_session: AsyncSession) -> None:
        expected = {
            "ix_user_addresses_user_id",
            "ix_saved_screeners_user_id",
            "ix_alert_configs_user_id",
            "ix_alert_history_alert_config_id",
        }
        result = await db_session.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        )
        found = {row[0] for row in result.fetchall()}
        missing = expected - found
        assert not missing, f"Missing FK indexes: {missing}"

    async def test_hypertable_indexes_exist(self, db_session: AsyncSession) -> None:
        expected = {
            "ix_subnet_snapshots_netuid_time",
            "ix_alpha_prices_netuid_time",
            "ix_emission_records_netuid_time",
            "ix_metagraph_entries_netuid_time",
        }
        result = await db_session.execute(
            text("SELECT indexname FROM pg_indexes WHERE schemaname = 'public'")
        )
        found = {row[0] for row in result.fetchall()}
        missing = expected - found
        assert not missing, f"Missing hypertable indexes: {missing}"


class TestContinuousAggregates:
    """Verify continuous aggregate views and their refresh policies."""

    async def test_continuous_aggregates_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT view_name
                FROM timescaledb_information.continuous_aggregates
            """)
        )
        views = {row[0] for row in result.fetchall()}
        assert "subnet_snapshots_daily" in views, "subnet_snapshots_daily not found"
        assert "alpha_prices_daily" in views, "alpha_prices_daily not found"

    async def test_refresh_policies_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT hypertable_name
                FROM timescaledb_information.jobs
                WHERE proc_name = 'policy_refresh_continuous_aggregate'
            """)
        )
        views_with_refresh = {row[0] for row in result.fetchall()}
        assert "subnet_snapshots_daily" in views_with_refresh, (
            "subnet_snapshots_daily missing refresh policy"
        )
        assert "alpha_prices_daily" in views_with_refresh, (
            "alpha_prices_daily missing refresh policy"
        )


class TestRetentionPolicies:
    """Verify retention policies are configured."""

    async def test_retention_policies_exist(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT hypertable_name
                FROM timescaledb_information.jobs
                WHERE proc_name = 'policy_retention'
            """)
        )
        tables_with_retention = {row[0] for row in result.fetchall()}
        expected = {"subnet_snapshots", "alpha_prices", "metagraph_entries"}
        missing = expected - tables_with_retention
        assert not missing, f"Missing retention policies: {missing}"

    async def test_no_retention_on_emission_records(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT hypertable_name
                FROM timescaledb_information.jobs
                WHERE proc_name = 'policy_retention'
                  AND hypertable_name = 'emission_records'
            """)
        )
        assert result.fetchone() is None, "emission_records should NOT have retention policy"

    async def test_no_retention_on_portfolio_snapshots(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT hypertable_name
                FROM timescaledb_information.jobs
                WHERE proc_name = 'policy_retention'
                  AND hypertable_name = 'portfolio_snapshots'
            """)
        )
        assert result.fetchone() is None, "portfolio_snapshots should NOT have retention policy"


class TestForeignKeyCascade:
    """Verify ON DELETE CASCADE is set on FK constraints."""

    async def test_cascade_on_user_addresses(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT confdeltype FROM pg_constraint
                WHERE conname = 'fk_user_addresses_user_id'
            """)
        )
        row = result.fetchone()
        assert row is not None, "FK constraint fk_user_addresses_user_id not found"
        confdeltype = row[0] if isinstance(row[0], str) else row[0].decode()
        assert confdeltype == "c", f"Expected CASCADE (c), got: {confdeltype}"

    async def test_cascade_on_alert_history(self, db_session: AsyncSession) -> None:
        result = await db_session.execute(
            text("""
                SELECT confdeltype FROM pg_constraint
                WHERE conname = 'fk_alert_history_alert_config_id'
            """)
        )
        row = result.fetchone()
        assert row is not None, "FK constraint fk_alert_history_alert_config_id not found"
        confdeltype = row[0] if isinstance(row[0], str) else row[0].decode()
        assert confdeltype == "c", f"Expected CASCADE (c), got: {confdeltype}"

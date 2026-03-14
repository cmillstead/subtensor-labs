"""Add TimescaleDB continuous aggregates and retention policies.

Creates daily materialized views for subnet_snapshots and alpha_prices with
automatic refresh policies. Adds retention policies to drop raw data older
than 90 days (aggregates survive in continuous aggregates).

Revision ID: 004
Revises: 003
Create Date: 2026-03-14

"""

from collections.abc import Sequence

from alembic import op

revision: str = "004"
down_revision: str | None = "003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---- Continuous Aggregates ----

    # subnet_snapshots_daily
    op.execute("""
        CREATE MATERIALIZED VIEW subnet_snapshots_daily
        WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
        SELECT
            time_bucket('1 day', time) AS bucket,
            netuid,
            avg(miner_count)::double precision AS avg_miner_count,
            avg(validator_count)::double precision AS avg_validator_count,
            avg(emission_share) AS avg_emission_share,
            avg(registration_cost) AS avg_registration_cost,
            avg(alpha_price) AS avg_alpha_price,
            last(alpha_price, time) AS close_alpha_price,
            first(alpha_price, time) AS open_alpha_price,
            max(alpha_price) AS high_alpha_price,
            min(alpha_price) AS low_alpha_price,
            avg(alpha_market_cap) AS avg_alpha_market_cap,
            last(tao_reserves, time) AS close_tao_reserves,
            last(alpha_reserves, time) AS close_alpha_reserves,
            avg(fill_rate) AS avg_fill_rate,
            last(owner_take_rate, time) AS close_owner_take_rate,
            count(*) AS sample_count
        FROM subnet_snapshots
        GROUP BY bucket, netuid
        WITH NO DATA
    """)

    # alpha_prices_daily
    op.execute("""
        CREATE MATERIALIZED VIEW alpha_prices_daily
        WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
        SELECT
            time_bucket('1 day', time) AS bucket,
            netuid,
            avg(price_tao) AS avg_price_tao,
            first(price_tao, time) AS open_price_tao,
            last(price_tao, time) AS close_price_tao,
            max(price_tao) AS high_price_tao,
            min(price_tao) AS low_price_tao,
            last(tao_reserve, time) AS close_tao_reserve,
            last(alpha_reserve, time) AS close_alpha_reserve,
            sum(volume_24h) AS total_volume_24h,
            count(*) AS sample_count
        FROM alpha_prices
        GROUP BY bucket, netuid
        WITH NO DATA
    """)

    # ---- Refresh Policies (every 1 hour, covering last 3 days) ----

    op.execute("""
        SELECT add_continuous_aggregate_policy('subnet_snapshots_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour')
    """)

    op.execute("""
        SELECT add_continuous_aggregate_policy('alpha_prices_daily',
            start_offset => INTERVAL '3 days',
            end_offset => INTERVAL '1 hour',
            schedule_interval => INTERVAL '1 hour')
    """)

    # ---- Retention Policies (drop raw chunks older than 90 days) ----
    # Continuous aggregates survive — they store pre-computed daily data
    # Do NOT add retention to emission_records (small, kept indefinitely)
    # or portfolio_snapshots (kept indefinitely per user)

    op.execute("SELECT add_retention_policy('subnet_snapshots', INTERVAL '90 days')")
    op.execute("SELECT add_retention_policy('alpha_prices', INTERVAL '90 days')")
    op.execute("SELECT add_retention_policy('metagraph_entries', INTERVAL '90 days')")


def downgrade() -> None:
    # Remove retention policies
    op.execute("SELECT remove_retention_policy('metagraph_entries', if_exists => true)")
    op.execute("SELECT remove_retention_policy('alpha_prices', if_exists => true)")
    op.execute("SELECT remove_retention_policy('subnet_snapshots', if_exists => true)")

    # Remove refresh policies
    op.execute(
        "SELECT remove_continuous_aggregate_policy('alpha_prices_daily', if_exists => true)"
    )
    op.execute(
        "SELECT remove_continuous_aggregate_policy('subnet_snapshots_daily', if_exists => true)"
    )

    # Drop continuous aggregates
    op.execute("DROP MATERIALIZED VIEW IF EXISTS alpha_prices_daily CASCADE")
    op.execute("DROP MATERIALIZED VIEW IF EXISTS subnet_snapshots_daily CASCADE")

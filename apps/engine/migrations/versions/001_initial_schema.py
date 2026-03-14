"""Initial schema — all tables, TimescaleDB hypertables, compression policies.

Revision ID: 001
Revises: None
Create Date: 2026-03-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Enable TimescaleDB extension
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")

    # ---- Standard tables ----

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("premium_status", sa.String(20), nullable=False, server_default="free"),
        sa.Column("premium_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stripe_customer_id", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    op.create_table(
        "user_addresses",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("coldkey_address", sa.String(512), nullable=False),
        sa.Column("label", sa.String(100), nullable=True),
        sa.Column("is_watch_only", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_user_addresses_user_id"),
    )

    op.create_table(
        "saved_screeners",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("filters_json", JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_saved_screeners_user_id"),
    )

    op.create_table(
        "alert_configs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("conditions_json", JSONB(), nullable=False),
        sa.Column("delivery_channels_json", JSONB(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("last_triggered_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name="fk_alert_configs_user_id"),
    )

    op.create_table(
        "alert_history",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("alert_config_id", sa.Integer(), nullable=False),
        sa.Column(
            "triggered_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("context_json", JSONB(), nullable=False),
        sa.Column("acknowledged", sa.Boolean(), nullable=False, server_default="false"),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["alert_config_id"], ["alert_configs.id"], name="fk_alert_history_alert_config_id"
        ),
    )

    # ---- TimescaleDB hypertables ----

    op.create_table(
        "subnet_snapshots",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("netuid", sa.Integer(), nullable=False),
        sa.Column("miner_count", sa.Integer(), nullable=False),
        sa.Column("validator_count", sa.Integer(), nullable=False),
        sa.Column("emission_share", sa.Float(), nullable=False),
        sa.Column("registration_cost", sa.Float(), nullable=False),
        sa.Column("alpha_price", sa.Float(), nullable=False),
        sa.Column("alpha_market_cap", sa.Float(), nullable=False),
        sa.Column("tao_reserves", sa.Float(), nullable=False),
        sa.Column("alpha_reserves", sa.Float(), nullable=False),
        sa.Column("fill_rate", sa.Float(), nullable=False),
        sa.Column("owner_take_rate", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("time", "netuid"),
    )
    op.create_index("ix_subnet_snapshots_netuid_time", "subnet_snapshots", ["netuid", sa.text("time DESC")])

    op.create_table(
        "alpha_prices",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("netuid", sa.Integer(), nullable=False),
        sa.Column("price_tao", sa.Float(), nullable=False),
        sa.Column("tao_reserve", sa.Float(), nullable=False),
        sa.Column("alpha_reserve", sa.Float(), nullable=False),
        sa.Column("volume_24h", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("time", "netuid"),
    )
    op.create_index("ix_alpha_prices_netuid_time", "alpha_prices", ["netuid", sa.text("time DESC")])

    op.create_table(
        "emission_records",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("netuid", sa.Integer(), nullable=False),
        sa.Column("emission_tao", sa.Float(), nullable=False),
        sa.Column("emission_share_pct", sa.Float(), nullable=False),
        sa.Column("net_tao_inflow", sa.Float(), nullable=False),
        sa.Column("cumulative_stake", sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint("time", "netuid"),
    )
    op.create_index("ix_emission_records_netuid_time", "emission_records", ["netuid", sa.text("time DESC")])

    op.create_table(
        "metagraph_entries",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("netuid", sa.Integer(), nullable=False),
        sa.Column("uid", sa.Integer(), nullable=False),
        sa.Column("hotkey", sa.String(48), nullable=False),
        sa.Column("coldkey", sa.String(48), nullable=False),
        sa.Column("stake", sa.Float(), nullable=False),
        sa.Column("incentive", sa.Float(), nullable=False),
        sa.Column("trust", sa.Float(), nullable=False),
        sa.Column("dividends", sa.Float(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.PrimaryKeyConstraint("time", "netuid", "uid"),
    )
    op.create_index("ix_metagraph_entries_netuid_time", "metagraph_entries", ["netuid", sa.text("time DESC")])
    op.create_index("ix_metagraph_entries_coldkey", "metagraph_entries", ["coldkey"])
    op.create_index("ix_metagraph_entries_hotkey", "metagraph_entries", ["hotkey"])

    op.create_table(
        "portfolio_snapshots",
        sa.Column("time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("total_value_tao", sa.Float(), nullable=False),
        sa.Column("per_subnet_json", JSONB(), nullable=False),
        sa.PrimaryKeyConstraint("time", "user_id"),
    )
    op.create_index("ix_portfolio_snapshots_user_id_time", "portfolio_snapshots", ["user_id", sa.text("time DESC")])

    # Convert to TimescaleDB hypertables (1-day chunk interval)
    hypertables = [
        "subnet_snapshots",
        "alpha_prices",
        "emission_records",
        "metagraph_entries",
        "portfolio_snapshots",
    ]
    for table in hypertables:
        op.execute(
            f"SELECT create_hypertable('{table}', 'time', chunk_time_interval => INTERVAL '1 day')"
        )

    # Set compression policies with segmentby/orderby (compress chunks older than 7 days)
    netuid_tables = [
        "subnet_snapshots",
        "alpha_prices",
        "emission_records",
        "metagraph_entries",
    ]
    for table in netuid_tables:
        op.execute(
            f"ALTER TABLE {table} SET ("
            f"timescaledb.compress, "
            f"timescaledb.compress_segmentby = 'netuid', "
            f"timescaledb.compress_orderby = 'time DESC')"
        )
        op.execute(
            f"SELECT add_compression_policy('{table}', INTERVAL '7 days')"
        )

    op.execute(
        "ALTER TABLE portfolio_snapshots SET ("
        "timescaledb.compress, "
        "timescaledb.compress_segmentby = 'user_id', "
        "timescaledb.compress_orderby = 'time DESC')"
    )
    op.execute(
        "SELECT add_compression_policy('portfolio_snapshots', INTERVAL '7 days')"
    )


def downgrade() -> None:
    tables = [
        "portfolio_snapshots",
        "metagraph_entries",
        "emission_records",
        "alpha_prices",
        "subnet_snapshots",
        "alert_history",
        "alert_configs",
        "saved_screeners",
        "user_addresses",
        "users",
    ]
    for table in tables:
        op.drop_table(table)

    op.execute("DROP EXTENSION IF EXISTS timescaledb")

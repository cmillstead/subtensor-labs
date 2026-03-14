"""Add FK indexes and ON DELETE CASCADE to standard tables.

PostgreSQL does not auto-index FK columns. This migration adds indexes for
efficient JOINs and cascading deletes, and updates FK constraints to include
ON DELETE CASCADE at the database level.

Revision ID: 003
Revises: 002
Create Date: 2026-03-14

"""

from collections.abc import Sequence

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # -- Add FK indexes --
    op.create_index("ix_user_addresses_user_id", "user_addresses", ["user_id"])
    op.create_index("ix_saved_screeners_user_id", "saved_screeners", ["user_id"])
    op.create_index("ix_alert_configs_user_id", "alert_configs", ["user_id"])
    op.create_index("ix_alert_history_alert_config_id", "alert_history", ["alert_config_id"])

    # -- Replace FK constraints to add ON DELETE CASCADE --

    # user_addresses.user_id
    op.drop_constraint("fk_user_addresses_user_id", "user_addresses", type_="foreignkey")
    op.create_foreign_key(
        "fk_user_addresses_user_id",
        "user_addresses",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # saved_screeners.user_id
    op.drop_constraint("fk_saved_screeners_user_id", "saved_screeners", type_="foreignkey")
    op.create_foreign_key(
        "fk_saved_screeners_user_id",
        "saved_screeners",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # alert_configs.user_id
    op.drop_constraint("fk_alert_configs_user_id", "alert_configs", type_="foreignkey")
    op.create_foreign_key(
        "fk_alert_configs_user_id",
        "alert_configs",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )

    # alert_history.alert_config_id
    op.drop_constraint("fk_alert_history_alert_config_id", "alert_history", type_="foreignkey")
    op.create_foreign_key(
        "fk_alert_history_alert_config_id",
        "alert_history",
        "alert_configs",
        ["alert_config_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    # -- Restore FK constraints without CASCADE --
    op.drop_constraint("fk_alert_history_alert_config_id", "alert_history", type_="foreignkey")
    op.create_foreign_key(
        "fk_alert_history_alert_config_id",
        "alert_history",
        "alert_configs",
        ["alert_config_id"],
        ["id"],
    )

    op.drop_constraint("fk_alert_configs_user_id", "alert_configs", type_="foreignkey")
    op.create_foreign_key(
        "fk_alert_configs_user_id", "alert_configs", "users", ["user_id"], ["id"]
    )

    op.drop_constraint("fk_saved_screeners_user_id", "saved_screeners", type_="foreignkey")
    op.create_foreign_key(
        "fk_saved_screeners_user_id", "saved_screeners", "users", ["user_id"], ["id"]
    )

    op.drop_constraint("fk_user_addresses_user_id", "user_addresses", type_="foreignkey")
    op.create_foreign_key(
        "fk_user_addresses_user_id", "user_addresses", "users", ["user_id"], ["id"]
    )

    # -- Drop FK indexes --
    op.drop_index("ix_alert_history_alert_config_id", table_name="alert_history")
    op.drop_index("ix_alert_configs_user_id", table_name="alert_configs")
    op.drop_index("ix_saved_screeners_user_id", table_name="saved_screeners")
    op.drop_index("ix_user_addresses_user_id", table_name="user_addresses")

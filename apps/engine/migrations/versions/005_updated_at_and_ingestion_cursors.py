"""Add updated_at columns and ingestion_cursors table.

Adds updated_at to users and alert_configs for audit trails.
Creates ingestion_cursors table for pipeline resumability.

Revision ID: 005
Revises: 004
Create Date: 2026-03-14

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Add updated_at to users
    op.add_column(
        "users",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Add updated_at to alert_configs
    op.add_column(
        "alert_configs",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    # Create ingestion_cursors table
    op.create_table(
        "ingestion_cursors",
        sa.Column("source", sa.String(100), nullable=False),
        sa.Column("last_processed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_block_number", sa.BigInteger(), nullable=True),
        sa.Column("metadata_json", JSONB(), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("source"),
    )


def downgrade() -> None:
    op.drop_table("ingestion_cursors")
    op.drop_column("alert_configs", "updated_at")
    op.drop_column("users", "updated_at")

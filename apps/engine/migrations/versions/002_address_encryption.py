"""Address encryption — coldkey_address now AES-256-GCM encrypted at the ORM layer.

Column type remains String(512); encryption is handled by the EncryptedString
TypeDecorator. No schema change needed — this migration documents the behavioral
change and ensures migration ordering.

Revision ID: 002
Revises: 001
Create Date: 2026-03-14

"""

from collections.abc import Sequence

revision: str = "002"
down_revision: str | None = "001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # No schema change — encryption handled by ORM TypeDecorator.
    # Existing plaintext rows will need a data migration if any exist.
    pass


def downgrade() -> None:
    # No schema change to reverse.
    pass

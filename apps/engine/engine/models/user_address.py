"""Standard table: user_addresses (encrypted coldkeys)."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.database import Base
from engine.core.encryption import EncryptedString


class UserAddress(Base):
    """User-linked coldkey address (encrypted at rest via AES-256-GCM)."""

    __tablename__ = "user_addresses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    coldkey_address: Mapped[str] = mapped_column(EncryptedString, nullable=False)
    label: Mapped[str | None] = mapped_column(String(100), nullable=True)
    is_watch_only: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="addresses")  # type: ignore[name-defined]  # noqa: F821

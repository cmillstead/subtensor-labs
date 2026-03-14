"""Standard table: users."""

from datetime import datetime

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.database import Base


class User(Base):
    """User account for authentication and saved data."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    premium_status: Mapped[str] = mapped_column(String(20), nullable=False, server_default="free")
    premium_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    addresses: Mapped[list["UserAddress"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    alert_configs: Mapped[list["AlertConfig"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )
    saved_screeners: Mapped[list["SavedScreener"]] = relationship(  # noqa: F821
        back_populates="user", cascade="all, delete-orphan"
    )

"""Standard table: alert_configs."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.database import Base


class AlertConfig(Base):
    """User-configured alert definition."""

    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    delivery_channels_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    user: Mapped["User"] = relationship(back_populates="alert_configs")  # type: ignore[name-defined]  # noqa: F821
    history: Mapped[list["AlertHistory"]] = relationship(  # type: ignore[name-defined]  # noqa: F821
        back_populates="alert_config", cascade="all, delete-orphan"
    )

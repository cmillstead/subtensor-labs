"""Standard table: alert_configs."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.database import Base


class AlertConfig(Base):
    """User-configured alert definition."""

    __tablename__ = "alert_configs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    type: Mapped[str] = mapped_column(String(20), nullable=False)
    conditions_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    delivery_channels_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    user: Mapped["User"] = relationship(back_populates="alert_configs")  # noqa: F821
    history: Mapped[list["AlertHistory"]] = relationship(  # noqa: F821
        back_populates="alert_config", cascade="all, delete-orphan"
    )

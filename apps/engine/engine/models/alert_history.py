"""Standard table: alert_history."""

from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from engine.core.database import Base


class AlertHistory(Base):
    """Record of a triggered alert."""

    __tablename__ = "alert_history"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_config_id: Mapped[int] = mapped_column(
        ForeignKey("alert_configs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    context_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    acknowledged: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    alert_config: Mapped["AlertConfig"] = relationship(back_populates="history")  # noqa: F821

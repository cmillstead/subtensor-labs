"""TimescaleDB hypertable: portfolio_snapshots."""

from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class PortfolioSnapshot(Base):
    """Daily portfolio value snapshot (TimescaleDB hypertable, 1-day chunks)."""

    __tablename__ = "portfolio_snapshots"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, primary_key=True)
    total_value_tao: Mapped[float] = mapped_column(Float, nullable=False)
    per_subnet_json: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)

    __table_args__ = (Index("ix_portfolio_snapshots_user_id_time", "user_id", time.desc()),)

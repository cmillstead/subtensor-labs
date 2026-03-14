"""TimescaleDB hypertable: alpha_prices."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class AlphaPrice(Base):
    """Alpha token price record (TimescaleDB hypertable, 1-day chunks)."""

    __tablename__ = "alpha_prices"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    netuid: Mapped[int] = mapped_column(Integer, primary_key=True)
    price_tao: Mapped[float] = mapped_column(Float, nullable=False)
    tao_reserve: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_reserve: Mapped[float] = mapped_column(Float, nullable=False)
    volume_24h: Mapped[float | None] = mapped_column(Float, nullable=True)

    __table_args__ = (Index("ix_alpha_prices_netuid_time", "netuid", time.desc()),)

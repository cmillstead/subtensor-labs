"""TimescaleDB hypertable: emission_records."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class EmissionRecord(Base):
    """Per-subnet emission data (TimescaleDB hypertable, 1-day chunks)."""

    __tablename__ = "emission_records"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    netuid: Mapped[int] = mapped_column(Integer, primary_key=True)
    emission_tao: Mapped[float] = mapped_column(Float, nullable=False)
    emission_share_pct: Mapped[float] = mapped_column(Float, nullable=False)
    net_tao_inflow: Mapped[float] = mapped_column(Float, nullable=False)
    cumulative_stake: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (Index("ix_emission_records_netuid_time", "netuid", time.desc()),)

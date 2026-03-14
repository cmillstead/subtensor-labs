"""TimescaleDB hypertable: subnet_snapshots."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class SubnetSnapshot(Base):
    """Per-subnet metrics snapshot (TimescaleDB hypertable, 1-day chunks)."""

    __tablename__ = "subnet_snapshots"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    netuid: Mapped[int] = mapped_column(Integer, primary_key=True)
    miner_count: Mapped[int] = mapped_column(Integer, nullable=False)
    validator_count: Mapped[int] = mapped_column(Integer, nullable=False)
    emission_share: Mapped[float] = mapped_column(Float, nullable=False)
    registration_cost: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_price: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_market_cap: Mapped[float] = mapped_column(Float, nullable=False)
    tao_reserves: Mapped[float] = mapped_column(Float, nullable=False)
    alpha_reserves: Mapped[float] = mapped_column(Float, nullable=False)
    fill_rate: Mapped[float] = mapped_column(Float, nullable=False)
    owner_take_rate: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index("ix_subnet_snapshots_netuid_time", "netuid", time.desc()),
    )

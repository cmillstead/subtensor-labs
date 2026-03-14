"""TimescaleDB hypertable: metagraph_entries."""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class MetagraphEntry(Base):
    """Per-neuron metagraph data (TimescaleDB hypertable, 1-day chunks)."""

    __tablename__ = "metagraph_entries"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    netuid: Mapped[int] = mapped_column(Integer, primary_key=True)
    uid: Mapped[int] = mapped_column(Integer, primary_key=True)
    hotkey: Mapped[str] = mapped_column(String(48), nullable=False)
    coldkey: Mapped[str] = mapped_column(String(48), nullable=False)
    stake: Mapped[float] = mapped_column(Float, nullable=False)
    incentive: Mapped[float] = mapped_column(Float, nullable=False)
    trust: Mapped[float] = mapped_column(Float, nullable=False)
    dividends: Mapped[float] = mapped_column(Float, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")

    __table_args__ = (
        Index("ix_metagraph_entries_netuid_time", "netuid", time.desc()),
        Index("ix_metagraph_entries_coldkey", "coldkey"),
        Index("ix_metagraph_entries_hotkey", "hotkey"),
    )

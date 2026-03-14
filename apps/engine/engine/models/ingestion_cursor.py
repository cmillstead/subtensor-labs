"""Standard table: ingestion_cursors for pipeline resumability."""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from engine.core.database import Base


class IngestionCursor(Base):
    """Tracks the last-processed position for each data ingestion source."""

    __tablename__ = "ingestion_cursors"

    source: Mapped[str] = mapped_column(String(100), primary_key=True)
    last_processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_block_number: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

"""Pydantic v2 request/response schemas for portfolio history."""

import re
from typing import Literal

from pydantic import field_validator

from engine.schemas import BaseSchema

# SS58 address pattern: base58 characters, typically 48 chars for Bittensor
_SS58_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{46,48}$")

_MAX_ADDRESSES = 20


class PortfolioHistoryRequestSchema(BaseSchema):
    """Request schema for portfolio history."""

    coldkey_addresses: list[str]
    time_range: Literal["7d", "30d", "90d"]

    @field_validator("coldkey_addresses")
    @classmethod
    def validate_addresses(cls, v: list[str]) -> list[str]:
        if not v:
            raise ValueError("At least one coldkey address is required")
        if len(v) > _MAX_ADDRESSES:
            raise ValueError(f"Maximum {_MAX_ADDRESSES} addresses allowed")
        for addr in v:
            if not _SS58_PATTERN.match(addr):
                raise ValueError(f"Invalid SS58 address format: {addr}")
        return v


class PortfolioHistoryPointSchema(BaseSchema):
    """A single data point in portfolio history."""

    time: str
    total_value_tao: float


class PortfolioHistoryResponseSchema(BaseSchema):
    """Response schema for portfolio history."""

    points: list[PortfolioHistoryPointSchema]
    data_start: str | None
    time_range: str

"""Pydantic v2 request/response schemas for portfolio aggregation."""

import re

from pydantic import field_validator

from engine.schemas import BaseSchema

# SS58 address pattern: base58 characters, typically 48 chars for Bittensor
_SS58_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{46,48}$")

_MAX_ADDRESSES = 20


class SubnetPositionSchema(BaseSchema):
    """Per-subnet position detail for a portfolio."""

    netuid: int
    hotkey: str
    staked_tao: float
    alpha_value_tao: float
    emission_share: float
    incentive: float
    trust: float
    dividends: float
    is_active: bool
    is_miner: bool


class ColdkeyPortfolioSchema(BaseSchema):
    """Portfolio data for a single coldkey address."""

    coldkey: str
    total_value_tao: float
    total_staked_tao: float
    total_alpha_value_tao: float
    positions: list[SubnetPositionSchema]
    subnets_exposed: int


class PortfolioResponseSchema(BaseSchema):
    """Unified portfolio response across one or more coldkeys."""

    total_value_tao: float
    total_staked_tao: float
    total_alpha_value_tao: float
    positions: list[SubnetPositionSchema]
    subnets_exposed: int
    coldkeys_resolved: int
    last_updated: str


class PortfolioRequestSchema(BaseSchema):
    """Request schema for portfolio aggregation."""

    coldkey_addresses: list[str]

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

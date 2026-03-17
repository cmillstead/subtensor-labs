"""Pydantic v2 request/response schemas for yield projections."""

import re

from pydantic import field_validator

from engine.schemas import BaseSchema

_SS58_PATTERN = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{46,48}$")

_MAX_ADDRESSES = 20
_VALID_HORIZONS = {30, 60, 90}

YIELD_CAVEAT = (
    "Based on trend extrapolation. Not financial advice. "
    "Past emission trends do not guarantee future results."
)


class YieldProjectionRequestSchema(BaseSchema):
    """Request schema for yield projection."""

    coldkey_addresses: list[str]
    horizons: list[int] = [30, 60, 90]

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

    @field_validator("horizons")
    @classmethod
    def validate_horizons(cls, v: list[int]) -> list[int]:
        if not v:
            raise ValueError("At least one horizon is required")
        for h in v:
            if h not in _VALID_HORIZONS:
                raise ValueError(f"Invalid horizon {h}, must be one of {_VALID_HORIZONS}")
        return sorted(v)


class YieldChartPointSchema(BaseSchema):
    """A single point in the yield projection time-series chart."""

    day: int
    projected_yield_tao: float
    confidence_68_lower: float
    confidence_68_upper: float
    confidence_95_lower: float
    confidence_95_upper: float


class SubnetYieldProjectionSchema(BaseSchema):
    """Yield projection for a single subnet at a given horizon."""

    netuid: int
    subnet_name: str | None = None
    current_stake_tao: float
    projected_yield_tao: float
    emission_trend_slope: float
    r_squared: float
    confidence_68_lower: float
    confidence_68_upper: float
    confidence_95_lower: float
    confidence_95_upper: float
    has_volatility_warning: bool


class HorizonProjectionSchema(BaseSchema):
    """Aggregated yield projection for a specific time horizon."""

    horizon_days: int
    total_projected_yield_tao: float
    total_confidence_68_lower: float
    total_confidence_68_upper: float
    total_confidence_95_lower: float
    total_confidence_95_upper: float
    subnet_projections: list[SubnetYieldProjectionSchema]


class YieldProjectionResponseSchema(BaseSchema):
    """Complete yield projection response."""

    projections: list[HorizonProjectionSchema]
    chart_data: list[YieldChartPointSchema]
    caveat: str = YIELD_CAVEAT
    last_computed: str
    total_staked_tao: float
    subnets_analyzed: int
    subnets_skipped: int

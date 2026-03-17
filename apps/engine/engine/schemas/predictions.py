"""Pydantic v2 request/response schemas for predictions (yield + scenario)."""

import re
from typing import Any

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


# --- Scenario Calculator Schemas ---

_MAX_SCENARIOS = 5
_MAX_MOVES_PER_SCENARIO = 10
_MAX_HORIZON = 365


class ScenarioMoveSchema(BaseSchema):
    """A single TAO rebalancing move within a scenario."""

    source_netuid: int
    dest_netuid: int
    amount_tao: float

    @field_validator("amount_tao")
    @classmethod
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("Move amount must be positive")
        return v

    @field_validator("dest_netuid")
    @classmethod
    def validate_different_subnets(cls, v: int, info: Any) -> int:
        source = info.data.get("source_netuid")
        if source is not None and v == source:
            raise ValueError("Source and destination subnets must differ")
        return v


class ScenarioInputSchema(BaseSchema):
    """A single scenario consisting of one or more moves."""

    label: str | None = None
    moves: list[ScenarioMoveSchema]

    @field_validator("moves")
    @classmethod
    def validate_moves(cls, v: list[ScenarioMoveSchema]) -> list[ScenarioMoveSchema]:
        if not v:
            raise ValueError("At least one move is required per scenario")
        if len(v) > _MAX_MOVES_PER_SCENARIO:
            raise ValueError(f"Maximum {_MAX_MOVES_PER_SCENARIO} moves per scenario")
        return v


class ScenarioCalcRequestSchema(BaseSchema):
    """Request for scenario comparison calculation."""

    coldkey_addresses: list[str]
    scenarios: list[ScenarioInputSchema]
    horizon: int = 90

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

    @field_validator("scenarios")
    @classmethod
    def validate_scenarios(
        cls,
        v: list[ScenarioInputSchema],
    ) -> list[ScenarioInputSchema]:
        if not v:
            raise ValueError("At least one scenario is required")
        if len(v) > _MAX_SCENARIOS:
            raise ValueError(f"Maximum {_MAX_SCENARIOS} scenarios allowed")
        return v

    @field_validator("horizon")
    @classmethod
    def validate_horizon(cls, v: int) -> int:
        if v < 1 or v > _MAX_HORIZON:
            raise ValueError(f"Horizon must be between 1 and {_MAX_HORIZON} days")
        return v


class SubnetAllocationSchema(BaseSchema):
    """Per-subnet allocation and yield within a scenario outcome."""

    netuid: int
    stake_tao: float
    allocation_pct: float
    projected_yield_tao: float
    confidence_68_lower: float
    confidence_68_upper: float
    alpha_price: float | None = None
    alpha_exposure_tao: float | None = None


class ScenarioOutcomeSchema(BaseSchema):
    """Full outcome for a single scenario (or the baseline)."""

    label: str | None = None
    allocations: list[SubnetAllocationSchema]
    total_staked_tao: float
    total_projected_yield_tao: float
    total_confidence_68_lower: float
    total_confidence_68_upper: float
    total_alpha_exposure_tao: float
    hhi: float
    yield_delta_tao: float = 0.0
    yield_delta_pct: float = 0.0


class ScenarioComparisonResponseSchema(BaseSchema):
    """Complete scenario comparison response."""

    baseline: ScenarioOutcomeSchema
    scenarios: list[ScenarioOutcomeSchema]
    best_yield_index: int
    best_diversification_index: int
    horizon_days: int
    caveat: str = YIELD_CAVEAT
    last_computed: str

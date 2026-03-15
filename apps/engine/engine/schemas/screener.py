"""Pydantic v2 request/response schemas for screener queries."""

from engine.schemas import BaseSchema


class ScreenerSubnetSchema(BaseSchema):
    """Per-subnet data for the screener table."""

    netuid: int
    name: str | None = None
    miner_count: int
    validator_count: int
    registration_cost: float
    emission_share: float
    alpha_price: float
    alpha_market_cap: float
    fill_rate: float
    owner_take_rate: float
    tao_reserves: float
    alpha_reserves: float
    subnet_age_days: int
    sparkline_emission_7d: list[float]
    sparkline_price_7d: list[float]


class ScreenerResponseSchema(BaseSchema):
    """Response for screener query."""

    subnets: list[ScreenerSubnetSchema]
    subnet_count: int

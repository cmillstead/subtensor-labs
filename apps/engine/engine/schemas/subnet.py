"""Pydantic v2 request/response schemas for subnet detail."""

from engine.schemas import BaseSchema


class SubnetDetailSchema(BaseSchema):
    """Current snapshot for a single subnet with computed fields."""

    netuid: int
    name: str | None = None
    miner_count: int
    validator_count: int
    registration_cost: float
    emission_share: float
    alpha_price: float
    alpha_market_cap: float
    tao_reserves: float
    alpha_reserves: float
    fill_rate: float
    owner_take_rate: float
    subnet_age_days: int
    description: str | None = None


class SubnetHistoryPointSchema(BaseSchema):
    """Daily aggregated history point for time-series charts."""

    time: str
    emission_share: float
    alpha_price: float
    miner_count: int


class SubnetNeuronSchema(BaseSchema):
    """A single neuron (miner or validator) in a subnet."""

    uid: int
    hotkey: str
    coldkey: str
    stake: float
    incentive: float
    trust: float
    dividends: float
    is_active: bool


class SubnetDetailResponseSchema(BaseSchema):
    """Complete subnet detail response."""

    detail: SubnetDetailSchema
    history: list[SubnetHistoryPointSchema]
    miners: list[SubnetNeuronSchema]
    validators: list[SubnetNeuronSchema]

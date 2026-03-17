"""Shared test helpers and factories for portfolio tests."""

from engine.schemas.portfolio import ColdkeyPortfolioSchema, SubnetPositionSchema

COLDKEY_1 = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"
HOTKEY_2 = "5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw"


def make_position(
    netuid: int = 1,
    hotkey: str = HOTKEY_1,
    staked: float = 100.0,
    alpha: float = 50.0,
    emission_share: float = 0.05,
    incentive: float = 0.0,
    trust: float = 0.9,
    dividends: float = 0.1,
    is_active: bool = True,
    is_miner: bool = False,
) -> SubnetPositionSchema:
    """Create a SubnetPositionSchema with sensible defaults."""
    return SubnetPositionSchema(
        netuid=netuid,
        hotkey=hotkey,
        staked_tao=staked,
        alpha_value_tao=alpha,
        emission_share=emission_share,
        incentive=incentive,
        trust=trust,
        dividends=dividends,
        is_active=is_active,
        is_miner=is_miner,
    )


def make_coldkey_portfolio(
    coldkey: str = COLDKEY_1,
    positions: list[SubnetPositionSchema] | None = None,
) -> ColdkeyPortfolioSchema:
    """Create a ColdkeyPortfolioSchema with computed totals."""
    if positions is None:
        positions = [make_position()]
    staked = sum(p.staked_tao for p in positions)
    alpha = sum(p.alpha_value_tao for p in positions)
    netuids = {p.netuid for p in positions}
    return ColdkeyPortfolioSchema(
        coldkey=coldkey,
        total_value_tao=staked + alpha,
        total_staked_tao=staked,
        total_alpha_value_tao=alpha,
        positions=positions,
        subnets_exposed=len(netuids),
    )


def make_position_entry(
    netuid: int = 1,
    hotkey: str = HOTKEY_1,
    stake: float = 100.0,
    incentive: float = 0.0,
    trust: float = 0.9,
    dividends: float = 0.1,
    is_active: bool = True,
    emission_share: float = 0.05,
) -> dict:
    """Create a raw position entry dict for compute_position_details."""
    return {
        "netuid": netuid,
        "hotkey": hotkey,
        "stake": stake,
        "incentive": incentive,
        "trust": trust,
        "dividends": dividends,
        "is_active": is_active,
        "emission_share": emission_share,
    }

"""Per-subnet position detail computation."""

from typing import Any

from engine.schemas.portfolio import DelegationDetailSchema, SubnetPositionSchema

# Approximate blocks per year for APY estimation (12s block time)
_BLOCKS_PER_YEAR = 365.25 * 24 * 3600 / 12


def _compute_delegation(entry: dict[str, Any]) -> DelegationDetailSchema:
    """Build a delegation detail from a metagraph entry.

    Each entry represents a neuron (hotkey) owned by the coldkey.
    For validators (non-miners with stake), the hotkey IS the validator.
    """
    staked = float(entry.get("stake", 0.0) or 0.0)
    dividends = float(entry.get("dividends", 0.0) or 0.0)
    take_rate = float(entry.get("take_rate", 0.0) or 0.0)

    # Rough APY: annualize the dividends/stake ratio
    estimated_apy: float | None = None
    if staked > 0 and dividends > 0:
        estimated_apy = round((dividends / staked) * _BLOCKS_PER_YEAR * 100, 2)

    return DelegationDetailSchema(
        validator_hotkey=str(entry.get("hotkey", "")),
        validator_name=entry.get("validator_name"),
        delegated_amount=staked,
        estimated_apy=estimated_apy,
        take_rate=take_rate,
    )


def compute_position_details(
    entries: list[dict[str, Any]],
    prices: dict[int, float],
) -> list[SubnetPositionSchema]:
    """Compute per-subnet position details from metagraph entries and prices.

    Args:
        entries: List of dicts with keys matching MetagraphEntry columns
                 (netuid, hotkey, stake, incentive, trust, dividends, is_active).
        prices: Mapping of netuid -> alpha price in TAO.

    Returns:
        List of SubnetPositionSchema with computed values.
    """
    positions: list[SubnetPositionSchema] = []
    for entry in entries:
        netuid = int(entry["netuid"])
        staked_tao = float(entry.get("stake", 0.0) or 0.0)
        price = prices.get(netuid, 0.0)
        alpha_value = staked_tao * price if price else 0.0
        # Alpha holdings: inverse of price (TAO staked / price = alpha tokens)
        alpha_holdings = staked_tao / price if price > 0 else 0.0
        incentive = float(entry.get("incentive", 0.0) or 0.0)
        # A neuron is a miner if it has incentive > 0 (earns mining rewards)
        is_miner = incentive > 0.0

        delegation = _compute_delegation(entry)

        positions.append(
            SubnetPositionSchema(
                netuid=netuid,
                subnet_name=entry.get("subnet_name"),
                hotkey=str(entry.get("hotkey", "")),
                staked_tao=staked_tao,
                alpha_holdings=alpha_holdings,
                alpha_value_tao=alpha_value,
                emission_share=float(entry.get("emission_share", 0.0) or 0.0),
                incentive=incentive,
                trust=float(entry.get("trust", 0.0) or 0.0),
                dividends=float(entry.get("dividends", 0.0) or 0.0),
                is_active=bool(entry.get("is_active", False)),
                is_miner=is_miner,
                delegations=[delegation],
            )
        )
    return positions


def compute_totals(
    positions: list[SubnetPositionSchema],
) -> tuple[float, float, float]:
    """Compute aggregate totals from a list of positions.

    Returns:
        (total_staked_tao, total_alpha_value_tao, total_value_tao)
    """
    total_staked = sum(p.staked_tao for p in positions)
    total_alpha = sum(p.alpha_value_tao for p in positions)
    total_value = total_staked + total_alpha
    return total_staked, total_alpha, total_value

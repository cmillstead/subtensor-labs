"""What-if scenario calculator — algebraic rebalancing on top of yield projector."""

import hashlib
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.subnet_snapshot import SubnetSnapshot
from engine.predictions.yield_projector import (
    _MIN_DATA_POINTS,
    _get_emission_history,
    _get_user_stakes,
    _get_validator_take_rates,
    _project_subnet_yield,
)
from engine.schemas.predictions import (
    ScenarioCalcRequestSchema,
    ScenarioComparisonResponseSchema,
    ScenarioInputSchema,
    ScenarioOutcomeSchema,
    SubnetAllocationSchema,
)

log = get_logger(__name__)

_CACHE_KEY_PREFIX = "prediction"


def _scenario_cache_key(user_id: str, request_body: ScenarioCalcRequestSchema) -> str:
    """Build a cache key that includes a hash of the scenario request."""
    body_json = request_body.model_dump_json()
    body_hash = hashlib.sha256(body_json.encode()).hexdigest()[:16]
    return f"{_CACHE_KEY_PREFIX}:{user_id}:scenario:{body_hash}"


def compute_hhi(allocations: list[SubnetAllocationSchema]) -> float:
    """Compute Herfindahl-Hirschman Index from allocation percentages.

    Returns a value between 0 (perfectly diversified) and 10000 (single position).
    """
    return sum(a.allocation_pct**2 for a in allocations)


def _build_outcome(
    stakes: dict[int, float],
    emission_history: dict[int, list[tuple[datetime, float]]],
    take_rates: dict[int, float],
    alpha_prices: dict[int, float],
    horizon: int,
    label: str | None = None,
    baseline_yield: float | None = None,
) -> ScenarioOutcomeSchema:
    """Build a ScenarioOutcomeSchema for a given set of stakes.

    This is the core algebraic computation shared between baseline and scenarios.
    """
    total_staked = sum(stakes.values())

    allocations: list[SubnetAllocationSchema] = []
    total_yield = 0.0
    total_ci68_lower = 0.0
    total_ci68_upper = 0.0
    total_alpha_exposure = 0.0

    for netuid, stake in stakes.items():
        if stake <= 0:
            continue

        history = emission_history.get(netuid, [])
        allocation_pct = (stake / total_staked * 100.0) if total_staked > 0 else 0.0

        # Alpha exposure
        price = alpha_prices.get(netuid)
        alpha_exp = stake * price if price is not None else None

        projected_yield = 0.0
        ci68_lower = 0.0
        ci68_upper = 0.0

        if len(history) >= _MIN_DATA_POINTS:
            take_rate = take_rates.get(netuid, 0.0)
            try:
                projections, _, _ = _project_subnet_yield(history, stake, take_rate, [horizon])
                proj = projections[0]
                projected_yield = proj.projected_yield_tao
                ci68_lower = proj.confidence_68_lower
                ci68_upper = proj.confidence_68_upper
            except ValueError:
                log.warning(
                    "scenario_subnet_projection_failed",
                    netuid=netuid,
                    exc_info=True,
                    worker="predictions",
                )

        total_yield += projected_yield
        total_ci68_lower += ci68_lower
        total_ci68_upper += ci68_upper
        if alpha_exp is not None:
            total_alpha_exposure += alpha_exp

        allocations.append(
            SubnetAllocationSchema(
                netuid=netuid,
                stake_tao=stake,
                allocation_pct=round(allocation_pct, 2),
                projected_yield_tao=projected_yield,
                confidence_68_lower=ci68_lower,
                confidence_68_upper=ci68_upper,
                alpha_price=price,
                alpha_exposure_tao=alpha_exp,
            )
        )

    hhi = compute_hhi(allocations)

    yield_delta = 0.0
    yield_delta_pct = 0.0
    if baseline_yield is not None:
        yield_delta = total_yield - baseline_yield
        yield_delta_pct = (yield_delta / baseline_yield * 100.0) if baseline_yield != 0 else 0.0

    return ScenarioOutcomeSchema(
        label=label,
        allocations=allocations,
        total_staked_tao=total_staked,
        total_projected_yield_tao=total_yield,
        total_confidence_68_lower=total_ci68_lower,
        total_confidence_68_upper=total_ci68_upper,
        total_alpha_exposure_tao=total_alpha_exposure,
        hhi=round(hhi, 2),
        yield_delta_tao=round(yield_delta, 6),
        yield_delta_pct=round(yield_delta_pct, 2),
    )


def apply_moves(
    base_stakes: dict[int, float],
    scenario: ScenarioInputSchema,
) -> dict[int, float] | str:
    """Apply scenario moves to a copy of the base stakes.

    Returns the modified stakes dict, or an error string if a move is invalid.
    """
    modified = dict(base_stakes)
    for move in scenario.moves:
        source_stake = modified.get(move.source_netuid, 0.0)
        if move.amount_tao > source_stake + 1e-9:  # Tolerance for float
            return (
                f"Move exceeds stake: cannot move {move.amount_tao} TAO from "
                f"SN{move.source_netuid} (has {source_stake} TAO)"
            )
        modified[move.source_netuid] = source_stake - move.amount_tao
        modified[move.dest_netuid] = modified.get(move.dest_netuid, 0.0) + move.amount_tao
    return modified


async def _get_alpha_prices(
    session: AsyncSession,
    netuids: list[int],
) -> dict[int, float]:
    """Get the latest alpha_price per subnet from subnet_snapshots."""
    latest_time_q = select(SubnetSnapshot.time).order_by(SubnetSnapshot.time.desc()).limit(1)
    latest_result = await session.execute(latest_time_q)
    latest_time = latest_result.scalar_one_or_none()
    if latest_time is None:
        return {}

    stmt = select(SubnetSnapshot.netuid, SubnetSnapshot.alpha_price).where(
        SubnetSnapshot.netuid.in_(netuids),
        SubnetSnapshot.time == latest_time,
    )
    result = await session.execute(stmt)
    return {int(netuid): float(price) for netuid, price in result.all()}


async def compute_scenario(
    user_id: str,
    request_body: ScenarioCalcRequestSchema,
) -> tuple[ScenarioComparisonResponseSchema, bool]:
    """Compute scenario comparison for a user's portfolio.

    Checks Redis cache first. On miss, queries DB, applies scenario moves,
    runs yield projections via the existing yield projector engine, and caches result.

    Returns:
        Tuple of (ScenarioComparisonResponseSchema, cache_hit).
    """
    cache_key = _scenario_cache_key(user_id, request_body)

    # Check Redis cache
    try:
        cached = await cache_get(cache_key)
    except Exception:
        log.warning("scenario_cache_read_failed", user_id=user_id, exc_info=True)
        cached = None

    if cached is not None:
        try:
            response = ScenarioComparisonResponseSchema.model_validate_json(cached)
            log.info("scenario_cache_hit", user_id=user_id, worker="predictions")
            return response, True
        except Exception:
            log.warning("scenario_cache_deserialize_failed", user_id=user_id, exc_info=True)

    # Cache miss — compute from DB
    factory = get_session_factory()
    async with factory() as session:
        user_stakes = await _get_user_stakes(session, request_body.coldkey_addresses)

        if not user_stakes:
            empty_baseline = ScenarioOutcomeSchema(
                label="Current",
                allocations=[],
                total_staked_tao=0.0,
                total_projected_yield_tao=0.0,
                total_confidence_68_lower=0.0,
                total_confidence_68_upper=0.0,
                total_alpha_exposure_tao=0.0,
                hhi=0.0,
            )
            response = ScenarioComparisonResponseSchema(
                baseline=empty_baseline,
                scenarios=[],
                best_yield_index=0,
                best_diversification_index=0,
                horizon_days=request_body.horizon,
                last_computed=datetime.now(UTC).isoformat(),
            )
            return response, False

        # Collect all netuids: current stakes + scenario destinations
        all_netuids = set(user_stakes.keys())
        for scenario in request_body.scenarios:
            for move in scenario.moves:
                all_netuids.add(move.source_netuid)
                all_netuids.add(move.dest_netuid)
        all_netuids_list = list(all_netuids)

        emission_history = await _get_emission_history(session, all_netuids_list)
        take_rates = await _get_validator_take_rates(session, all_netuids_list)
        alpha_prices = await _get_alpha_prices(session, all_netuids_list)

    horizon = request_body.horizon

    # Compute baseline outcome
    baseline = _build_outcome(
        user_stakes, emission_history, take_rates, alpha_prices, horizon, label="Current"
    )
    baseline_yield = baseline.total_projected_yield_tao

    # Compute each scenario outcome
    scenario_outcomes: list[ScenarioOutcomeSchema] = []
    for i, scenario in enumerate(request_body.scenarios):
        modified_stakes = apply_moves(user_stakes, scenario)
        if isinstance(modified_stakes, str):
            # Invalid move — return error as a zero-yield scenario with the error as label
            log.warning(
                "scenario_invalid_move",
                user_id=user_id,
                scenario_index=i,
                error=modified_stakes,
                worker="predictions",
            )
            scenario_outcomes.append(
                ScenarioOutcomeSchema(
                    label=f"Error: {modified_stakes}",
                    allocations=[],
                    total_staked_tao=0.0,
                    total_projected_yield_tao=0.0,
                    total_confidence_68_lower=0.0,
                    total_confidence_68_upper=0.0,
                    total_alpha_exposure_tao=0.0,
                    hhi=0.0,
                    yield_delta_tao=0.0,
                    yield_delta_pct=0.0,
                )
            )
            continue

        outcome = _build_outcome(
            modified_stakes,
            emission_history,
            take_rates,
            alpha_prices,
            horizon,
            label=scenario.label or f"Scenario {i + 1}",
            baseline_yield=baseline_yield,
        )
        scenario_outcomes.append(outcome)

    # Find best yield and best diversification (only among valid scenarios)
    best_yield_idx = 0
    best_div_idx = 0
    valid_scenarios = [(i, s) for i, s in enumerate(scenario_outcomes) if s.allocations]
    if valid_scenarios:
        best_yield_idx = max(
            valid_scenarios,
            key=lambda x: x[1].total_projected_yield_tao,
        )[0]
        best_div_idx = min(valid_scenarios, key=lambda x: x[1].hhi)[0]

    response = ScenarioComparisonResponseSchema(
        baseline=baseline,
        scenarios=scenario_outcomes,
        best_yield_index=best_yield_idx,
        best_diversification_index=best_div_idx,
        horizon_days=horizon,
        last_computed=datetime.now(UTC).isoformat(),
    )

    # Cache the result
    try:
        await cache_set(cache_key, response.model_dump_json(), settings.cache_ttl_prediction)
        log.info(
            "scenario_cached",
            user_id=user_id,
            num_scenarios=len(scenario_outcomes),
            worker="predictions",
        )
    except Exception:
        log.warning("scenario_cache_write_failed", user_id=user_id, exc_info=True)

    return response, False

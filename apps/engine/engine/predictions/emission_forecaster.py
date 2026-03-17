"""Emission trajectory forecasting via exponential moving averages on net TAO inflow."""

from datetime import UTC, datetime, timedelta
from typing import Literal

import numpy as np
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.emission_record import EmissionRecord
from engine.models.subnet_snapshot import SubnetSnapshot
from engine.schemas.predictions import (
    EmissionForecastRequestSchema,
    EmissionForecastResponseSchema,
    HalvingImpactSchema,
    SubnetEmissionForecastPointSchema,
    SubnetEmissionForecastSchema,
    SubnetStakingMigrationSchema,
)

log = get_logger(__name__)

# Minimum data points required for EMA computation
_MIN_DATA_POINTS = 7

# EMA span (days) — captures ~2 weeks of momentum
_EMA_SPAN = 14

# Lookback days for emission history
_LOOKBACK_DAYS = 90

# Bittensor halving constants
HALVING_INTERVAL_BLOCKS = 10_500_000  # ~4 years at 12s/block
GENESIS_EMISSION_PER_BLOCK = 1.0  # TAO per block at genesis (pre-halving)
BLOCKS_PER_DAY = 7_200  # 12s block time
TAO_PER_DAY = GENESIS_EMISSION_PER_BLOCK / 2 * BLOCKS_PER_DAY  # 3,600 TAO/day (post-first-halving)

# First halving block (approximate — Bittensor genesis + interval)
FIRST_HALVING_BLOCK = 10_500_000

# Cache key
_CACHE_KEY_PREFIX = "prediction"

# EMA momentum threshold for trend classification.
# Values smaller than ±0.01 pct/day are classified as "stable".
# Calibrated against historical subnet emission volatility —
# most subnets fluctuate ±0.005-0.02 pct/day in steady state.
_MOMENTUM_THRESHOLD = 0.01


def _cache_key() -> str:
    return f"{_CACHE_KEY_PREFIX}:emission:global"


def compute_ema(values: list[float], span: int = _EMA_SPAN) -> list[float]:
    """Compute exponential moving average.

    Args:
        values: Time-series values (oldest first).
        span: EMA span in periods.

    Returns:
        EMA values (same length as input).
    """
    alpha = 2.0 / (span + 1)
    ema = [values[0]]
    for i in range(1, len(values)):
        ema.append(alpha * values[i] + (1 - alpha) * ema[-1])
    return ema


def project_emission_trajectory(
    emission_shares: list[float],
    horizon_days: int,
    span: int = _EMA_SPAN,
) -> dict[str, list[float] | float]:
    """Project emission share forward using EMA momentum with decay.

    The EMA momentum (daily change in EMA) is extrapolated forward,
    decaying linearly to zero over the projection horizon. Confidence
    bands widen with sqrt(days_ahead) scaled by historical volatility.

    Args:
        emission_shares: Historical emission_share_pct values (oldest first).
        horizon_days: Number of days to project forward.
        span: EMA span for smoothing.

    Returns:
        Dictionary with keys: predicted, lower_68, upper_68, lower_95, upper_95, momentum
    """
    ema_values = compute_ema(emission_shares, span)

    # Current EMA value and momentum (daily delta)
    current_ema = ema_values[-1]
    momentum = ema_values[-1] - ema_values[-2] if len(ema_values) >= 2 else 0.0

    # Historical volatility (std dev of daily changes in emission_share)
    if len(emission_shares) >= 3:
        daily_changes = np.diff(emission_shares)
        volatility = float(np.std(daily_changes, ddof=1))
    else:
        volatility = 0.0

    # Project forward: momentum decays linearly to zero over horizon
    predicted = []
    lower_68 = []
    upper_68 = []
    lower_95 = []
    upper_95 = []

    cumulative_change = 0.0
    for day in range(1, horizon_days + 1):
        # Linear decay: momentum goes from full to zero over horizon
        decay_factor = max(0.0, 1.0 - day / horizon_days)
        daily_projected_change = momentum * decay_factor
        cumulative_change += daily_projected_change

        proj_value = max(0.0, current_ema + cumulative_change)
        predicted.append(proj_value)

        # Confidence bands widen with sqrt(time)
        band_68 = volatility * np.sqrt(day)
        band_95 = 1.96 * volatility * np.sqrt(day)

        lower_68.append(max(0.0, proj_value - band_68))
        upper_68.append(proj_value + band_68)
        lower_95.append(max(0.0, proj_value - band_95))
        upper_95.append(proj_value + band_95)

    return {
        "predicted": predicted,
        "lower_68": lower_68,
        "upper_68": upper_68,
        "lower_95": lower_95,
        "upper_95": upper_95,
        "momentum": momentum,
    }


def classify_trend(momentum: float) -> Literal["rising", "falling", "stable"]:
    """Classify EMA trend based on momentum magnitude."""
    if momentum > _MOMENTUM_THRESHOLD:
        return "rising"
    elif momentum < -_MOMENTUM_THRESHOLD:
        return "falling"
    return "stable"


def compute_halving_impact(
    current_block: int,
    horizon_days: int,
) -> HalvingImpactSchema:
    """Compute halving countdown and network-level emission impact.

    Uses genesis emission rate and number of halvings passed to derive the
    current per-block rate, avoiding double-counting.

    Args:
        current_block: Current Bittensor block number.
        horizon_days: Projection horizon in days.

    Returns:
        HalvingImpactSchema with countdown and network-level yield impact.
    """
    # Calculate next halving block
    halvings_passed = current_block // HALVING_INTERVAL_BLOCKS
    next_halving_block = (halvings_passed + 1) * HALVING_INTERVAL_BLOCKS
    blocks_remaining = max(0, next_halving_block - current_block)

    # Time remaining
    seconds_remaining = blocks_remaining * 12  # 12s per block
    days_remaining = seconds_remaining / 86400.0

    # Current daily emission rate (H5 fix: derive from genesis rate)
    current_rate = GENESIS_EMISSION_PER_BLOCK / (2**halvings_passed)
    current_daily = current_rate * BLOCKS_PER_DAY

    # Post-halving rate
    post_halving_daily = current_daily / 2.0

    # Network-level yield impact over horizon
    yield_impact_pct = -50.0  # Halving always reduces emissions by 50%
    yield_impact_tao = -(current_daily - post_halving_daily) * horizon_days

    return HalvingImpactSchema(
        blocks_remaining=blocks_remaining,
        estimated_days_remaining=round(days_remaining, 1),
        current_emission_per_day_tao=current_daily,
        post_halving_emission_per_day_tao=post_halving_daily,
        estimated_yield_impact_pct=yield_impact_pct,
        estimated_yield_impact_tao=round(yield_impact_tao, 4),
    )


async def _get_all_emission_history(
    session: AsyncSession,
    lookback_days: int = _LOOKBACK_DAYS,
) -> dict[int, list[tuple[datetime, float, float, float]]]:
    """Get historical emission data for ALL subnets.

    Returns:
        Dict mapping netuid → list of (time, emission_share_pct, net_tao_inflow, cumulative_stake)
        sorted by time ascending.
    """
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    stmt = (
        select(
            EmissionRecord.netuid,
            EmissionRecord.time,
            EmissionRecord.emission_share_pct,
            EmissionRecord.net_tao_inflow,
            EmissionRecord.cumulative_stake,
        )
        .where(EmissionRecord.time >= cutoff)
        .order_by(EmissionRecord.netuid, EmissionRecord.time)
    )
    result = await session.execute(stmt)
    rows = result.all()

    history: dict[int, list[tuple[datetime, float, float, float]]] = {}
    for netuid, time, emission_share_pct, net_tao_inflow, cumulative_stake in rows:
        if netuid not in history:
            history[netuid] = []
        history[netuid].append(
            (time, float(emission_share_pct), float(net_tao_inflow), float(cumulative_stake))
        )

    return history


async def _get_latest_block_estimate(session: AsyncSession) -> int:
    """Estimate current block number from latest subnet snapshot time.

    Uses a rough estimate: blocks since genesis ≈ seconds_since_genesis / 12.
    Bittensor genesis approximate: 2021-11-15.
    """
    stmt = select(func.max(SubnetSnapshot.time))
    result = await session.execute(stmt)
    latest_time = result.scalar_one_or_none()

    if latest_time is None:
        return 0

    # Rough estimate: Bittensor genesis ~2021-11-15
    genesis = datetime(2021, 11, 15, tzinfo=UTC)
    if latest_time.tzinfo is None:
        latest_time = latest_time.replace(tzinfo=UTC)
    seconds_since_genesis = (latest_time - genesis).total_seconds()
    return int(seconds_since_genesis / 12)


async def _get_staking_migration(
    session: AsyncSession,
    lookback_days: int = 30,
) -> list[SubnetStakingMigrationSchema]:
    """Compute net TAO inflow/outflow per subnet over the lookback period.

    Returns list sorted by absolute magnitude (largest flows first).
    """
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    stmt = (
        select(
            EmissionRecord.netuid,
            func.sum(EmissionRecord.net_tao_inflow).label("total_inflow"),
            func.count().label("days"),
        )
        .where(EmissionRecord.time >= cutoff)
        .group_by(EmissionRecord.netuid)
        .order_by(func.abs(func.sum(EmissionRecord.net_tao_inflow)).desc())
        .limit(20)
    )
    result = await session.execute(stmt)
    rows = result.all()

    migrations = []
    for netuid, total_inflow, days in rows:
        total = float(total_inflow)
        avg_daily = total / max(int(days), 1)
        direction: Literal["inflow", "outflow"] = "inflow" if total >= 0 else "outflow"
        migrations.append(
            SubnetStakingMigrationSchema(
                netuid=int(netuid),
                net_tao_inflow_30d=round(total, 4),
                avg_daily_inflow=round(avg_daily, 4),
                direction=direction,
            )
        )

    return migrations


async def compute_emission_forecast(
    user_id: str,
    request_body: EmissionForecastRequestSchema,
) -> tuple[EmissionForecastResponseSchema, bool]:
    """Compute emission trajectory forecast.

    Checks Redis cache first. On miss, queries DB, runs EMA projections,
    computes halving impact and staking migration.

    Args:
        user_id: The user ID for cache keying.
        request_body: Request with coldkey addresses and horizons.

    Returns:
        Tuple of (EmissionForecastResponseSchema, cache_hit).
    """
    horizons = request_body.horizons
    max_horizon = max(horizons)

    cache_key = _cache_key()

    # Check Redis cache (global — computation is user-independent)
    try:
        cached = await cache_get(cache_key)
    except Exception:
        log.warning("emission_cache_read_failed", exc_info=True)
        cached = None

    if cached is not None:
        try:
            response = EmissionForecastResponseSchema.model_validate_json(cached)
            log.info("emission_cache_hit", user_id=user_id, worker="predictions")
            return response, True
        except Exception:
            log.warning("emission_cache_deserialize_failed", user_id=user_id, exc_info=True)

    # Cache miss — compute from DB
    factory = get_session_factory()
    async with factory() as session:
        # Get emission history for all subnets
        all_history = await _get_all_emission_history(session)

        # Get latest block estimate for halving countdown
        current_block = await _get_latest_block_estimate(session)

        # Get staking migration data
        staking_migration = await _get_staking_migration(session)

    # Project emission trajectories per subnet
    subnet_forecasts: list[SubnetEmissionForecastSchema] = []
    subnets_analyzed = 0
    subnets_skipped = 0

    for netuid, history in sorted(all_history.items()):
        if len(history) < _MIN_DATA_POINTS:
            log.info(
                "emission_subnet_skipped",
                netuid=netuid,
                data_points=len(history),
                min_required=_MIN_DATA_POINTS,
                worker="predictions",
            )
            subnets_skipped += 1
            continue

        emission_shares = [h[1] for h in history]

        try:
            projection = project_emission_trajectory(emission_shares, max_horizon)
        except Exception as exc:
            log.warning(
                "emission_projection_failed",
                netuid=netuid,
                error=str(exc),
                worker="predictions",
            )
            subnets_skipped += 1
            continue

        subnets_analyzed += 1
        momentum = float(projection["momentum"])  # type: ignore[arg-type]
        trend = classify_trend(momentum)

        # Extract projected lists (type narrowing for mypy)
        predicted = projection["predicted"]
        lower_68 = projection["lower_68"]
        upper_68 = projection["upper_68"]
        lower_95 = projection["lower_95"]
        upper_95 = projection["upper_95"]
        # Build chart data
        chart_data = [
            SubnetEmissionForecastPointSchema(
                day=day + 1,
                emission_share_pct=predicted[day],  # type: ignore[index]
                confidence_68_lower=lower_68[day],  # type: ignore[index]
                confidence_68_upper=upper_68[day],  # type: ignore[index]
                confidence_95_lower=lower_95[day],  # type: ignore[index]
                confidence_95_upper=upper_95[day],  # type: ignore[index]
            )
            for day in range(max_horizon)
        ]

        subnet_forecasts.append(
            SubnetEmissionForecastSchema(
                netuid=netuid,
                current_emission_share_pct=emission_shares[-1],
                ema_trend=trend,
                momentum=round(momentum, 6),
                chart_data=chart_data,
            )
        )

    # Compute halving impact (network-level, no per-user parameters needed)
    halving_impact = compute_halving_impact(
        current_block=current_block,
        horizon_days=max_horizon,
    )

    response = EmissionForecastResponseSchema(
        subnet_forecasts=subnet_forecasts,
        halving_impact=halving_impact,
        staking_migration=staking_migration,
        last_computed=datetime.now(UTC).isoformat(),
        subnets_analyzed=subnets_analyzed,
        subnets_skipped=subnets_skipped,
    )

    # Cache the result
    try:
        await cache_set(cache_key, response.model_dump_json(), settings.cache_ttl_prediction)
        log.info(
            "emission_cached",
            user_id=user_id,
            subnets_analyzed=subnets_analyzed,
            subnets_skipped=subnets_skipped,
            worker="predictions",
        )
    except Exception:
        log.warning("emission_cache_write_failed", user_id=user_id, exc_info=True)

    return response, False

"""Staking yield forecasting via scipy linear regression on emission trends."""

from datetime import UTC, datetime, timedelta

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.emission_record import EmissionRecord
from engine.models.metagraph_entry import MetagraphEntry
from engine.models.subnet_snapshot import SubnetSnapshot
from engine.predictions.confidence import compute_confidence_bands
from engine.schemas.predictions import (
    HorizonProjectionSchema,
    SubnetYieldProjectionSchema,
    YieldChartPointSchema,
    YieldProjectionResponseSchema,
)

log = get_logger(__name__)

# Minimum data points required for regression
_MIN_DATA_POINTS = 7

# Subnets with fewer days than this get a volatility warning
_VOLATILITY_THRESHOLD_DAYS = 60

# Days of historical data to use for regression
_LOOKBACK_DAYS = 90

# Cache key pattern
_CACHE_KEY_PREFIX = "prediction"


def _cache_key(user_id: str) -> str:
    return f"{_CACHE_KEY_PREFIX}:{user_id}:yield"


async def _get_user_stakes(
    session: AsyncSession,
    coldkey_addresses: list[str],
) -> dict[int, float]:
    """Get user's total stake per subnet from latest metagraph entries.

    Returns:
        Dict mapping netuid → total_stake_tao for the user's coldkeys.
    """
    # Get the latest time in metagraph_entries
    latest_time_q = select(MetagraphEntry.time).order_by(MetagraphEntry.time.desc()).limit(1)
    latest_result = await session.execute(latest_time_q)
    latest_time = latest_result.scalar_one_or_none()
    if latest_time is None:
        return {}

    # Query all entries for user's coldkeys at the latest time
    stmt = select(MetagraphEntry.netuid, MetagraphEntry.stake).where(
        MetagraphEntry.time == latest_time,
        MetagraphEntry.coldkey.in_(coldkey_addresses),
        MetagraphEntry.is_active.is_(True),
    )
    result = await session.execute(stmt)
    rows = result.all()

    # Aggregate stake by netuid
    stakes: dict[int, float] = {}
    for netuid, stake in rows:
        stakes[netuid] = stakes.get(netuid, 0.0) + float(stake)

    return stakes


async def _get_emission_history(
    session: AsyncSession,
    netuids: list[int],
    lookback_days: int = _LOOKBACK_DAYS,
) -> dict[int, list[tuple[datetime, float]]]:
    """Get historical emission_share_pct for specified subnets.

    Returns:
        Dict mapping netuid → list of (time, emission_share_pct) sorted by time asc.
    """
    cutoff = datetime.now(UTC) - timedelta(days=lookback_days)

    stmt = (
        select(EmissionRecord.netuid, EmissionRecord.time, EmissionRecord.emission_share_pct)
        .where(
            EmissionRecord.netuid.in_(netuids),
            EmissionRecord.time >= cutoff,
        )
        .order_by(EmissionRecord.netuid, EmissionRecord.time)
    )
    result = await session.execute(stmt)
    rows = result.all()

    history: dict[int, list[tuple[datetime, float]]] = {}
    for netuid, time, emission_share_pct in rows:
        if netuid not in history:
            history[netuid] = []
        history[netuid].append((time, float(emission_share_pct)))

    return history


async def _get_validator_take_rates(
    session: AsyncSession,
    netuids: list[int],
) -> dict[int, float]:
    """Get the latest owner_take_rate per subnet from subnet_snapshots.

    Returns:
        Dict mapping netuid → owner_take_rate (0.0 to 1.0).
    """
    # Get the latest snapshot time
    latest_time_q = select(SubnetSnapshot.time).order_by(SubnetSnapshot.time.desc()).limit(1)
    latest_result = await session.execute(latest_time_q)
    latest_time = latest_result.scalar_one_or_none()
    if latest_time is None:
        return {}

    stmt = select(SubnetSnapshot.netuid, SubnetSnapshot.owner_take_rate).where(
        SubnetSnapshot.netuid.in_(netuids),
        SubnetSnapshot.time == latest_time,
    )
    result = await session.execute(stmt)

    return {int(netuid): float(rate) for netuid, rate in result.all()}


def _project_subnet_yield(
    emission_history: list[tuple[datetime, float]],
    stake_tao: float,
    take_rate: float,
    horizons: list[int],
) -> tuple[list[SubnetYieldProjectionSchema], list[YieldChartPointSchema], bool]:
    """Run regression on a single subnet's emission history and project yield.

    Returns:
        (per-horizon projections, chart data points, has_volatility_warning)
    """
    n = len(emission_history)
    has_warning = n < _VOLATILITY_THRESHOLD_DAYS

    # Convert to numpy arrays — days since first observation
    base_time = emission_history[0][0]
    x = np.array([(t - base_time).total_seconds() / 86400.0 for t, _ in emission_history])
    y = np.array([e for _, e in emission_history])

    # Build x_pred for chart data (daily from day 0 to max horizon)
    max_horizon = max(horizons)
    last_day = float(x[-1])
    x_chart = np.arange(last_day + 1, last_day + max_horizon + 1, dtype=np.float64)

    bands = compute_confidence_bands(x, y, x_chart, confidence_levels=[0.68, 0.95])
    predicted_emission = bands["predicted"]
    slope = float(bands["slope"][0])
    r_squared = float(bands["r_squared"][0])

    # Projected yield = stake_share * projected_emission * (1 - take_rate)
    # emission_share_pct is already a percentage (0-100), convert to fraction
    net_factor = stake_tao * (1.0 - take_rate) / 100.0

    # Generate chart data points (daily)
    chart_data: list[YieldChartPointSchema] = []
    for i, day_offset in enumerate(range(1, max_horizon + 1)):
        proj_emission = max(float(predicted_emission[i]), 0.0)
        chart_data.append(
            YieldChartPointSchema(
                day=day_offset,
                projected_yield_tao=proj_emission * net_factor * day_offset,
                confidence_68_lower=(
                    max(float(bands["lower_0.68"][i]), 0.0) * net_factor * day_offset
                ),
                confidence_68_upper=float(bands["upper_0.68"][i]) * net_factor * day_offset,
                confidence_95_lower=(
                    max(float(bands["lower_0.95"][i]), 0.0) * net_factor * day_offset
                ),
                confidence_95_upper=float(bands["upper_0.95"][i]) * net_factor * day_offset,
            )
        )

    # Generate per-horizon projections
    projections: list[SubnetYieldProjectionSchema] = []
    for horizon in horizons:
        idx = horizon - 1  # chart_data is 1-indexed by day
        point = chart_data[idx]
        projections.append(
            SubnetYieldProjectionSchema(
                netuid=0,  # Will be set by caller
                subnet_name=None,  # Will be set by caller
                current_stake_tao=stake_tao,
                projected_yield_tao=point.projected_yield_tao,
                emission_trend_slope=slope,
                r_squared=r_squared,
                confidence_68_lower=point.confidence_68_lower,
                confidence_68_upper=point.confidence_68_upper,
                confidence_95_lower=point.confidence_95_lower,
                confidence_95_upper=point.confidence_95_upper,
                has_volatility_warning=has_warning,
            )
        )

    return projections, chart_data, has_warning


async def compute_yield_projection(
    user_id: str,
    coldkey_addresses: list[str],
    horizons: list[int] | None = None,
) -> tuple[YieldProjectionResponseSchema, bool]:
    """Compute yield projections for a user's portfolio.

    Checks Redis cache first. On miss, queries DB, runs scipy regression,
    caches result.

    Args:
        user_id: The user ID for cache keying.
        coldkey_addresses: List of user's coldkey addresses.
        horizons: Projection horizons in days (default [30, 60, 90]).

    Returns:
        Tuple of (YieldProjectionResponseSchema, cache_hit).
    """
    if horizons is None:
        horizons = [30, 60, 90]
    horizons = sorted(horizons)

    cache_key = _cache_key(user_id)

    # Check Redis cache
    try:
        cached = await cache_get(cache_key)
    except Exception:
        log.warning("prediction_cache_read_failed", user_id=user_id, exc_info=True)
        cached = None

    if cached is not None:
        try:
            response = YieldProjectionResponseSchema.model_validate_json(cached)
            log.info("prediction_cache_hit", user_id=user_id, worker="predictions")
            return response, True
        except Exception:
            log.warning("prediction_cache_deserialize_failed", user_id=user_id, exc_info=True)

    # Cache miss — compute from DB
    factory = get_session_factory()
    async with factory() as session:
        # Step 1: Get user's stake per subnet
        user_stakes = await _get_user_stakes(session, coldkey_addresses)
        if not user_stakes:
            response = YieldProjectionResponseSchema(
                projections=[
                    HorizonProjectionSchema(
                        horizon_days=h,
                        total_projected_yield_tao=0.0,
                        total_confidence_68_lower=0.0,
                        total_confidence_68_upper=0.0,
                        total_confidence_95_lower=0.0,
                        total_confidence_95_upper=0.0,
                        subnet_projections=[],
                    )
                    for h in horizons
                ],
                chart_data=[],
                last_computed=datetime.now(UTC).isoformat(),
                total_staked_tao=0.0,
                subnets_analyzed=0,
                subnets_skipped=0,
            )
            return response, False

        staked_netuids = list(user_stakes.keys())

        # Step 2: Get emission history for staked subnets
        emission_history = await _get_emission_history(session, staked_netuids)

        # Step 3: Get validator take rates
        take_rates = await _get_validator_take_rates(session, staked_netuids)

    # Step 4: Run projection per subnet
    # Organize by horizon
    horizon_subnet_projections: dict[int, list[SubnetYieldProjectionSchema]] = {
        h: [] for h in horizons
    }
    aggregated_chart_data: list[YieldChartPointSchema] = []
    subnets_analyzed = 0
    subnets_skipped = 0

    for netuid in staked_netuids:
        history = emission_history.get(netuid, [])

        if len(history) < _MIN_DATA_POINTS:
            log.info(
                "subnet_skipped_insufficient_data",
                netuid=netuid,
                data_points=len(history),
                min_required=_MIN_DATA_POINTS,
                worker="predictions",
            )
            subnets_skipped += 1
            continue

        stake = user_stakes[netuid]
        take_rate = take_rates.get(netuid, 0.0)

        try:
            projections, chart_points, _has_warning = _project_subnet_yield(
                history, stake, take_rate, horizons
            )
        except ValueError as exc:
            log.warning(
                "subnet_projection_failed",
                netuid=netuid,
                error=str(exc),
                worker="predictions",
            )
            subnets_skipped += 1
            continue

        subnets_analyzed += 1

        # Set netuid on projections
        for proj in projections:
            proj.netuid = netuid

        # Add to per-horizon lists
        for i, horizon in enumerate(horizons):
            horizon_subnet_projections[horizon].append(projections[i])

        # Aggregate chart data (sum across subnets)
        if not aggregated_chart_data:
            aggregated_chart_data = [
                YieldChartPointSchema(
                    day=p.day,
                    projected_yield_tao=p.projected_yield_tao,
                    confidence_68_lower=p.confidence_68_lower,
                    confidence_68_upper=p.confidence_68_upper,
                    confidence_95_lower=p.confidence_95_lower,
                    confidence_95_upper=p.confidence_95_upper,
                )
                for p in chart_points
            ]
        else:
            for j, p in enumerate(chart_points):
                existing = aggregated_chart_data[j]
                aggregated_chart_data[j] = YieldChartPointSchema(
                    day=existing.day,
                    projected_yield_tao=existing.projected_yield_tao + p.projected_yield_tao,
                    confidence_68_lower=existing.confidence_68_lower + p.confidence_68_lower,
                    confidence_68_upper=existing.confidence_68_upper + p.confidence_68_upper,
                    confidence_95_lower=existing.confidence_95_lower + p.confidence_95_lower,
                    confidence_95_upper=existing.confidence_95_upper + p.confidence_95_upper,
                )

    # Step 5: Build horizon projections
    horizon_results: list[HorizonProjectionSchema] = []
    for horizon in horizons:
        subnet_projs = horizon_subnet_projections[horizon]
        horizon_results.append(
            HorizonProjectionSchema(
                horizon_days=horizon,
                total_projected_yield_tao=sum(p.projected_yield_tao for p in subnet_projs),
                total_confidence_68_lower=sum(p.confidence_68_lower for p in subnet_projs),
                total_confidence_68_upper=sum(p.confidence_68_upper for p in subnet_projs),
                total_confidence_95_lower=sum(p.confidence_95_lower for p in subnet_projs),
                total_confidence_95_upper=sum(p.confidence_95_upper for p in subnet_projs),
                subnet_projections=subnet_projs,
            )
        )

    total_staked = sum(user_stakes.values())

    response = YieldProjectionResponseSchema(
        projections=horizon_results,
        chart_data=aggregated_chart_data,
        last_computed=datetime.now(UTC).isoformat(),
        total_staked_tao=total_staked,
        subnets_analyzed=subnets_analyzed,
        subnets_skipped=subnets_skipped,
    )

    # Cache the result
    try:
        await cache_set(cache_key, response.model_dump_json(), settings.cache_ttl_prediction)
        log.info(
            "prediction_cached",
            user_id=user_id,
            subnets_analyzed=subnets_analyzed,
            subnets_skipped=subnets_skipped,
            worker="predictions",
        )
    except Exception:
        log.warning("prediction_cache_write_failed", user_id=user_id, exc_info=True)

    return response, False

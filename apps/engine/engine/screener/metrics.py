"""Computed screener metrics — price changes, staking velocity, immunity."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.logging import get_logger
from engine.models.emission_record import EmissionRecord
from engine.models.subnet_snapshot import SubnetSnapshot

log = get_logger(__name__)

# Immunity heuristic: subnets younger than this many days are considered immune
IMMUNITY_THRESHOLD_DAYS = 2


@dataclass
class PriceChanges:
    """Percentage price changes for a subnet's alpha token."""

    change_24h: float | None = None
    change_7d: float | None = None
    change_30d: float | None = None


async def compute_price_changes(
    session: AsyncSession,
    netuids: list[int],
    current_prices: dict[int, float],
    now: datetime | None = None,
) -> dict[int, PriceChanges]:
    """Compute alpha token price percentage changes (24h, 7d, 30d).

    Uses nearest-snapshot lookups from subnet_snapshots to find historical
    prices at each time offset. Returns percentage change relative to current.
    """
    if not netuids:
        return {}

    now = now or datetime.now(UTC)
    offsets = {
        "change_24h": timedelta(hours=24),
        "change_7d": timedelta(days=7),
        "change_30d": timedelta(days=30),
    }

    # For each offset, find the snapshot closest to (now - offset) per netuid
    historical: dict[str, dict[int, float]] = {}
    for label, delta in offsets.items():
        target_time = now - delta
        # Window: look within ±12 hours of the target time for a snapshot
        window_start = target_time - timedelta(hours=12)
        window_end = target_time + timedelta(hours=12)

        query = (
            select(
                SubnetSnapshot.netuid,
                SubnetSnapshot.alpha_price,
            )
            .where(
                SubnetSnapshot.netuid.in_(netuids),
                SubnetSnapshot.time >= window_start,
                SubnetSnapshot.time <= window_end,
            )
            .distinct(SubnetSnapshot.netuid)
            .order_by(
                SubnetSnapshot.netuid,
                # Sort by proximity to target time (closest first)
                func.abs(func.extract("epoch", SubnetSnapshot.time - target_time)),
            )
        )

        result = await session.execute(query)
        historical[label] = {row.netuid: float(row.alpha_price) for row in result}

    # Build PriceChanges per netuid
    changes: dict[int, PriceChanges] = {}
    for netuid in netuids:
        current = current_prices.get(netuid)
        if current is None or current == 0:
            changes[netuid] = PriceChanges()
            continue

        pc = PriceChanges()
        for label in offsets:
            old_price = historical[label].get(netuid)
            if old_price is not None and old_price != 0:
                pct = ((current - old_price) / old_price) * 100
                setattr(pc, label, round(pct, 2))
        changes[netuid] = pc

    return changes


async def compute_net_tao_inflow(
    session: AsyncSession,
    netuids: list[int],
) -> dict[int, float | None]:
    """Get the most recent net_tao_inflow from emission_records per netuid."""
    if not netuids:
        return {}

    # For each netuid, get the most recent emission_record
    query = (
        select(
            EmissionRecord.netuid,
            EmissionRecord.net_tao_inflow,
        )
        .where(EmissionRecord.netuid.in_(netuids))
        .distinct(EmissionRecord.netuid)
        .order_by(EmissionRecord.netuid, EmissionRecord.time.desc())
    )

    result = await session.execute(query)
    inflow_map: dict[int, float | None] = {row.netuid: float(row.net_tao_inflow) for row in result}

    # Return None for netuids not found in emission_records
    return {n: inflow_map.get(n) for n in netuids}


def compute_immunity_status(
    subnet_ages: dict[int, int],
) -> dict[int, bool]:
    """Determine immunity status for each subnet based on age.

    Returns True if immunity is active (subnet is young), False if expired.
    Simple heuristic: subnets younger than IMMUNITY_THRESHOLD_DAYS are immune.
    """
    return {netuid: age < IMMUNITY_THRESHOLD_DAYS for netuid, age in subnet_ages.items()}

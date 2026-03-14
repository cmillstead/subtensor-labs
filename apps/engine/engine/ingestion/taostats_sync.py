"""Taostats historical backfill pipeline — fetches historical data and writes to TimescaleDB."""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.bittensor import get_active_subnet_netuids
from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.ingestion.taostats_client import TaostatsClient
from engine.models.alpha_price import AlphaPrice
from engine.models.emission_record import EmissionRecord
from engine.models.ingestion_cursor import IngestionCursor
from engine.models.subnet_snapshot import SubnetSnapshot

log = get_logger(__name__)

# Default backfill start: 2023-01-01 UTC (earliest reasonable Bittensor data)
_DEFAULT_BACKFILL_START = datetime(2023, 1, 1, tzinfo=UTC)


def _parse_float(value: Any, default: float = 0.0) -> float:
    """Safely parse a numeric value (string or number) to float."""
    if value is None:
        return default
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def _parse_datetime(value: Any) -> datetime | None:
    """Parse an ISO 8601 timestamp string to datetime with UTC timezone."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(str(value))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    except (ValueError, TypeError):
        return None


async def _get_last_backfill_timestamp(session: AsyncSession) -> datetime | None:
    """Get the last successful backfill timestamp from IngestionCursor."""
    result = await session.execute(
        select(IngestionCursor).where(IngestionCursor.source == "taostats_backfill")
    )
    cursor = result.scalar_one_or_none()
    if cursor is None:
        return None
    metadata = cursor.metadata_json or {}
    last_ts = metadata.get("last_timestamp")
    if last_ts:
        return _parse_datetime(last_ts)
    return cursor.last_processed_at


async def _detect_snapshot_gaps(
    session: AsyncSession, netuid: int, since: datetime
) -> list[tuple[datetime, datetime]]:
    """Detect date gaps in subnet_snapshots for a given subnet since a start date.

    Returns list of (gap_start, gap_end) tuples representing missing date ranges.
    Checks for days with no records — gaps > 1 day are reported.
    """
    result = await session.execute(
        select(func.date_trunc("day", SubnetSnapshot.time).label("day"))
        .where(SubnetSnapshot.netuid == netuid)
        .where(SubnetSnapshot.time >= since)
        .distinct()
        .order_by("day")
    )
    existing_days = {row.day.date() for row in result}

    if not existing_days:
        return [(since, datetime.now(UTC))]

    gaps: list[tuple[datetime, datetime]] = []
    current = since.date()
    end = datetime.now(UTC).date()

    gap_start: datetime | None = None
    while current <= end:
        if current not in existing_days:
            if gap_start is None:
                gap_start = datetime(current.year, current.month, current.day, tzinfo=UTC)
        else:
            if gap_start is not None:
                gap_end = datetime(current.year, current.month, current.day, tzinfo=UTC)
                gaps.append((gap_start, gap_end))
                gap_start = None
        current = current + timedelta(days=1)

    if gap_start is not None:
        gaps.append((gap_start, datetime.now(UTC)))

    return gaps


async def backfill_subnet_history(
    client: TaostatsClient,
    netuid: int,
    since: datetime,
    session: AsyncSession,
    *,
    until: datetime | None = None,
) -> int:
    """Fetch historical subnet/metagraph data from Taostats and write to subnet_snapshots.

    Returns number of records written.
    """
    try:
        records = await client.fetch_metagraph_history(subnet_id=netuid, since=since, until=until)
    except Exception:
        log.warning(
            "subnet_history_fetch_failed",
            netuid=netuid,
            exc_info=True,
            worker="taostats_sync",
        )
        return 0

    if not records:
        return 0

    rows: list[dict[str, Any]] = []
    for record in records:
        ts = _parse_datetime(record.get("timestamp"))
        if ts is None:
            continue
        rows.append(
            {
                "time": ts,
                "netuid": netuid,
                "miner_count": int(
                    _parse_float(record.get("miner_count", record.get("neuron_count", 0)))
                ),
                "validator_count": int(_parse_float(record.get("validator_count", 0))),
                "emission_share": _parse_float(
                    record.get("emission", record.get("emission_share", 0))
                ),
                "registration_cost": _parse_float(record.get("registration_cost", 0)),
                "alpha_price": _parse_float(record.get("alpha_price", record.get("price", 0))),
                "alpha_market_cap": _parse_float(
                    record.get("alpha_market_cap", record.get("market_cap", 0))
                ),
                "tao_reserves": _parse_float(
                    record.get("tao_reserves", record.get("tao_reserve", 0))
                ),
                "alpha_reserves": _parse_float(
                    record.get("alpha_reserves", record.get("alpha_reserve", 0))
                ),
                "fill_rate": _parse_float(record.get("fill_rate", 0)),
                "owner_take_rate": _parse_float(
                    record.get("owner_take_rate", record.get("take_rate", 0))
                ),
            }
        )

    if not rows:
        return 0

    stmt = (
        pg_insert(SubnetSnapshot)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["time", "netuid"])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]


async def backfill_emission_history(
    client: TaostatsClient,
    netuid: int,
    since: datetime,
    session: AsyncSession,
    *,
    until: datetime | None = None,
) -> int:
    """Fetch historical emission data from Taostats and write to emission_records.

    Returns number of records written.
    """
    try:
        records = await client.fetch_subnet_emission(subnet_id=netuid, since=since, until=until)
    except Exception:
        log.warning(
            "emission_history_fetch_failed",
            netuid=netuid,
            exc_info=True,
            worker="taostats_sync",
        )
        return 0

    if not records:
        return 0

    rows: list[dict[str, Any]] = []
    for record in records:
        ts = _parse_datetime(record.get("timestamp"))
        if ts is None:
            continue
        rows.append(
            {
                "time": ts,
                "netuid": netuid,
                "emission_tao": _parse_float(record.get("emission_tao", record.get("emission", 0))),
                "emission_share_pct": _parse_float(
                    record.get(
                        "emission_share_pct",
                        record.get("emission_share", record.get("emission_percentage", 0)),
                    )
                ),
                "net_tao_inflow": _parse_float(
                    record.get("net_tao_inflow", record.get("tao_inflow", 0))
                ),
                "cumulative_stake": _parse_float(
                    record.get("cumulative_stake", record.get("total_stake", 0))
                ),
            }
        )

    if not rows:
        return 0

    stmt = (
        pg_insert(EmissionRecord)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["time", "netuid"])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]


async def backfill_price_history(
    client: TaostatsClient,
    since: datetime,
    session: AsyncSession,
    *,
    until: datetime | None = None,
) -> int:
    """Fetch historical TAO price data from Taostats and write to alpha_prices.

    NOTE: Taostats provides TAO/USD price, not per-subnet alpha token prices.
    Alpha price history may not be available pre-dTAO. We store TAO price data
    as netuid=0 (network-level) for portfolio value calculations.

    Returns number of records written.
    """
    try:
        records = await client.fetch_price_history(since=since, until=until)
    except Exception:
        log.warning(
            "price_history_fetch_failed",
            exc_info=True,
            worker="taostats_sync",
        )
        return 0

    if not records:
        return 0

    rows: list[dict[str, Any]] = []
    for record in records:
        ts = _parse_datetime(
            record.get("last_updated", record.get("timestamp", record.get("created_at")))
        )
        if ts is None:
            continue
        price = _parse_float(record.get("price", 0))
        rows.append(
            {
                "time": ts,
                "netuid": 0,  # Network-level TAO price, not subnet-specific
                "price_tao": price,
                "tao_reserve": 0.0,  # Not applicable for TAO/USD price
                "alpha_reserve": 0.0,
                "volume_24h": _parse_float(record.get("volume_24h")),
            }
        )

    if not rows:
        return 0

    stmt = (
        pg_insert(AlphaPrice).values(rows).on_conflict_do_nothing(index_elements=["time", "netuid"])
    )
    result = await session.execute(stmt)
    await session.commit()
    return result.rowcount or 0  # type: ignore[attr-defined]


async def _backfill_single_subnet(
    client: TaostatsClient,
    netuid: int,
    since: datetime,
    *,
    until: datetime | None = None,
) -> tuple[int, int]:
    """Backfill all data for a single subnet. Returns (records_written, errors)."""
    start = time.monotonic()
    total_records = 0
    errors = 0

    factory = get_session_factory()
    async with factory() as session:
        # Detect gaps and backfill only missing ranges
        gaps = await _detect_snapshot_gaps(session, netuid, since)
        if not gaps:
            log.info(
                "subnet_backfill_skipped_no_gaps",
                netuid=netuid,
                worker="taostats_sync",
            )
            return 0, 0

        for gap_start, gap_end in gaps:
            effective_until = until if until and until < gap_end else gap_end

            # Subnet snapshots (metagraph history)
            try:
                count = await backfill_subnet_history(
                    client, netuid, gap_start, session, until=effective_until
                )
                total_records += count
            except Exception:
                log.warning(
                    "subnet_snapshot_backfill_failed",
                    netuid=netuid,
                    exc_info=True,
                    worker="taostats_sync",
                )
                errors += 1

            # Emission history
            try:
                count = await backfill_emission_history(
                    client, netuid, gap_start, session, until=effective_until
                )
                total_records += count
            except Exception:
                log.warning(
                    "emission_backfill_failed",
                    netuid=netuid,
                    exc_info=True,
                    worker="taostats_sync",
                )
                errors += 1

    elapsed_s = round(time.monotonic() - start, 2)
    log.info(
        "subnet_backfill_completed",
        netuid=netuid,
        records_written=total_records,
        errors=errors,
        duration_s=elapsed_s,
        worker="taostats_sync",
    )
    return total_records, errors


async def run_taostats_backfill(
    *,
    subnet_filter: int | None = None,
    since_override: datetime | None = None,
    until_override: datetime | None = None,
) -> None:
    """Run a full Taostats historical backfill cycle.

    Args:
        subnet_filter: If set, only backfill this specific subnet.
        since_override: Override the start date (for manual backfill).
        until_override: Override the end date (for manual backfill).
    """
    cycle_start = time.monotonic()
    log.info("taostats_backfill_started", worker="taostats_sync")

    # Determine backfill start date
    since = since_override
    if since is None:
        try:
            factory = get_session_factory()
            async with factory() as session:
                since = await _get_last_backfill_timestamp(session)
        except Exception:
            log.warning("backfill_cursor_read_failed", exc_info=True, worker="taostats_sync")

    if since is None:
        since = _DEFAULT_BACKFILL_START

    # Discover subnets
    if subnet_filter is not None:
        netuids = [subnet_filter]
    else:
        try:
            netuids = await get_active_subnet_netuids()
        except Exception:
            log.error("backfill_subnet_discovery_failed", exc_info=True, worker="taostats_sync")
            return

    client = TaostatsClient()
    semaphore = asyncio.Semaphore(settings.taostats_backfill_workers)
    total_records = 0
    subnets_backfilled = 0
    subnets_failed = 0

    backfill_since = since  # Guaranteed non-None by this point

    async def _backfill_with_semaphore(netuid: int) -> tuple[int, int]:
        async with semaphore:
            return await _backfill_single_subnet(
                client,
                netuid,
                backfill_since,
                until=until_override,
            )

    results = await asyncio.gather(
        *[_backfill_with_semaphore(netuid) for netuid in netuids],
        return_exceptions=True,
    )

    for result in results:
        if isinstance(result, tuple):
            records, errors = result
            total_records += records
            if errors > 0:
                subnets_failed += 1
            else:
                subnets_backfilled += 1
        else:
            subnets_failed += 1

    # Backfill TAO price history (once, not per-subnet)
    try:
        factory = get_session_factory()
        async with factory() as session:
            price_count = await backfill_price_history(client, since, session, until=until_override)
            total_records += price_count
    except Exception:
        log.warning("tao_price_backfill_failed", exc_info=True, worker="taostats_sync")

    await client.close()

    # Update ingestion cursor
    try:
        now = datetime.now(UTC)
        factory = get_session_factory()
        async with factory() as session:
            stmt = (
                pg_insert(IngestionCursor)
                .values(
                    source="taostats_backfill",
                    last_processed_at=now,
                    metadata_json={
                        "subnets_backfilled": subnets_backfilled,
                        "subnets_failed": subnets_failed,
                        "total_records_written": total_records,
                        "last_timestamp": now.isoformat(),
                    },
                )
                .on_conflict_do_update(
                    index_elements=["source"],
                    set_={
                        "last_processed_at": now,
                        "metadata_json": {
                            "subnets_backfilled": subnets_backfilled,
                            "subnets_failed": subnets_failed,
                            "total_records_written": total_records,
                            "last_timestamp": now.isoformat(),
                        },
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
    except Exception:
        log.warning("backfill_cursor_update_failed", exc_info=True, worker="taostats_sync")

    cycle_duration_s = round(time.monotonic() - cycle_start, 2)
    log.info(
        "taostats_backfill_completed",
        subnets_backfilled=subnets_backfilled,
        subnets_failed=subnets_failed,
        total_records=total_records,
        duration_s=cycle_duration_s,
        worker="taostats_sync",
    )

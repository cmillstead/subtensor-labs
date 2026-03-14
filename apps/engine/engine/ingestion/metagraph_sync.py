"""Metagraph sync pipeline — per-subnet metagraph data ingestion."""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.bittensor import get_active_subnet_netuids, sync_subnet_metagraph
from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.ingestion_cursor import IngestionCursor
from engine.models.metagraph_entry import MetagraphEntry
from engine.models.subnet_snapshot import SubnetSnapshot

log = get_logger(__name__)

# Per-subnet sync timeout (30s gives margin over 10s NFR5 target)
_SUBNET_SYNC_TIMEOUT_S = 30


def _extract_subnet_snapshot(
    netuid: int,
    metagraph: Any,
    now: datetime,
    price_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract subnet-level metrics from metagraph into a SubnetSnapshot dict.

    If price_data is provided (from Redis price cache), populates price-related
    fields. Otherwise defaults to 0.0.
    """
    active_list = (
        metagraph.active.tolist() if hasattr(metagraph.active, "tolist") else list(metagraph.active)
    )
    stake_list = (
        metagraph.stake.tolist() if hasattr(metagraph.stake, "tolist") else list(metagraph.stake)
    )

    miner_count = sum(1 for a in active_list if a)
    # Validators: neurons with stake > 0 (heuristic)
    validator_count = sum(1 for s in stake_list if s > 0)

    alpha_price = 0.0
    alpha_market_cap = 0.0
    tao_reserves = 0.0
    alpha_reserves = 0.0
    if price_data:
        alpha_price = float(price_data.get("price_tao", 0.0))
        alpha_market_cap = float(price_data.get("alpha_market_cap", 0.0))
        tao_reserves = float(price_data.get("tao_reserve", 0.0))
        alpha_reserves = float(price_data.get("alpha_reserve", 0.0))

    return {
        "time": now,
        "netuid": netuid,
        "miner_count": miner_count,
        "validator_count": validator_count,
        "emission_share": 0.0,
        "registration_cost": 0.0,
        "alpha_price": alpha_price,
        "alpha_market_cap": alpha_market_cap,
        "tao_reserves": tao_reserves,
        "alpha_reserves": alpha_reserves,
        "fill_rate": 0.0,
        "owner_take_rate": 0.0,
    }


def _extract_metagraph_entries(netuid: int, metagraph: Any, now: datetime) -> list[dict[str, Any]]:
    """Extract per-neuron data from metagraph into MetagraphEntry dicts."""
    n = metagraph.n.item() if hasattr(metagraph.n, "item") else int(metagraph.n)
    hotkeys = metagraph.hotkeys
    coldkeys = metagraph.coldkeys
    stake = (
        metagraph.stake.tolist() if hasattr(metagraph.stake, "tolist") else list(metagraph.stake)
    )
    incentive = (
        metagraph.incentive.tolist()
        if hasattr(metagraph.incentive, "tolist")
        else list(metagraph.incentive)
    )
    trust = (
        metagraph.trust.tolist() if hasattr(metagraph.trust, "tolist") else list(metagraph.trust)
    )
    dividends = (
        metagraph.dividends.tolist()
        if hasattr(metagraph.dividends, "tolist")
        else list(metagraph.dividends)
    )
    active = (
        metagraph.active.tolist() if hasattr(metagraph.active, "tolist") else list(metagraph.active)
    )

    return [
        {
            "time": now,
            "netuid": netuid,
            "uid": uid,
            "hotkey": hotkeys[uid],
            "coldkey": coldkeys[uid],
            "stake": float(stake[uid]),
            "incentive": float(incentive[uid]),
            "trust": float(trust[uid]),
            "dividends": float(dividends[uid]),
            "is_active": bool(active[uid]),
        }
        for uid in range(n)
    ]


def _serialize_metagraph_cache(netuid: int, metagraph: Any, now: datetime) -> str:
    """Serialize metagraph state for Redis cache."""
    block = metagraph.block.item() if hasattr(metagraph.block, "item") else int(metagraph.block)
    return json.dumps(
        {
            "netuid": netuid,
            "n": metagraph.n.item() if hasattr(metagraph.n, "item") else int(metagraph.n),
            "block": block,
            "uids": metagraph.uids.tolist()
            if hasattr(metagraph.uids, "tolist")
            else list(metagraph.uids),
            "hotkeys": list(metagraph.hotkeys),
            "coldkeys": list(metagraph.coldkeys),
            "stake": metagraph.stake.tolist()
            if hasattr(metagraph.stake, "tolist")
            else list(metagraph.stake),
            "incentive": metagraph.incentive.tolist()
            if hasattr(metagraph.incentive, "tolist")
            else list(metagraph.incentive),
            "trust": metagraph.trust.tolist()
            if hasattr(metagraph.trust, "tolist")
            else list(metagraph.trust),
            "dividends": metagraph.dividends.tolist()
            if hasattr(metagraph.dividends, "tolist")
            else list(metagraph.dividends),
            "active": metagraph.active.tolist()
            if hasattr(metagraph.active, "tolist")
            else list(metagraph.active),
            "synced_at": now.isoformat(),
        }
    )


async def sync_single_subnet(netuid: int, session: AsyncSession) -> None:
    """Sync metagraph for a single subnet: SDK → DB → Redis."""
    start = time.monotonic()
    now = datetime.now(UTC)

    metagraph = await asyncio.wait_for(
        sync_subnet_metagraph(netuid),
        timeout=_SUBNET_SYNC_TIMEOUT_S,
    )

    # Read price data from cache (populated by price_tracker)
    price_data: dict[str, Any] | None = None
    try:
        cached_price = await cache_get(f"price:{netuid}")
        if cached_price:
            price_data = json.loads(cached_price)
    except Exception:
        log.debug("price_cache_read_failed", netuid=netuid, worker="metagraph_sync")

    # Write SubnetSnapshot
    snapshot = _extract_subnet_snapshot(netuid, metagraph, now, price_data=price_data)
    await session.execute(insert(SubnetSnapshot).values(snapshot))

    # Bulk write MetagraphEntry rows
    entries = _extract_metagraph_entries(netuid, metagraph, now)
    if entries:
        await session.execute(insert(MetagraphEntry), entries)

    await session.commit()

    # Update Redis cache
    cache_data = _serialize_metagraph_cache(netuid, metagraph, now)
    await cache_set(f"metagraph:{netuid}", cache_data, ttl=settings.cache_ttl_metagraph)

    # Track per-subnet sync timestamp for health staleness reporting
    await cache_set(f"metagraph_sync_ts:{netuid}", now.isoformat(), ttl=600)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    log.info(
        "subnet_sync_completed",
        netuid=netuid,
        neurons=len(entries),
        duration_ms=elapsed_ms,
        worker="metagraph_sync",
    )


async def run_metagraph_sync_cycle() -> None:
    """Run a full metagraph sync cycle across all active subnets."""
    cycle_start = time.monotonic()
    log.info("metagraph_sync_started", worker="metagraph_sync")

    try:
        netuids = await get_active_subnet_netuids()
    except Exception:
        log.error("metagraph_sync_subnet_discovery_failed", exc_info=True, worker="metagraph_sync")
        return

    semaphore = asyncio.Semaphore(settings.metagraph_sync_workers)
    subnets_synced = 0
    subnets_failed = 0

    async def _sync_with_semaphore(netuid: int) -> bool:
        async with semaphore:
            factory = get_session_factory()
            async with factory() as session:
                try:
                    await sync_single_subnet(netuid, session)
                    return True
                except Exception:
                    log.warning(
                        "subnet_sync_failed",
                        netuid=netuid,
                        exc_info=True,
                        worker="metagraph_sync",
                    )
                    return False

    results = await asyncio.gather(
        *[_sync_with_semaphore(netuid) for netuid in netuids],
        return_exceptions=True,
    )

    for result in results:
        if result is True:
            subnets_synced += 1
        else:
            subnets_failed += 1

    # Update ingestion cursor
    try:
        factory = get_session_factory()
        async with factory() as session:
            now = datetime.now(UTC)
            stmt = (
                pg_insert(IngestionCursor)
                .values(
                    source="metagraph_sync",
                    last_processed_at=now,
                    metadata_json={
                        "subnets_synced": subnets_synced,
                        "subnets_failed": subnets_failed,
                        "total_subnets": len(netuids),
                    },
                )
                .on_conflict_do_update(
                    index_elements=["source"],
                    set_={
                        "last_processed_at": now,
                        "metadata_json": {
                            "subnets_synced": subnets_synced,
                            "subnets_failed": subnets_failed,
                            "total_subnets": len(netuids),
                        },
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
    except Exception:
        log.warning("ingestion_cursor_update_failed", exc_info=True, worker="metagraph_sync")

    cycle_duration_s = round(time.monotonic() - cycle_start, 2)

    if subnets_failed == len(netuids) and len(netuids) > 0:
        log.error(
            "metagraph_sync_cycle_all_failed",
            subnets_synced=subnets_synced,
            subnets_failed=subnets_failed,
            duration_s=cycle_duration_s,
            worker="metagraph_sync",
        )
    else:
        log.info(
            "metagraph_sync_cycle_completed",
            subnets_synced=subnets_synced,
            subnets_failed=subnets_failed,
            duration_s=cycle_duration_s,
            worker="metagraph_sync",
        )

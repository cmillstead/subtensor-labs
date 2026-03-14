"""Alpha token price sync pipeline — on-chain AMM reserve queries."""

import asyncio
import json
import time
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import insert
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.bittensor import get_active_subnet_netuids, get_subnet_hyperparams
from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_set
from engine.models.alpha_price import AlphaPrice
from engine.models.ingestion_cursor import IngestionCursor

log = get_logger(__name__)


def _extract_reserves(hyperparams: Any) -> tuple[float, float]:
    """Extract TAO and alpha reserves from subnet hyperparameters.

    Returns (tao_reserve, alpha_reserve). Raises ValueError if reserves
    cannot be extracted or alpha_reserve is zero.
    """
    # Bittensor SDK SubnetHyperparams exposes pool reserves.
    # Try common attribute names for TAO/alpha reserves.
    tao_reserve: float = 0.0
    alpha_reserve: float = 0.0

    if hasattr(hyperparams, "tao_in"):
        tao_reserve = float(hyperparams.tao_in)
    elif hasattr(hyperparams, "tao_reserve"):
        tao_reserve = float(hyperparams.tao_reserve)
    elif hasattr(hyperparams, "pool_tao"):
        tao_reserve = float(hyperparams.pool_tao)

    if hasattr(hyperparams, "alpha_out"):
        alpha_reserve = float(hyperparams.alpha_out)
    elif hasattr(hyperparams, "alpha_reserve"):
        alpha_reserve = float(hyperparams.alpha_reserve)
    elif hasattr(hyperparams, "pool_alpha"):
        alpha_reserve = float(hyperparams.pool_alpha)

    if tao_reserve == 0.0:
        raise ValueError("tao_reserve is zero — cannot compute price")

    if alpha_reserve == 0.0:
        raise ValueError("alpha_reserve is zero — cannot compute price")

    return tao_reserve, alpha_reserve


def _compute_price(tao_reserve: float, alpha_reserve: float) -> float:
    """Compute alpha token price in TAO from AMM reserves (constant product)."""
    return tao_reserve / alpha_reserve


def _compute_market_cap(price_tao: float, alpha_reserve: float) -> float:
    """Compute alpha token market cap (price * outstanding supply)."""
    return price_tao * alpha_reserve


def _serialize_price_cache(
    netuid: int,
    price_tao: float,
    tao_reserve: float,
    alpha_reserve: float,
    alpha_market_cap: float,
    now: datetime,
) -> str:
    """Serialize price data for Redis cache."""
    return json.dumps(
        {
            "netuid": netuid,
            "price_tao": price_tao,
            "tao_reserve": tao_reserve,
            "alpha_reserve": alpha_reserve,
            "alpha_market_cap": alpha_market_cap,
            "synced_at": now.isoformat(),
        }
    )


async def sync_single_subnet_price(netuid: int, session: AsyncSession) -> None:
    """Sync alpha token price for a single subnet: SDK → DB → Redis."""
    start = time.monotonic()
    now = datetime.now(UTC)

    hyperparams = await asyncio.wait_for(
        get_subnet_hyperparams(netuid),
        timeout=settings.price_sync_timeout_seconds,
    )

    tao_reserve, alpha_reserve = _extract_reserves(hyperparams)
    price_tao = _compute_price(tao_reserve, alpha_reserve)
    alpha_market_cap = _compute_market_cap(price_tao, alpha_reserve)

    # Write AlphaPrice row
    await session.execute(
        insert(AlphaPrice).values(
            {
                "time": now,
                "netuid": netuid,
                "price_tao": price_tao,
                "tao_reserve": tao_reserve,
                "alpha_reserve": alpha_reserve,
                "volume_24h": None,
            }
        )
    )
    await session.commit()

    # Update Redis cache
    cache_data = _serialize_price_cache(
        netuid, price_tao, tao_reserve, alpha_reserve, alpha_market_cap, now
    )
    await cache_set(f"price:{netuid}", cache_data, ttl=settings.cache_ttl_price)

    # Track per-subnet price sync timestamp for health staleness
    await cache_set(f"price_sync_ts:{netuid}", now.isoformat(), ttl=600)

    elapsed_ms = int((time.monotonic() - start) * 1000)
    log.info(
        "subnet_price_synced",
        netuid=netuid,
        price_tao=round(price_tao, 8),
        tao_reserve=round(tao_reserve, 4),
        alpha_reserve=round(alpha_reserve, 4),
        duration_ms=elapsed_ms,
        worker="price_tracker",
    )


async def run_price_sync_cycle() -> None:
    """Run a full price sync cycle across all active subnets."""
    cycle_start = time.monotonic()
    log.info("price_sync_started", worker="price_tracker")

    try:
        netuids = await get_active_subnet_netuids()
    except Exception:
        log.error("price_sync_subnet_discovery_failed", exc_info=True, worker="price_tracker")
        return

    semaphore = asyncio.Semaphore(settings.price_sync_workers)
    subnets_priced = 0
    subnets_failed = 0

    async def _sync_with_semaphore(netuid: int) -> bool:
        async with semaphore:
            factory = get_session_factory()
            async with factory() as session:
                try:
                    await sync_single_subnet_price(netuid, session)
                    return True
                except Exception:
                    log.warning(
                        "subnet_price_failed",
                        netuid=netuid,
                        exc_info=True,
                        worker="price_tracker",
                    )
                    return False

    results = await asyncio.gather(
        *[_sync_with_semaphore(netuid) for netuid in netuids],
        return_exceptions=True,
    )

    for result in results:
        if result is True:
            subnets_priced += 1
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
                    source="price_sync",
                    last_processed_at=now,
                    metadata_json={
                        "subnets_priced": subnets_priced,
                        "subnets_failed": subnets_failed,
                        "total_subnets": len(netuids),
                    },
                )
                .on_conflict_do_update(
                    index_elements=["source"],
                    set_={
                        "last_processed_at": now,
                        "metadata_json": {
                            "subnets_priced": subnets_priced,
                            "subnets_failed": subnets_failed,
                            "total_subnets": len(netuids),
                        },
                    },
                )
            )
            await session.execute(stmt)
            await session.commit()
    except Exception:
        log.warning("ingestion_cursor_update_failed", exc_info=True, worker="price_tracker")

    cycle_duration_s = round(time.monotonic() - cycle_start, 2)

    if subnets_failed == len(netuids) and len(netuids) > 0:
        log.error(
            "price_sync_cycle_all_failed",
            subnets_priced=subnets_priced,
            subnets_failed=subnets_failed,
            duration_s=cycle_duration_s,
            worker="price_tracker",
        )
    else:
        log.info(
            "price_sync_cycle_completed",
            subnets_priced=subnets_priced,
            subnets_failed=subnets_failed,
            duration_s=cycle_duration_s,
            worker="price_tracker",
        )

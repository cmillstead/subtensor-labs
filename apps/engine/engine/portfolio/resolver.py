"""Coldkey → hotkeys → positions resolution via DB and chain fallback."""

import asyncio
from typing import Any

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from engine.core.bittensor import get_active_subnet_netuids, sync_subnet_metagraph
from engine.core.database import get_session_factory
from engine.core.logging import get_logger, truncate_address
from engine.models.alpha_price import AlphaPrice
from engine.models.metagraph_entry import MetagraphEntry
from engine.portfolio.positions import compute_position_details, compute_totals
from engine.schemas.portfolio import ColdkeyPortfolioSchema

log = get_logger(__name__)


async def _get_latest_prices(session: AsyncSession) -> dict[int, float]:
    """Get the latest alpha price per netuid from the database."""
    latest_price_subq = (
        select(AlphaPrice.netuid, func.max(AlphaPrice.time).label("max_time"))
        .group_by(AlphaPrice.netuid)
        .subquery()
    )
    result = await session.execute(
        select(AlphaPrice).join(
            latest_price_subq,
            and_(
                AlphaPrice.netuid == latest_price_subq.c.netuid,
                AlphaPrice.time == latest_price_subq.c.max_time,
            ),
        )
    )
    prices: dict[int, float] = {}
    for row in result.scalars().all():
        prices[row.netuid] = row.price_tao
    return prices


async def _query_db_positions(coldkey: str, session: AsyncSession) -> list[dict[str, Any]]:
    """Query latest metagraph entries for a coldkey across all subnets.

    Uses ix_metagraph_entries_coldkey index for efficient lookup.
    """
    latest_time_subq = (
        select(
            MetagraphEntry.netuid,
            func.max(MetagraphEntry.time).label("max_time"),
        )
        .where(MetagraphEntry.coldkey == coldkey)
        .group_by(MetagraphEntry.netuid)
        .subquery()
    )
    result = await session.execute(
        select(MetagraphEntry).join(
            latest_time_subq,
            and_(
                MetagraphEntry.netuid == latest_time_subq.c.netuid,
                MetagraphEntry.time == latest_time_subq.c.max_time,
                MetagraphEntry.coldkey == coldkey,
            ),
        )
    )
    entries: list[dict[str, Any]] = []
    for row in result.scalars().all():
        entries.append(
            {
                "netuid": row.netuid,
                "uid": row.uid,
                "hotkey": row.hotkey,
                "coldkey": row.coldkey,
                "stake": row.stake,
                "incentive": row.incentive,
                "trust": row.trust,
                "dividends": row.dividends,
                "is_active": row.is_active,
                "emission_share": 0.0,  # Not stored per-neuron in metagraph_entries
            }
        )
    return entries


async def _query_chain_positions(coldkey: str) -> list[dict[str, Any]]:
    """Fallback: query chain via SDK for coldkey's positions across all subnets.

    Used when no DB entries exist for this coldkey (never synced).
    Uses asyncio.gather with a semaphore for concurrent subnet queries.
    """
    log.warning(
        "chain_fallback_started",
        coldkey=truncate_address(coldkey),
        worker="portfolio",
    )
    try:
        netuids = await get_active_subnet_netuids()
    except Exception:
        log.error(
            "chain_fallback_subnet_discovery_failed",
            coldkey=truncate_address(coldkey),
            exc_info=True,
            worker="portfolio",
        )
        return []

    # Limit concurrency to avoid overwhelming the chain RPC
    semaphore = asyncio.Semaphore(8)

    async def _scan_subnet(netuid: int) -> list[dict[str, Any]]:
        async with semaphore:
            try:
                metagraph = await sync_subnet_metagraph(netuid)
            except Exception:
                log.warning(
                    "chain_fallback_subnet_failed",
                    netuid=netuid,
                    coldkey=truncate_address(coldkey),
                    exc_info=True,
                    worker="portfolio",
                )
                return []

            n = metagraph.n.item() if hasattr(metagraph.n, "item") else int(metagraph.n)
            ck_list = metagraph.coldkeys
            hk_list = metagraph.hotkeys
            stake = (
                metagraph.stake.tolist()
                if hasattr(metagraph.stake, "tolist")
                else list(metagraph.stake)
            )
            incentive = (
                metagraph.incentive.tolist()
                if hasattr(metagraph.incentive, "tolist")
                else list(metagraph.incentive)
            )
            trust = (
                metagraph.trust.tolist()
                if hasattr(metagraph.trust, "tolist")
                else list(metagraph.trust)
            )
            dividends = (
                metagraph.dividends.tolist()
                if hasattr(metagraph.dividends, "tolist")
                else list(metagraph.dividends)
            )
            active = (
                metagraph.active.tolist()
                if hasattr(metagraph.active, "tolist")
                else list(metagraph.active)
            )

            found: list[dict[str, Any]] = []
            for uid in range(n):
                if ck_list[uid] == coldkey:
                    found.append(
                        {
                            "netuid": netuid,
                            "uid": uid,
                            "hotkey": hk_list[uid],
                            "coldkey": ck_list[uid],
                            "stake": float(stake[uid]),
                            "incentive": float(incentive[uid]),
                            "trust": float(trust[uid]),
                            "dividends": float(dividends[uid]),
                            "is_active": bool(active[uid]),
                            "emission_share": 0.0,
                        }
                    )
            return found

    results = await asyncio.gather(
        *[_scan_subnet(netuid) for netuid in netuids],
        return_exceptions=True,
    )

    entries: list[dict[str, Any]] = []
    for result in results:
        if isinstance(result, list):
            entries.extend(result)

    log.info(
        "chain_fallback_completed",
        coldkey=truncate_address(coldkey),
        positions_found=len(entries),
        worker="portfolio",
    )
    return entries


async def resolve_coldkey_positions(coldkey: str) -> ColdkeyPortfolioSchema:
    """Resolve a coldkey address into a complete portfolio position.

    Strategy:
      1. Query DB for latest metagraph entries matching this coldkey
      2. If no DB entries, fall back to chain query via SDK
      3. Join with latest alpha prices for value computation
      4. Return empty positions (not error) if coldkey has no activity
    """
    factory = get_session_factory()
    async with factory() as session:
        # Step 1: Try DB first
        entries = await _query_db_positions(coldkey, session)

        # Step 2: Chain fallback if DB has no data
        if not entries:
            entries = await _query_chain_positions(coldkey)

        # Step 3: Get prices for value computation
        prices = await _get_latest_prices(session)

    # Step 4: Compute positions
    positions = compute_position_details(entries, prices)
    total_staked, total_alpha, total_value = compute_totals(positions)

    # Deduplicate subnets for count
    unique_netuids = {p.netuid for p in positions}

    log.info(
        "coldkey_resolved",
        coldkey=truncate_address(coldkey),
        positions=len(positions),
        subnets=len(unique_netuids),
        total_value_tao=round(total_value, 4),
        worker="portfolio",
    )

    return ColdkeyPortfolioSchema(
        coldkey=coldkey,
        total_value_tao=total_value,
        total_staked_tao=total_staked,
        total_alpha_value_tao=total_alpha,
        positions=positions,
        subnets_exposed=len(unique_netuids),
    )

"""Multi-address portfolio assembly with Redis caching and deduplication."""

import time
from datetime import UTC, datetime

from engine.core.config import settings
from engine.core.logging import get_logger, truncate_address
from engine.core.redis import cache_get, cache_set
from engine.portfolio.resolver import resolve_coldkey_positions
from engine.schemas.portfolio import (
    ColdkeyPortfolioSchema,
    PortfolioResponseSchema,
    SubnetPositionSchema,
)

log = get_logger(__name__)


def _serialize_coldkey_portfolio(portfolio: ColdkeyPortfolioSchema) -> str:
    """Serialize a coldkey portfolio to JSON for Redis caching."""
    return portfolio.model_dump_json()


def _deserialize_coldkey_portfolio(data: str) -> ColdkeyPortfolioSchema:
    """Deserialize a coldkey portfolio from Redis JSON cache."""
    return ColdkeyPortfolioSchema.model_validate_json(data)


def _merge_positions(
    per_coldkey_results: list[ColdkeyPortfolioSchema],
) -> list[SubnetPositionSchema]:
    """Merge positions from multiple coldkeys and deduplicate by hotkey.

    When the same hotkey appears under multiple coldkeys (e.g., user owns
    multiple coldkeys but delegates to the same validator), keep only the
    first occurrence to avoid double-counting. Delegation lists are merged
    for positions in the same subnet.
    """
    seen_hotkeys: set[str] = set()
    # Track per-subnet: (index in merged list, set of seen validator hotkeys)
    netuid_index: dict[int, int] = {}
    netuid_validators: dict[int, set[str]] = {}
    merged: list[SubnetPositionSchema] = []

    for result in per_coldkey_results:
        for pos in result.positions:
            key = f"{pos.netuid}:{pos.hotkey}"
            if key not in seen_hotkeys:
                seen_hotkeys.add(key)
                merged.append(pos)

                # Aggregate delegations per subnet
                if pos.netuid in netuid_index:
                    idx = netuid_index[pos.netuid]
                    existing = merged[idx]
                    seen_vals = netuid_validators[pos.netuid]

                    new_delegations = [
                        d for d in pos.delegations if d.validator_hotkey not in seen_vals
                    ]
                    if new_delegations:
                        for d in new_delegations:
                            seen_vals.add(d.validator_hotkey)
                        combined = list(existing.delegations) + new_delegations
                        merged[idx] = existing.model_copy(update={"delegations": combined})
                    # Clear delegations from the appended position to avoid double-counting
                    merged[-1] = merged[-1].model_copy(update={"delegations": []})
                else:
                    netuid_index[pos.netuid] = len(merged) - 1
                    netuid_validators[pos.netuid] = {d.validator_hotkey for d in pos.delegations}

    return merged


async def aggregate_portfolio(
    coldkey_addresses: list[str],
) -> tuple[PortfolioResponseSchema, bool]:
    """Aggregate portfolio across one or more coldkey addresses.

    Returns:
        Tuple of (PortfolioResponseSchema, cache_hit) where cache_hit is True
        if ALL coldkeys were served from cache.
    """
    start = time.monotonic()
    per_coldkey_results: list[ColdkeyPortfolioSchema] = []
    all_cache_hit = True

    for coldkey in coldkey_addresses:
        cache_key = f"portfolio:{coldkey}"

        # Step 1: Check Redis cache
        try:
            cached = await cache_get(cache_key)
        except Exception:
            log.warning(
                "portfolio_cache_read_failed",
                coldkey=truncate_address(coldkey),
                exc_info=True,
                worker="portfolio",
            )
            cached = None

        if cached is not None:
            try:
                result = _deserialize_coldkey_portfolio(cached)
                per_coldkey_results.append(result)
                log.info(
                    "portfolio_cache_hit",
                    coldkey=truncate_address(coldkey),
                    worker="portfolio",
                )
                continue
            except Exception:
                log.warning(
                    "portfolio_cache_deserialize_failed",
                    coldkey=truncate_address(coldkey),
                    exc_info=True,
                    worker="portfolio",
                )

        # Step 2: Cache miss — resolve from DB/chain
        all_cache_hit = False
        result = await resolve_coldkey_positions(coldkey)
        per_coldkey_results.append(result)

        # Step 3: Cache the result
        try:
            serialized = _serialize_coldkey_portfolio(result)
            await cache_set(cache_key, serialized, settings.cache_ttl_portfolio)
        except Exception:
            log.warning(
                "portfolio_cache_write_failed",
                coldkey=truncate_address(coldkey),
                exc_info=True,
                worker="portfolio",
            )

    # Step 4: Merge and deduplicate across coldkeys
    merged_positions = _merge_positions(per_coldkey_results)

    total_staked = sum(p.staked_tao for p in merged_positions)
    total_alpha = sum(p.alpha_value_tao for p in merged_positions)
    total_value = total_staked + total_alpha
    unique_netuids = {p.netuid for p in merged_positions}

    elapsed_ms = int((time.monotonic() - start) * 1000)

    log.info(
        "portfolio_aggregated",
        coldkeys=len(coldkey_addresses),
        positions=len(merged_positions),
        subnets=len(unique_netuids),
        total_value_tao=round(total_value, 4),
        cache_hit=all_cache_hit,
        duration_ms=elapsed_ms,
        worker="portfolio",
    )

    response = PortfolioResponseSchema(
        total_value_tao=total_value,
        total_staked_tao=total_staked,
        total_alpha_value_tao=total_alpha,
        positions=merged_positions,
        subnets_exposed=len(unique_netuids),
        coldkeys_resolved=len(coldkey_addresses),
        last_updated=datetime.now(UTC).isoformat(),
    )
    return response, all_cache_hit

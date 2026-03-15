"""Screener query engine — cache-first reads from subnet_snapshots."""

import json
from datetime import UTC, datetime

from sqlalchemy import func, select, text

from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.subnet_snapshot import SubnetSnapshot
from engine.schemas.screener import ScreenerResponseSchema, ScreenerSubnetSchema

log = get_logger(__name__)

CACHE_KEY = "screener:all"

# Keep in sync with packages/shared/constants.ts SUBNET_NAMES
SUBNET_NAMES: dict[int, str] = {
    0: "Root",
    1: "Text Prompting",
    2: "Machine Translation",
    3: "Data Scraping",
    4: "Multi Modality",
    5: "Image Generation",
    8: "Taoshi",
    9: "Pretraining",
    13: "Dataverse",
    18: "Cortex.t",
    19: "Vision",
    21: "FileTAO",
    22: "Datura",
    27: "Compute",
    32: "It's AI",
    34: "BitMind",
}


async def get_all_subnets() -> tuple[ScreenerResponseSchema, bool]:
    """Fetch all subnet data for the screener table.

    Returns (response, cache_hit).
    """
    cached = await cache_get(CACHE_KEY)
    if cached is not None:
        data = json.loads(cached)
        return ScreenerResponseSchema(**data), True

    result = await _query_subnets()

    await cache_set(CACHE_KEY, result.model_dump_json(), settings.cache_ttl_screener)

    return result, False


async def _query_subnets() -> ScreenerResponseSchema:
    """Query TimescaleDB for latest subnet snapshots and 7-day sparklines."""
    factory = get_session_factory()
    async with factory() as session:
        # Latest snapshot per netuid
        latest_subquery = (
            select(
                SubnetSnapshot.netuid,
                func.max(SubnetSnapshot.time).label("max_time"),
            )
            .group_by(SubnetSnapshot.netuid)
            .subquery()
        )

        latest_query = select(SubnetSnapshot).join(
            latest_subquery,
            (SubnetSnapshot.netuid == latest_subquery.c.netuid)
            & (SubnetSnapshot.time == latest_subquery.c.max_time),
        )

        latest_result = await session.execute(latest_query)
        latest_snapshots = latest_result.scalars().all()

        # Earliest snapshot per netuid (for subnet age)
        age_query = select(
            SubnetSnapshot.netuid,
            func.min(SubnetSnapshot.time).label("first_seen"),
        ).group_by(SubnetSnapshot.netuid)

        age_result = await session.execute(age_query)
        first_seen_map: dict[int, datetime] = {row.netuid: row.first_seen for row in age_result}

        # 7-day sparkline data (daily averages)
        sparkline_query = text("""
            SELECT netuid,
                   date_trunc('day', time) AS day,
                   AVG(emission_share) AS avg_emission,
                   AVG(alpha_price) AS avg_price
            FROM subnet_snapshots
            WHERE time >= NOW() - INTERVAL '7 days'
            GROUP BY netuid, date_trunc('day', time)
            ORDER BY netuid, day
        """)

        sparkline_result = await session.execute(sparkline_query)
        sparkline_rows = sparkline_result.fetchall()

        # Build sparkline maps: netuid -> list of daily values
        emission_sparklines: dict[int, list[float]] = {}
        price_sparklines: dict[int, list[float]] = {}
        for row in sparkline_rows:
            netuid = row.netuid
            emission_sparklines.setdefault(netuid, []).append(float(row.avg_emission))
            price_sparklines.setdefault(netuid, []).append(float(row.avg_price))

        now = datetime.now(UTC)
        subnets: list[ScreenerSubnetSchema] = []

        for snap in latest_snapshots:
            first = first_seen_map.get(snap.netuid, now)
            age_days = max(0, (now - first).days)

            subnets.append(
                ScreenerSubnetSchema(
                    netuid=snap.netuid,
                    name=SUBNET_NAMES.get(snap.netuid),
                    miner_count=snap.miner_count,
                    validator_count=snap.validator_count,
                    registration_cost=snap.registration_cost,
                    emission_share=snap.emission_share,
                    alpha_price=snap.alpha_price,
                    alpha_market_cap=snap.alpha_market_cap,
                    fill_rate=snap.fill_rate,
                    owner_take_rate=snap.owner_take_rate,
                    tao_reserves=snap.tao_reserves,
                    alpha_reserves=snap.alpha_reserves,
                    subnet_age_days=age_days,
                    sparkline_emission_7d=emission_sparklines.get(snap.netuid, []),
                    sparkline_price_7d=price_sparklines.get(snap.netuid, []),
                )
            )

        return ScreenerResponseSchema(subnets=subnets, subnet_count=len(subnets))

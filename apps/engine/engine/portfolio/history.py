"""Historical portfolio value computation from subnet snapshots."""

import hashlib
import json
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import text

from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.portfolio.aggregator import aggregate_portfolio

log = get_logger(__name__)

_CACHE_TTL = 300  # 5 minutes

_BUCKET_CONFIG: dict[str, tuple[str, int]] = {
    "7d": ("1 hour", 7),
    "30d": ("1 day", 30),
    "90d": ("1 day", 90),
}


def _cache_key(coldkey_addresses: list[str], time_range: str) -> str:
    """Build a Redis cache key for portfolio history."""
    addr_hash = hashlib.sha256(",".join(sorted(coldkey_addresses)).encode()).hexdigest()
    return f"portfolio_history:{addr_hash}:{time_range}"


async def get_portfolio_history(
    coldkey_addresses: list[str],
    time_range: str,
) -> tuple[list[dict[str, Any]], str | None]:
    """Compute historical portfolio value from subnet snapshots.

    Returns (points, data_start) where points is [{time, total_value_tao}, ...]
    and data_start is the earliest data timestamp if data doesn't cover full range.
    """
    # Check cache first
    key = _cache_key(coldkey_addresses, time_range)
    try:
        cached = await cache_get(key)
    except Exception:
        log.warning("portfolio_history_cache_read_failed", exc_info=True, worker="portfolio")
        cached = None

    if cached is not None:
        try:
            payload = json.loads(cached)
            return payload["points"], payload["data_start"]
        except Exception:
            log.warning(
                "portfolio_history_cache_deserialize_failed",
                exc_info=True,
                worker="portfolio",
            )

    # Get current portfolio to know positions
    portfolio, _ = await aggregate_portfolio(coldkey_addresses)

    # Build netuid -> (staked_tao, alpha_holdings) from current positions
    position_map: dict[int, tuple[float, float]] = {}
    for pos in portfolio.positions:
        if pos.netuid in position_map:
            existing = position_map[pos.netuid]
            position_map[pos.netuid] = (
                existing[0] + pos.staked_tao,
                existing[1] + pos.alpha_holdings,
            )
        else:
            position_map[pos.netuid] = (pos.staked_tao, pos.alpha_holdings)

    if not position_map:
        result: list[dict[str, Any]] = []
        try:
            await cache_set(key, json.dumps({"points": result, "data_start": None}), _CACHE_TTL)
        except Exception:
            log.warning("portfolio_history_cache_write_failed", exc_info=True, worker="portfolio")
        return result, None

    bucket_interval, days_back = _BUCKET_CONFIG[time_range]
    range_start = datetime.now(UTC) - timedelta(days=days_back)

    netuids = list(position_map.keys())

    query = text("""
        SELECT
            time_bucket(CAST(:bucket AS INTERVAL), time) AS bucket,
            netuid,
            avg(alpha_price) AS avg_alpha_price
        FROM subnet_snapshots
        WHERE time >= :range_start
          AND netuid = ANY(:netuids)
        GROUP BY bucket, netuid
        ORDER BY bucket ASC
    """)

    session_factory = get_session_factory()
    async with session_factory() as session:
        result_rows = await session.execute(
            query,
            {
                "bucket": bucket_interval,
                "range_start": range_start,
                "netuids": netuids,
            },
        )
        rows = result_rows.fetchall()

    # Group rows by bucket timestamp
    bucket_values: dict[str, float] = {}
    for row in rows:
        bucket_time = row[0].isoformat() if hasattr(row[0], "isoformat") else str(row[0])
        netuid = int(row[1])
        avg_price = float(row[2])

        staked_tao, alpha_holdings = position_map.get(netuid, (0.0, 0.0))
        value = staked_tao + alpha_holdings * avg_price

        if bucket_time in bucket_values:
            bucket_values[bucket_time] += value
        else:
            bucket_values[bucket_time] = value

    # Build sorted points
    points: list[dict[str, Any]] = [
        {"time": t, "total_value_tao": round(float(v), 4)} for t, v in sorted(bucket_values.items())
    ]

    # Detect sparse data
    data_start: str | None = None
    if points:
        first_point_time = str(points[0]["time"])
        if first_point_time > range_start.isoformat():
            data_start = first_point_time

    # Cache the result
    try:
        await cache_set(
            key,
            json.dumps({"points": points, "data_start": data_start}),
            _CACHE_TTL,
        )
    except Exception:
        log.warning("portfolio_history_cache_write_failed", exc_info=True, worker="portfolio")

    return points, data_start

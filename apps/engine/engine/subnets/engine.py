"""Subnet detail query engine — cache-first reads for individual subnets."""

import json
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, text

from engine.core.config import settings
from engine.core.database import get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import cache_get, cache_set
from engine.models.metagraph_entry import MetagraphEntry
from engine.models.subnet_snapshot import SubnetSnapshot
from engine.schemas.subnet import (
    SubnetDetailResponseSchema,
    SubnetDetailSchema,
    SubnetHistoryPointSchema,
    SubnetNeuronSchema,
)
from engine.screener.engine import SUBNET_NAMES

log = get_logger(__name__)

VALID_TIME_RANGES = {"7d": 7, "30d": 30, "90d": 90}
NEURON_LIMIT = 50


def _cache_key(netuid: int, time_range: str) -> str:
    return f"subnet:{netuid}:{time_range}"


async def get_subnet_detail(
    netuid: int, time_range: str = "30d"
) -> tuple[SubnetDetailResponseSchema, bool]:
    """Fetch detailed data for a single subnet.

    Returns (response, cache_hit). Raises HTTPException(404) if subnet not found.
    """
    if time_range not in VALID_TIME_RANGES:
        time_range = "30d"

    key = _cache_key(netuid, time_range)
    cached = await cache_get(key)
    if cached is not None:
        data = json.loads(cached)
        return SubnetDetailResponseSchema(**data), True

    result = await _query_subnet_detail(netuid, time_range)

    await cache_set(key, result.model_dump_json(), settings.cache_ttl_screener)

    return result, False


async def _query_subnet_detail(netuid: int, time_range: str) -> SubnetDetailResponseSchema:
    """Query TimescaleDB for subnet detail, history, and neurons."""
    days = VALID_TIME_RANGES[time_range]
    factory = get_session_factory()

    async with factory() as session:
        # Latest snapshot for this netuid
        latest_query = (
            select(SubnetSnapshot)
            .where(SubnetSnapshot.netuid == netuid)
            .order_by(SubnetSnapshot.time.desc())
            .limit(1)
        )
        latest_result = await session.execute(latest_query)
        snapshot = latest_result.scalar_one_or_none()

        if snapshot is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "type": "subnet_not_found",
                        "message": f"No data found for subnet {netuid}",
                        "code": 404,
                    }
                },
            )

        # First-seen date for subnet age
        age_query = select(func.min(SubnetSnapshot.time)).where(SubnetSnapshot.netuid == netuid)
        age_result = await session.execute(age_query)
        first_seen: datetime | None = age_result.scalar_one_or_none()
        now = datetime.now(UTC)
        subnet_age_days = max(0, (now - first_seen).days) if first_seen else 0

        # History — daily aggregates
        history_query = text("""
            SELECT
                date_trunc('day', time) AS day,
                AVG(emission_share) AS avg_emission,
                AVG(alpha_price) AS avg_price,
                AVG(miner_count)::int AS avg_miners
            FROM subnet_snapshots
            WHERE netuid = :netuid
              AND time >= NOW() - MAKE_INTERVAL(days => :days)
            GROUP BY date_trunc('day', time)
            ORDER BY day
        """)
        history_result = await session.execute(history_query, {"netuid": netuid, "days": days})
        history_rows = history_result.fetchall()

        history = [
            SubnetHistoryPointSchema(
                time=row.day.isoformat(),
                emission_share=float(row.avg_emission),
                alpha_price=float(row.avg_price),
                miner_count=int(row.avg_miners),
            )
            for row in history_rows
        ]

        # Latest metagraph entries for neurons
        latest_metagraph_subquery = (
            select(func.max(MetagraphEntry.time))
            .where(MetagraphEntry.netuid == netuid)
            .scalar_subquery()
        )

        neurons_query = (
            select(MetagraphEntry)
            .where(
                MetagraphEntry.netuid == netuid,
                MetagraphEntry.time == latest_metagraph_subquery,
            )
            .order_by(MetagraphEntry.incentive.desc())
        )
        neurons_result = await session.execute(neurons_query)
        all_neurons = neurons_result.scalars().all()

        # Partition into miners and validators
        miners: list[SubnetNeuronSchema] = []
        validators: list[SubnetNeuronSchema] = []

        for neuron in all_neurons:
            # Early exit once both lists are full
            if len(miners) >= NEURON_LIMIT and len(validators) >= NEURON_LIMIT:
                break

            # Validators have dividends > 0; miners have incentive > 0 and no dividends
            if neuron.dividends > 0 and len(validators) < NEURON_LIMIT:
                validators.append(
                    SubnetNeuronSchema(
                        uid=neuron.uid,
                        hotkey=neuron.hotkey,
                        coldkey=neuron.coldkey,
                        stake=neuron.stake,
                        incentive=neuron.incentive,
                        trust=neuron.trust,
                        dividends=neuron.dividends,
                        is_active=neuron.is_active,
                    )
                )
            elif neuron.incentive > 0 and neuron.dividends == 0 and len(miners) < NEURON_LIMIT:
                miners.append(
                    SubnetNeuronSchema(
                        uid=neuron.uid,
                        hotkey=neuron.hotkey,
                        coldkey=neuron.coldkey,
                        stake=neuron.stake,
                        incentive=neuron.incentive,
                        trust=neuron.trust,
                        dividends=neuron.dividends,
                        is_active=neuron.is_active,
                    )
                )

        detail = SubnetDetailSchema(
            netuid=snapshot.netuid,
            name=SUBNET_NAMES.get(snapshot.netuid),
            miner_count=snapshot.miner_count,
            validator_count=snapshot.validator_count,
            registration_cost=snapshot.registration_cost,
            emission_share=snapshot.emission_share,
            alpha_price=snapshot.alpha_price,
            alpha_market_cap=snapshot.alpha_market_cap,
            tao_reserves=snapshot.tao_reserves,
            alpha_reserves=snapshot.alpha_reserves,
            fill_rate=snapshot.fill_rate,
            owner_take_rate=snapshot.owner_take_rate,
            subnet_age_days=subnet_age_days,
            description=None,
        )

        return SubnetDetailResponseSchema(
            detail=detail,
            history=history,
            miners=miners,
            validators=validators,
        )

"""Engine health check endpoint."""

from datetime import UTC, datetime

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import select

from engine.core.database import check_db_health, get_session_factory
from engine.core.logging import get_logger
from engine.core.redis import check_redis_health, get_redis
from engine.models.ingestion_cursor import IngestionCursor
from engine.schemas import BaseSchema
from engine.schemas.errors import ENGINE_VERSION

log = get_logger(__name__)

# Staleness thresholds (seconds)
_STALE_THRESHOLD_S = 300  # 5 min — warn
_CRITICAL_STALE_THRESHOLD_S = 600  # 10 min — return 503


class SyncStatus(BaseSchema):
    last_sync_completed_at: str | None
    subnets_synced: int | None
    subnets_failed: int | None
    subnets_stale: list[int]
    sync_healthy: bool


class HealthData(BaseSchema):
    status: str
    engine: str
    database: str
    redis: str
    sync: SyncStatus


class HealthMeta(BaseSchema):
    service: str
    version: str


class HealthResponse(BaseSchema):
    data: HealthData
    meta: HealthMeta


router = APIRouter()


async def _get_stale_subnets() -> list[int]:
    """Scan Redis for per-subnet sync timestamps and return stale netuids."""
    try:
        redis = get_redis()
        keys: list[str] = []
        async for key in redis.scan_iter(match="metagraph_sync_ts:*"):
            keys.append(str(key))

        now = datetime.now(UTC)
        stale: list[int] = []
        for key in keys:
            netuid_str = key.split(":")[-1]
            val = await redis.get(key)
            if val is None:
                continue
            last_sync = datetime.fromisoformat(str(val))
            if (now - last_sync).total_seconds() > _STALE_THRESHOLD_S:
                stale.append(int(netuid_str))
        return sorted(stale)
    except Exception:
        log.warning("stale_subnets_scan_failed", exc_info=True)
        return []


async def _get_sync_status() -> SyncStatus:
    """Query IngestionCursor for metagraph_sync status."""
    try:
        factory = get_session_factory()
        async with factory() as session:
            result = await session.execute(
                select(IngestionCursor).where(IngestionCursor.source == "metagraph_sync")
            )
            cursor = result.scalar_one_or_none()

            if cursor is None:
                return SyncStatus(
                    last_sync_completed_at=None,
                    subnets_synced=None,
                    subnets_failed=None,
                    subnets_stale=[],
                    sync_healthy=False,
                )

            now = datetime.now(UTC)
            age_s = (now - cursor.last_processed_at).total_seconds()
            metadata = cursor.metadata_json or {}
            stale_subnets = await _get_stale_subnets()

            return SyncStatus(
                last_sync_completed_at=cursor.last_processed_at.isoformat(),
                subnets_synced=metadata.get("subnets_synced"),
                subnets_failed=metadata.get("subnets_failed"),
                subnets_stale=stale_subnets,
                sync_healthy=age_s < _STALE_THRESHOLD_S,
            )
    except Exception:
        log.warning("sync_status_query_failed", exc_info=True)
        return SyncStatus(
            last_sync_completed_at=None,
            subnets_synced=None,
            subnets_failed=None,
            subnets_stale=[],
            sync_healthy=False,
        )


@router.get("/health", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """Return engine health status including database, Redis, and sync status."""
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()
    sync_status = await _get_sync_status()

    is_healthy = db_healthy and redis_healthy
    # Persistently stale sync (> 10 min) degrades overall health
    sync_critically_stale = False
    if sync_status.last_sync_completed_at is not None:
        last_sync = datetime.fromisoformat(sync_status.last_sync_completed_at)
        age_s = (datetime.now(UTC) - last_sync).total_seconds()
        sync_critically_stale = age_s > _CRITICAL_STALE_THRESHOLD_S

    status = "healthy" if is_healthy and not sync_critically_stale else "degraded"

    body = HealthResponse(
        data=HealthData(
            status=status,
            engine="running",
            database="connected" if db_healthy else "disconnected",
            redis="connected" if redis_healthy else "disconnected",
            sync=sync_status,
        ),
        meta=HealthMeta(
            service="subtensor-labs-engine",
            version=ENGINE_VERSION,
        ),
    )
    return JSONResponse(
        status_code=200 if (is_healthy and not sync_critically_stale) else 503,
        content=body.model_dump(),
    )

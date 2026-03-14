"""Engine health check endpoint."""

from fastapi import APIRouter
from pydantic import BaseModel

from engine.core.database import check_db_health
from engine.core.redis import check_redis_health
from engine.schemas.errors import ENGINE_VERSION


class HealthData(BaseModel):
    status: str
    engine: str
    database: str
    redis: str


class HealthMeta(BaseModel):
    service: str
    version: str


class HealthResponse(BaseModel):
    data: HealthData
    meta: HealthMeta


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Return engine health status including database and Redis connectivity."""
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    status = "healthy" if (db_healthy and redis_healthy) else "degraded"

    return HealthResponse(
        data=HealthData(
            status=status,
            engine="running",
            database="connected" if db_healthy else "disconnected",
            redis="connected" if redis_healthy else "disconnected",
        ),
        meta=HealthMeta(
            service="subtensor-labs-engine",
            version=ENGINE_VERSION,
        ),
    )

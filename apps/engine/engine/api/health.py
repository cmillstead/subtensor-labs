"""Engine health check endpoint."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from engine.core.database import check_db_health
from engine.core.redis import check_redis_health
from engine.schemas import BaseSchema
from engine.schemas.errors import ENGINE_VERSION


class HealthData(BaseSchema):
    status: str
    engine: str
    database: str
    redis: str


class HealthMeta(BaseSchema):
    service: str
    version: str


class HealthResponse(BaseSchema):
    data: HealthData
    meta: HealthMeta


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> JSONResponse:
    """Return engine health status including database and Redis connectivity."""
    db_healthy = await check_db_health()
    redis_healthy = await check_redis_health()

    is_healthy = db_healthy and redis_healthy
    status = "healthy" if is_healthy else "degraded"

    body = HealthResponse(
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
    return JSONResponse(
        status_code=200 if is_healthy else 503,
        content=body.model_dump(),
    )

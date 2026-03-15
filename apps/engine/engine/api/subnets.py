"""Subnet detail API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Path, Query
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.subnets.engine import VALID_TIME_RANGES, get_subnet_detail

log = get_logger(__name__)

router = APIRouter(prefix="/subnets")


@router.get("/{netuid}")
async def subnet_detail(
    netuid: int = Path(..., ge=0, description="Subnet network UID"),
    time_range: str = Query("30d", description="History time range: 7d, 30d, or 90d"),
) -> JSONResponse:
    """Return detailed data for a single subnet.

    Returns data wrapped in the standard engine envelope:
    {"data": {...}, "meta": {"last_updated": ..., "cache_hit": ..., "compute_ms": ...}}
    """
    if time_range not in VALID_TIME_RANGES:
        valid = ", ".join(VALID_TIME_RANGES)
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "validation_error",
                    "message": f"Invalid time_range '{time_range}'. Must be one of: {valid}",
                    "code": 422,
                }
            },
        )

    start = time.monotonic()

    result, cache_hit = await get_subnet_detail(netuid, time_range)
    compute_ms = int((time.monotonic() - start) * 1000)

    body: dict[str, Any] = {
        "data": result.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "cache_hit": cache_hit,
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)

"""Screener API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.screener.engine import get_all_subnets

log = get_logger(__name__)

router = APIRouter(prefix="/screener")


@router.get("/query")
async def screener_query() -> JSONResponse:
    """Return all subnet data for the screener table.

    Returns data wrapped in the standard engine envelope:
    {"data": {...}, "meta": {"last_updated": ..., "cache_hit": ..., "compute_ms": ...}}
    """
    start = time.monotonic()

    result, cache_hit = await get_all_subnets()
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

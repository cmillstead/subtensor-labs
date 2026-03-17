"""Prediction API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.predictions.yield_projector import compute_yield_projection
from engine.schemas.predictions import YieldProjectionRequestSchema

log = get_logger(__name__)

router = APIRouter(prefix="/predictions")


@router.post("/yield")
async def yield_projection(
    request_body: YieldProjectionRequestSchema, request: Request
) -> JSONResponse:
    """Compute yield projection for a portfolio.

    Expects X-User-Id header to be set by the Next.js proxy for cache keying.
    Returns projection data wrapped in the standard engine envelope:
    {"data": {...}, "meta": {"last_updated": ..., "cache_hit": ..., "compute_ms": ...}}
    """
    start = time.monotonic()

    # User ID from proxy header; fall back to first address for direct engine calls
    user_id = request.headers.get("x-user-id") or request_body.coldkey_addresses[0]

    projection, cache_hit = await compute_yield_projection(
        user_id=user_id,
        coldkey_addresses=request_body.coldkey_addresses,
        horizons=request_body.horizons,
    )
    compute_ms = int((time.monotonic() - start) * 1000)

    body: dict[str, Any] = {
        "data": projection.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "cache_hit": cache_hit,
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)

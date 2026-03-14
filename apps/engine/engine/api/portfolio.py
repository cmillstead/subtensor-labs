"""Portfolio aggregation API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.portfolio.aggregator import aggregate_portfolio
from engine.schemas.portfolio import PortfolioRequestSchema

log = get_logger(__name__)

router = APIRouter(prefix="/portfolio")


@router.post("/aggregate")
async def portfolio_aggregate(request: PortfolioRequestSchema) -> JSONResponse:
    """Aggregate portfolio across one or more coldkey addresses.

    Returns the unified portfolio wrapped in the standard engine envelope:
    {"data": {...}, "meta": {"last_updated": ..., "cache_hit": ..., "compute_ms": ...}}
    """
    start = time.monotonic()

    portfolio, cache_hit = await aggregate_portfolio(request.coldkey_addresses)
    compute_ms = int((time.monotonic() - start) * 1000)

    body: dict[str, Any] = {
        "data": portfolio.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "cache_hit": cache_hit,
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)

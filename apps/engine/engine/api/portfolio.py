"""Portfolio aggregation API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.portfolio.aggregator import aggregate_portfolio
from engine.portfolio.history import get_portfolio_history
from engine.schemas.portfolio import PortfolioRequestSchema
from engine.schemas.portfolio_history import (
    PortfolioHistoryPointSchema,
    PortfolioHistoryRequestSchema,
    PortfolioHistoryResponseSchema,
)

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


@router.post("/history")
async def portfolio_history(request: PortfolioHistoryRequestSchema) -> JSONResponse:
    """Get historical portfolio value over time.

    Returns time-series data wrapped in the standard engine envelope:
    {"data": {...}, "meta": {"last_updated": ..., "compute_ms": ...}}
    """
    start = time.monotonic()

    points, data_start = await get_portfolio_history(request.coldkey_addresses, request.time_range)
    compute_ms = int((time.monotonic() - start) * 1000)

    response = PortfolioHistoryResponseSchema(
        points=[
            PortfolioHistoryPointSchema(
                time=str(p["time"]),
                total_value_tao=float(p["total_value_tao"]),
            )
            for p in points
        ],
        data_start=data_start,
        time_range=request.time_range,
    )

    body: dict[str, Any] = {
        "data": response.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)

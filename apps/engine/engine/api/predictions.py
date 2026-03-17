"""Prediction API endpoints."""

import time
from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from engine.core.logging import get_logger
from engine.predictions.emission_forecaster import compute_emission_forecast
from engine.predictions.scenario_engine import compute_scenario
from engine.predictions.yield_projector import compute_yield_projection
from engine.schemas.predictions import (
    EmissionForecastRequestSchema,
    ScenarioCalcRequestSchema,
    YieldProjectionRequestSchema,
)

log = get_logger(__name__)

router = APIRouter(prefix="/predictions")


def _user_id_from_request(request: Request, coldkey_addresses: list[str]) -> str:
    """Extract user ID from proxy header or fall back to first address."""
    return request.headers.get("x-user-id") or coldkey_addresses[0]


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
    user_id = _user_id_from_request(request, request_body.coldkey_addresses)

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


@router.post("/scenario")
async def scenario_calculation(
    request_body: ScenarioCalcRequestSchema, request: Request
) -> JSONResponse:
    """Compute scenario comparison for portfolio rebalancing.

    Expects X-User-Id header to be set by the Next.js proxy for cache keying.
    Applies hypothetical moves to user's current positions and compares yield outcomes.
    """
    start = time.monotonic()
    user_id = _user_id_from_request(request, request_body.coldkey_addresses)

    try:
        comparison, cache_hit = await compute_scenario(
            user_id=user_id,
            request_body=request_body,
        )
    except Exception:
        log.exception("scenario_computation_failed", user_id=user_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "computation_failed",
                    "message": "Scenario computation failed unexpectedly",
                    "code": 500,
                }
            },
        )
    compute_ms = int((time.monotonic() - start) * 1000)

    body: dict[str, Any] = {
        "data": comparison.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "cache_hit": cache_hit,
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)


@router.post("/emission")
async def emission_forecast(
    request_body: EmissionForecastRequestSchema, request: Request
) -> JSONResponse:
    """Compute emission trajectory forecast.

    Projects per-subnet emission share using EMA trends, computes halving
    impact and staking migration data.
    """
    start = time.monotonic()
    user_id = _user_id_from_request(request, request_body.coldkey_addresses)

    try:
        forecast, cache_hit = await compute_emission_forecast(
            user_id=user_id,
            request_body=request_body,
        )
    except Exception:
        log.exception("emission_computation_failed", user_id=user_id)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": "computation_failed",
                    "message": "Emission forecast computation failed unexpectedly",
                    "code": 500,
                }
            },
        )
    compute_ms = int((time.monotonic() - start) * 1000)

    body: dict[str, Any] = {
        "data": forecast.model_dump(),
        "meta": {
            "last_updated": datetime.now(UTC).isoformat(),
            "cache_hit": cache_hit,
            "compute_ms": compute_ms,
        },
    }
    return JSONResponse(status_code=200, content=body)

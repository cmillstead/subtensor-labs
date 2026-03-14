"""FastAPI application creation and lifespan management."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from engine.api.router import root_router
from engine.core.bittensor import dispose_subtensor
from engine.core.config import settings
from engine.core.database import dispose_engine
from engine.core.exceptions import EngineError
from engine.core.logging import get_logger, setup_logging
from engine.core.redis import close_redis
from engine.ingestion.metagraph_sync import run_metagraph_sync_cycle
from engine.schemas.errors import ENGINE_VERSION, ErrorDetail, ErrorResponseSchema

log = get_logger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC")


class CatchAllMiddleware(BaseHTTPMiddleware):
    """Catch unhandled exceptions and return sanitized JSON error responses.

    Note: BaseHTTPMiddleware buffers the entire response body, which breaks
    streaming/SSE responses. Convert to pure ASGI middleware when streaming
    endpoints are added.
    """

    async def dispatch(self, request: Request, call_next: Any) -> JSONResponse | Any:
        try:
            return await call_next(request)
        except Exception as exc:
            log.error("unhandled_exception", exc_info=exc)
            body = ErrorResponseSchema(
                error=ErrorDetail(
                    type="internal_error",
                    message="An unexpected error occurred",
                    code=500,
                )
            )
            # Include CORS header so browsers don't swallow the error as an
            # opaque CORS failure (CORSMiddleware runs first but its headers
            # aren't applied to responses generated inside this middleware).
            origin = request.headers.get("origin", "")
            cors_headers: dict[str, str] = {}
            if origin and origin in settings.cors_origins:
                cors_headers["Access-Control-Allow-Origin"] = origin
                cors_headers["Access-Control-Allow-Credentials"] = "true"
            return JSONResponse(status_code=500, content=body.model_dump(), headers=cors_headers)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan: startup and shutdown."""
    setup_logging(debug=settings.debug)
    log.info("engine_starting", host=settings.host, port=settings.port)

    # Register metagraph sync job
    scheduler.add_job(
        run_metagraph_sync_cycle,
        trigger="interval",
        seconds=settings.metagraph_sync_interval_seconds,
        id="metagraph_sync",
        name="Metagraph Sync Pipeline",
        replace_existing=True,
        next_run_time=datetime.now(UTC),
        misfire_grace_time=60,
    )
    scheduler.start()
    log.info(
        "scheduler_started",
        metagraph_sync_interval_s=settings.metagraph_sync_interval_seconds,
    )

    yield

    log.info("engine_stopping")
    scheduler.shutdown(wait=False)
    await dispose_subtensor()
    await dispose_engine()
    await close_redis()
    log.info("engine_stopped")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Subtensor Labs Engine",
        description="Data engine for Bittensor portfolio, predictions, and screener",
        version=ENGINE_VERSION,
        lifespan=lifespan,
    )

    app.add_middleware(CatchAllMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
    )

    app.include_router(root_router)

    @app.exception_handler(EngineError)
    async def engine_error_handler(_request: Request, exc: EngineError) -> JSONResponse:
        body = ErrorResponseSchema(
            error=ErrorDetail(type=exc.error_type, message=exc.message, code=exc.code)
        )
        return JSONResponse(status_code=exc.code, content=body.model_dump())

    return app


app = create_app()

"""Root router — mounts all sub-routers."""

from fastapi import APIRouter

from engine.api.health import router as health_router
from engine.api.portfolio import router as portfolio_router
from engine.api.screener import router as screener_router
from engine.api.subnets import router as subnets_router

root_router = APIRouter(prefix="/engine")
root_router.include_router(health_router, tags=["health"])
root_router.include_router(portfolio_router, tags=["portfolio"])
root_router.include_router(screener_router, tags=["screener"])
root_router.include_router(subnets_router, tags=["subnets"])

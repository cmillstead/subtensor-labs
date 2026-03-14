"""Root router — mounts all sub-routers."""

from fastapi import APIRouter

from engine.api.health import router as health_router
from engine.api.portfolio import router as portfolio_router

root_router = APIRouter(prefix="/engine")
root_router.include_router(health_router, tags=["health"])
root_router.include_router(portfolio_router, tags=["portfolio"])

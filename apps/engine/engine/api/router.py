"""Root router — mounts all sub-routers."""

from fastapi import APIRouter

from engine.api.health import router as health_router

root_router = APIRouter(prefix="/engine")
root_router.include_router(health_router, tags=["health"])

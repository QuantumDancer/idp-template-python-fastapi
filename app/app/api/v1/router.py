from fastapi import APIRouter

from app.api.v1.health import health_router

v1_router = APIRouter()

# Pattern for new resources: create app/api/v1/widgets.py with an APIRouter,
# then add: v1_router.include_router(widgets_router, prefix="/widgets", tags=["widgets"])
# Full URL will be /api/v1/widgets/. Docs, metrics, and correlation IDs come free.
v1_router.include_router(health_router, prefix="/health", tags=["health"])

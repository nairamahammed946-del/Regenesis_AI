from fastapi import APIRouter
from backend.app.api.routes import (
    auth, factories, listings, marketplace, matching,
    analysis, environmental, dashboard, advisor, notifications,
    reports, map as map_route, legacy
)
from backend.app.core.config import settings

api_router = APIRouter()

# Versioned API Routes (/api/v1/...)
v1_router = APIRouter(prefix=settings.API_V1_PREFIX)
v1_router.include_router(auth.router)
v1_router.include_router(factories.router)
v1_router.include_router(listings.router)
v1_router.include_router(marketplace.router)
v1_router.include_router(matching.router)
v1_router.include_router(analysis.router)
v1_router.include_router(environmental.router)
v1_router.include_router(dashboard.router)
v1_router.include_router(advisor.router)
v1_router.include_router(notifications.router)
v1_router.include_router(reports.router)
v1_router.include_router(map_route.router)

api_router.include_router(v1_router)

# Legacy Unversioned Routes (/api/...) for 100% Original Frontend Compatibility
api_router.include_router(legacy.router, prefix="/api")

"""
API v1 router aggregating all endpoint routers.

Combines all v1 endpoint routers into a single router.
"""

from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, uploads, admin, documents, audit, negotiation, dashboard

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Authentication"],
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Users"],
)
api_router.include_router(
    uploads.router,
    prefix="/uploads",
    tags=["Uploads"],
)
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["Documents"],
)
api_router.include_router(
    admin.router,
    tags=["Admin"],
)
api_router.include_router(
    audit.router,
    prefix="/audit",
    tags=["Audit"],
)
api_router.include_router(
    negotiation.router,
    prefix="/negotiations",
    tags=["Negotiations"],
)
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["Dashboard"],
)


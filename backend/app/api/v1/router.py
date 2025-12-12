"""
API v1 router aggregating all endpoint routers.

Combines all v1 endpoint routers into a single router.
Organized into:
- B2C endpoints (for patients/users)
- B2B endpoints (for hospital administrators)
"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth, users, uploads, admin, documents, audit, 
    negotiation, dashboard, pricing, translate,
    b2b_auth, b2b_dashboard
)

api_router = APIRouter()

# ============================================
# B2C Endpoints (Patients/Users)
# ============================================

api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["B2C - Authentication"],
)
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["B2C - Users"],
)
api_router.include_router(
    uploads.router,
    prefix="/uploads",
    tags=["B2C - Uploads"],
)
api_router.include_router(
    documents.router,
    prefix="/documents",
    tags=["B2C - Documents"],
)
api_router.include_router(
    audit.router,
    prefix="/audit",
    tags=["B2C - Audit"],
)
api_router.include_router(
    negotiation.router,
    prefix="/negotiations",
    tags=["B2C - Negotiations"],
)
api_router.include_router(
    dashboard.router,
    prefix="/dashboard",
    tags=["B2C - Dashboard"],
)
api_router.include_router(
    pricing.router,
    prefix="/pricing",
    tags=["Pricing Intelligence"],
)
api_router.include_router(
    translate.router,
    prefix="/translate",
    tags=["Translation"],
)

# ============================================
# B2B Endpoints (Hospital Administrators)
# ============================================

api_router.include_router(
    b2b_auth.router,
    prefix="/b2b/auth",
    tags=["B2B - Authentication"],
)
api_router.include_router(
    b2b_dashboard.router,
    prefix="/b2b/dashboard",
    tags=["B2B - Hospital Dashboard"],
)

# ============================================
# Admin Endpoints
# ============================================

api_router.include_router(
    admin.router,
    tags=["Admin"],
)

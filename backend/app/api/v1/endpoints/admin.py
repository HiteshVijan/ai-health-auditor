"""
Admin API Endpoints.

Protected endpoints for administrative functions requiring elevated privileges.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import get_db
from app.models.user import User, UserRole
from app.core.rbac import (
    Role,
    Permission,
    require_role,
    require_permission,
    get_role_permissions,
)
from app.core.encryption import get_encryption_service

router = APIRouter(prefix="/admin", tags=["admin"])


# ============================================
# Schemas
# ============================================

class UserResponse(BaseModel):
    """User response schema."""
    id: int
    username: str
    email: str
    full_name: Optional[str]
    role: str
    is_active: bool
    is_verified: bool
    
    class Config:
        from_attributes = True


class UserRoleUpdate(BaseModel):
    """Schema for updating user role."""
    role: str


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int


class RolePermissionsResponse(BaseModel):
    """Response showing role permissions."""
    role: str
    permissions: List[str]


class SystemStatsResponse(BaseModel):
    """System statistics response."""
    total_users: int
    active_users: int
    users_by_role: dict
    pending_review_tasks: int


# ============================================
# User Management Endpoints
# ============================================

@router.get(
    "/users",
    response_model=UserListResponse,
    dependencies=[Depends(require_permission(Permission.USER_VIEW))],
)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    List all users with pagination and filters.
    
    Requires: ADMIN role
    """
    query = db.query(User)
    
    if role:
        query = query.filter(User.role == UserRole(role))
    
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    
    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()
    
    return UserListResponse(
        users=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get(
    "/users/{user_id}",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.USER_VIEW))],
)
async def get_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Get a specific user's details.
    
    Requires: ADMIN role
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.USER_MANAGE_ROLES))],
)
async def update_user_role(
    user_id: int,
    role_update: UserRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Update a user's role.
    
    Requires: ADMIN role with USER_MANAGE_ROLES permission
    """
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    # Prevent self-demotion
    if user.id == current_user.id and role_update.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot demote yourself from admin",
        )
    
    try:
        user.role = UserRole(role_update.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {[r.value for r in UserRole]}",
        )
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/activate",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.USER_UPDATE))],
)
async def activate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Activate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.patch(
    "/users/{user_id}/deactivate",
    response_model=UserResponse,
    dependencies=[Depends(require_permission(Permission.USER_UPDATE))],
)
async def deactivate_user(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """Deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="Cannot deactivate yourself",
        )
    
    user.is_active = False
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return UserResponse.model_validate(user)


# ============================================
# Role & Permission Endpoints
# ============================================

@router.get(
    "/roles",
    response_model=List[RolePermissionsResponse],
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def list_roles():
    """
    List all roles and their permissions.
    
    Requires: ADMIN role
    """
    return [
        RolePermissionsResponse(
            role=role.value,
            permissions=[p.value for p in get_role_permissions(role)],
        )
        for role in Role
    ]


@router.get(
    "/roles/{role_name}/permissions",
    response_model=RolePermissionsResponse,
    dependencies=[Depends(require_role(Role.ADMIN))],
)
async def get_role_permissions_endpoint(role_name: str):
    """
    Get permissions for a specific role.
    
    Requires: ADMIN role
    """
    try:
        role = Role(role_name)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid role. Must be one of: {[r.value for r in Role]}",
        )
    
    return RolePermissionsResponse(
        role=role.value,
        permissions=[p.value for p in get_role_permissions(role)],
    )


# ============================================
# System Stats Endpoints
# ============================================

@router.get(
    "/stats",
    response_model=SystemStatsResponse,
    dependencies=[Depends(require_permission(Permission.SYSTEM_METRICS))],
)
async def get_system_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    """
    Get system statistics.
    
    Requires: ADMIN role with SYSTEM_METRICS permission
    """
    from app.models.review_task import ReviewTask, ReviewTaskStatus
    
    total_users = db.query(User).count()
    active_users = db.query(User).filter(User.is_active == True).count()
    
    users_by_role = {}
    for role in UserRole:
        count = db.query(User).filter(User.role == role).count()
        users_by_role[role.value] = count
    
    pending_tasks = db.query(ReviewTask).filter(
        ReviewTask.status == ReviewTaskStatus.PENDING
    ).count()
    
    return SystemStatsResponse(
        total_users=total_users,
        active_users=active_users,
        users_by_role=users_by_role,
        pending_review_tasks=pending_tasks,
    )


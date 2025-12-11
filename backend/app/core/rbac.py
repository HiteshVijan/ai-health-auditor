"""
Role-Based Access Control (RBAC) Module.

Implements role-based permissions for API endpoint access control.
"""

import logging
from enum import Enum
from functools import wraps
from typing import Callable, List, Optional, Set, Union

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.api.deps import get_current_user
from app.models.user import User

logger = logging.getLogger(__name__)


class Role(str, Enum):
    """User roles with hierarchical permissions."""
    
    USER = "user"           # Basic user - can upload and view own documents
    REVIEWER = "reviewer"   # Can review low-confidence fields
    ADMIN = "admin"         # Full access to all features


class Permission(str, Enum):
    """Granular permissions for fine-grained access control."""
    
    # Document permissions
    DOCUMENT_CREATE = "document:create"
    DOCUMENT_READ = "document:read"
    DOCUMENT_READ_ALL = "document:read_all"
    DOCUMENT_DELETE = "document:delete"
    DOCUMENT_DELETE_ALL = "document:delete_all"
    
    # Audit permissions
    AUDIT_VIEW = "audit:view"
    AUDIT_VIEW_ALL = "audit:view_all"
    AUDIT_EXPORT = "audit:export"
    
    # Review task permissions
    REVIEW_VIEW = "review:view"
    REVIEW_ASSIGN = "review:assign"
    REVIEW_SUBMIT = "review:submit"
    REVIEW_MANAGE = "review:manage"
    
    # Negotiation permissions
    NEGOTIATION_CREATE = "negotiation:create"
    NEGOTIATION_SEND = "negotiation:send"
    
    # User management permissions
    USER_VIEW = "user:view"
    USER_CREATE = "user:create"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_MANAGE_ROLES = "user:manage_roles"
    
    # System permissions
    SYSTEM_METRICS = "system:metrics"
    SYSTEM_LOGS = "system:logs"
    SYSTEM_CONFIG = "system:config"
    
    # ML pipeline permissions
    ML_RETRAIN = "ml:retrain"
    ML_VIEW_MODELS = "ml:view_models"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.USER: {
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_DELETE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.NEGOTIATION_CREATE,
        Permission.NEGOTIATION_SEND,
    },
    Role.REVIEWER: {
        # Inherits USER permissions
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_DELETE,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_EXPORT,
        Permission.NEGOTIATION_CREATE,
        Permission.NEGOTIATION_SEND,
        # Additional reviewer permissions
        Permission.REVIEW_VIEW,
        Permission.REVIEW_SUBMIT,
        Permission.DOCUMENT_READ_ALL,
        Permission.AUDIT_VIEW_ALL,
    },
    Role.ADMIN: {
        # All permissions
        Permission.DOCUMENT_CREATE,
        Permission.DOCUMENT_READ,
        Permission.DOCUMENT_READ_ALL,
        Permission.DOCUMENT_DELETE,
        Permission.DOCUMENT_DELETE_ALL,
        Permission.AUDIT_VIEW,
        Permission.AUDIT_VIEW_ALL,
        Permission.AUDIT_EXPORT,
        Permission.REVIEW_VIEW,
        Permission.REVIEW_ASSIGN,
        Permission.REVIEW_SUBMIT,
        Permission.REVIEW_MANAGE,
        Permission.NEGOTIATION_CREATE,
        Permission.NEGOTIATION_SEND,
        Permission.USER_VIEW,
        Permission.USER_CREATE,
        Permission.USER_UPDATE,
        Permission.USER_DELETE,
        Permission.USER_MANAGE_ROLES,
        Permission.SYSTEM_METRICS,
        Permission.SYSTEM_LOGS,
        Permission.SYSTEM_CONFIG,
        Permission.ML_RETRAIN,
        Permission.ML_VIEW_MODELS,
    },
}


def get_role_permissions(role: Role) -> Set[Permission]:
    """Get all permissions for a given role."""
    return ROLE_PERMISSIONS.get(role, set())


def has_permission(user_role: Role, permission: Permission) -> bool:
    """Check if a role has a specific permission."""
    role_permissions = get_role_permissions(user_role)
    return permission in role_permissions


def has_any_permission(user_role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has any of the specified permissions."""
    role_permissions = get_role_permissions(user_role)
    return any(p in role_permissions for p in permissions)


def has_all_permissions(user_role: Role, permissions: List[Permission]) -> bool:
    """Check if a role has all of the specified permissions."""
    role_permissions = get_role_permissions(user_role)
    return all(p in role_permissions for p in permissions)


class RBACError(Exception):
    """Base exception for RBAC errors."""
    pass


class InsufficientPermissionsError(RBACError):
    """Raised when user lacks required permissions."""
    pass


def require_role(allowed_roles: Union[Role, List[Role]]) -> Callable:
    """
    Dependency that requires the user to have one of the allowed roles.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role(Role.ADMIN))):
            ...
    """
    if isinstance(allowed_roles, Role):
        allowed_roles = [allowed_roles]
    
    async def role_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_role = Role(current_user.role) if current_user.role else Role.USER
        
        if user_role not in allowed_roles:
            logger.warning(
                f"Access denied: user {current_user.id} with role {user_role} "
                f"attempted to access endpoint requiring {allowed_roles}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required roles: {[r.value for r in allowed_roles]}",
            )
        
        return current_user
    
    return role_checker


def require_permission(required_permission: Permission) -> Callable:
    """
    Dependency that requires the user to have a specific permission.
    
    Usage:
        @router.post("/retrain")
        async def retrain_model(user: User = Depends(require_permission(Permission.ML_RETRAIN))):
            ...
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_role = Role(current_user.role) if current_user.role else Role.USER
        
        if not has_permission(user_role, required_permission):
            logger.warning(
                f"Access denied: user {current_user.id} with role {user_role} "
                f"lacks permission {required_permission}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission.value}",
            )
        
        return current_user
    
    return permission_checker


def require_any_permission(required_permissions: List[Permission]) -> Callable:
    """
    Dependency that requires the user to have at least one of the permissions.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_role = Role(current_user.role) if current_user.role else Role.USER
        
        if not has_any_permission(user_role, required_permissions):
            logger.warning(
                f"Access denied: user {current_user.id} with role {user_role} "
                f"lacks any of permissions {required_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required one of: {[p.value for p in required_permissions]}",
            )
        
        return current_user
    
    return permission_checker


def require_all_permissions(required_permissions: List[Permission]) -> Callable:
    """
    Dependency that requires the user to have all of the permissions.
    """
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ) -> User:
        user_role = Role(current_user.role) if current_user.role else Role.USER
        
        if not has_all_permissions(user_role, required_permissions):
            logger.warning(
                f"Access denied: user {current_user.id} with role {user_role} "
                f"lacks all permissions {required_permissions}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required all of: {[p.value for p in required_permissions]}",
            )
        
        return current_user
    
    return permission_checker


def check_resource_ownership(
    user: User,
    resource_owner_id: int,
    bypass_permission: Optional[Permission] = None,
) -> bool:
    """
    Check if user owns a resource or has permission to bypass ownership check.
    
    Args:
        user: The current user.
        resource_owner_id: The owner ID of the resource.
        bypass_permission: Permission that allows access regardless of ownership.
    
    Returns:
        True if user can access the resource.
    
    Raises:
        HTTPException: If access is denied.
    """
    # Owner can always access their own resources
    if user.id == resource_owner_id:
        return True
    
    # Check bypass permission (e.g., admin access)
    if bypass_permission:
        user_role = Role(user.role) if user.role else Role.USER
        if has_permission(user_role, bypass_permission):
            return True
    
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You don't have permission to access this resource",
    )


class RBACContext:
    """
    Context manager for checking permissions within a function.
    
    Usage:
        with RBACContext(user) as rbac:
            rbac.require(Permission.DOCUMENT_READ)
            # ... perform action
    """
    
    def __init__(self, user: User):
        self.user = user
        self.role = Role(user.role) if user.role else Role.USER
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        return False
    
    def require(self, permission: Permission) -> None:
        """Require a specific permission."""
        if not has_permission(self.role, permission):
            raise InsufficientPermissionsError(
                f"User lacks permission: {permission.value}"
            )
    
    def require_any(self, permissions: List[Permission]) -> None:
        """Require at least one of the permissions."""
        if not has_any_permission(self.role, permissions):
            raise InsufficientPermissionsError(
                f"User lacks any of: {[p.value for p in permissions]}"
            )
    
    def has(self, permission: Permission) -> bool:
        """Check if user has a permission without raising."""
        return has_permission(self.role, permission)
    
    def can_access_resource(
        self,
        resource_owner_id: int,
        bypass_permission: Optional[Permission] = None,
    ) -> bool:
        """Check if user can access a resource."""
        if self.user.id == resource_owner_id:
            return True
        
        if bypass_permission and self.has(bypass_permission):
            return True
        
        return False


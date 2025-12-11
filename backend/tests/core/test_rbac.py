"""
Unit tests for RBAC module.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi import HTTPException

from app.core.rbac import (
    Role,
    Permission,
    ROLE_PERMISSIONS,
    get_role_permissions,
    has_permission,
    has_any_permission,
    has_all_permissions,
    require_role,
    require_permission,
    require_any_permission,
    require_all_permissions,
    check_resource_ownership,
    RBACContext,
    InsufficientPermissionsError,
)
from app.models.user import User, UserRole


@pytest.fixture
def mock_user():
    """Create a mock user."""
    user = MagicMock(spec=User)
    user.id = 1
    user.role = UserRole.USER.value
    return user


@pytest.fixture
def mock_reviewer():
    """Create a mock reviewer user."""
    user = MagicMock(spec=User)
    user.id = 2
    user.role = UserRole.REVIEWER.value
    return user


@pytest.fixture
def mock_admin():
    """Create a mock admin user."""
    user = MagicMock(spec=User)
    user.id = 3
    user.role = UserRole.ADMIN.value
    return user


class TestRolePermissions:
    """Tests for role permissions mapping."""
    
    def test_all_roles_have_permissions(self):
        """All roles should have defined permissions."""
        for role in Role:
            permissions = get_role_permissions(role)
            assert isinstance(permissions, set)
    
    def test_admin_has_all_permissions(self):
        """Admin should have all defined permissions."""
        admin_permissions = get_role_permissions(Role.ADMIN)
        
        # Admin should have user management
        assert Permission.USER_VIEW in admin_permissions
        assert Permission.USER_MANAGE_ROLES in admin_permissions
        
        # Admin should have system access
        assert Permission.SYSTEM_METRICS in admin_permissions
        assert Permission.SYSTEM_CONFIG in admin_permissions
    
    def test_reviewer_has_review_permissions(self):
        """Reviewer should have review permissions."""
        reviewer_permissions = get_role_permissions(Role.REVIEWER)
        
        assert Permission.REVIEW_VIEW in reviewer_permissions
        assert Permission.REVIEW_SUBMIT in reviewer_permissions
    
    def test_user_has_basic_permissions(self):
        """User should have basic permissions."""
        user_permissions = get_role_permissions(Role.USER)
        
        assert Permission.DOCUMENT_CREATE in user_permissions
        assert Permission.DOCUMENT_READ in user_permissions
        assert Permission.AUDIT_VIEW in user_permissions
    
    def test_user_lacks_admin_permissions(self):
        """User should not have admin permissions."""
        user_permissions = get_role_permissions(Role.USER)
        
        assert Permission.USER_MANAGE_ROLES not in user_permissions
        assert Permission.SYSTEM_CONFIG not in user_permissions
        assert Permission.ML_RETRAIN not in user_permissions


class TestHasPermission:
    """Tests for permission checking functions."""
    
    def test_has_permission_true(self):
        """Should return True for valid permission."""
        assert has_permission(Role.USER, Permission.DOCUMENT_CREATE)
        assert has_permission(Role.ADMIN, Permission.USER_MANAGE_ROLES)
    
    def test_has_permission_false(self):
        """Should return False for invalid permission."""
        assert not has_permission(Role.USER, Permission.USER_MANAGE_ROLES)
        assert not has_permission(Role.REVIEWER, Permission.SYSTEM_CONFIG)
    
    def test_has_any_permission(self):
        """Should return True if any permission is present."""
        assert has_any_permission(
            Role.USER,
            [Permission.DOCUMENT_CREATE, Permission.USER_MANAGE_ROLES]
        )
        
        assert not has_any_permission(
            Role.USER,
            [Permission.USER_MANAGE_ROLES, Permission.SYSTEM_CONFIG]
        )
    
    def test_has_all_permissions(self):
        """Should return True only if all permissions are present."""
        assert has_all_permissions(
            Role.ADMIN,
            [Permission.USER_VIEW, Permission.USER_MANAGE_ROLES]
        )
        
        assert not has_all_permissions(
            Role.USER,
            [Permission.DOCUMENT_CREATE, Permission.USER_MANAGE_ROLES]
        )


class TestRequireRole:
    """Tests for require_role dependency."""
    
    @pytest.mark.asyncio
    async def test_require_role_success(self, mock_admin):
        """Should allow user with correct role."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_admin
            
            checker = require_role(Role.ADMIN)
            result = await checker(current_user=mock_admin)
            
            assert result == mock_admin
    
    @pytest.mark.asyncio
    async def test_require_role_failure(self, mock_user):
        """Should deny user without correct role."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user
            
            checker = require_role(Role.ADMIN)
            
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_user=mock_user)
            
            assert exc_info.value.status_code == 403
    
    @pytest.mark.asyncio
    async def test_require_role_multiple(self, mock_reviewer):
        """Should allow any of multiple roles."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_reviewer
            
            checker = require_role([Role.REVIEWER, Role.ADMIN])
            result = await checker(current_user=mock_reviewer)
            
            assert result == mock_reviewer


class TestRequirePermission:
    """Tests for require_permission dependency."""
    
    @pytest.mark.asyncio
    async def test_require_permission_success(self, mock_user):
        """Should allow user with required permission."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user
            
            checker = require_permission(Permission.DOCUMENT_CREATE)
            result = await checker(current_user=mock_user)
            
            assert result == mock_user
    
    @pytest.mark.asyncio
    async def test_require_permission_failure(self, mock_user):
        """Should deny user without required permission."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user
            
            checker = require_permission(Permission.USER_MANAGE_ROLES)
            
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_user=mock_user)
            
            assert exc_info.value.status_code == 403


class TestRequireAnyPermission:
    """Tests for require_any_permission dependency."""
    
    @pytest.mark.asyncio
    async def test_require_any_success(self, mock_reviewer):
        """Should allow if user has any of the permissions."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_reviewer
            
            checker = require_any_permission([
                Permission.REVIEW_VIEW,
                Permission.USER_MANAGE_ROLES,
            ])
            result = await checker(current_user=mock_reviewer)
            
            assert result == mock_reviewer
    
    @pytest.mark.asyncio
    async def test_require_any_failure(self, mock_user):
        """Should deny if user has none of the permissions."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_user
            
            checker = require_any_permission([
                Permission.REVIEW_MANAGE,
                Permission.USER_MANAGE_ROLES,
            ])
            
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_user=mock_user)
            
            assert exc_info.value.status_code == 403


class TestRequireAllPermissions:
    """Tests for require_all_permissions dependency."""
    
    @pytest.mark.asyncio
    async def test_require_all_success(self, mock_admin):
        """Should allow if user has all permissions."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_admin
            
            checker = require_all_permissions([
                Permission.USER_VIEW,
                Permission.USER_MANAGE_ROLES,
            ])
            result = await checker(current_user=mock_admin)
            
            assert result == mock_admin
    
    @pytest.mark.asyncio
    async def test_require_all_failure(self, mock_reviewer):
        """Should deny if user lacks any permission."""
        with patch("backend.app.core.rbac.get_current_user") as mock_get_user:
            mock_get_user.return_value = mock_reviewer
            
            checker = require_all_permissions([
                Permission.REVIEW_VIEW,  # Has this
                Permission.USER_MANAGE_ROLES,  # Doesn't have this
            ])
            
            with pytest.raises(HTTPException) as exc_info:
                await checker(current_user=mock_reviewer)
            
            assert exc_info.value.status_code == 403


class TestCheckResourceOwnership:
    """Tests for resource ownership checking."""
    
    def test_owner_can_access(self, mock_user):
        """Owner should be able to access their resource."""
        result = check_resource_ownership(
            user=mock_user,
            resource_owner_id=mock_user.id,
        )
        assert result is True
    
    def test_non_owner_denied(self, mock_user):
        """Non-owner should be denied access."""
        with pytest.raises(HTTPException) as exc_info:
            check_resource_ownership(
                user=mock_user,
                resource_owner_id=999,
            )
        
        assert exc_info.value.status_code == 403
    
    def test_bypass_permission_allows_access(self, mock_admin):
        """User with bypass permission should access any resource."""
        result = check_resource_ownership(
            user=mock_admin,
            resource_owner_id=999,
            bypass_permission=Permission.DOCUMENT_READ_ALL,
        )
        assert result is True
    
    def test_bypass_permission_not_held(self, mock_user):
        """User without bypass permission should be denied."""
        with pytest.raises(HTTPException):
            check_resource_ownership(
                user=mock_user,
                resource_owner_id=999,
                bypass_permission=Permission.DOCUMENT_READ_ALL,
            )


class TestRBACContext:
    """Tests for RBACContext context manager."""
    
    def test_context_require_success(self, mock_user):
        """Should not raise for valid permission."""
        with RBACContext(mock_user) as rbac:
            rbac.require(Permission.DOCUMENT_CREATE)  # Should not raise
    
    def test_context_require_failure(self, mock_user):
        """Should raise for invalid permission."""
        with RBACContext(mock_user) as rbac:
            with pytest.raises(InsufficientPermissionsError):
                rbac.require(Permission.USER_MANAGE_ROLES)
    
    def test_context_require_any_success(self, mock_reviewer):
        """Should not raise if any permission is present."""
        with RBACContext(mock_reviewer) as rbac:
            rbac.require_any([Permission.REVIEW_VIEW, Permission.SYSTEM_CONFIG])
    
    def test_context_require_any_failure(self, mock_user):
        """Should raise if no permission is present."""
        with RBACContext(mock_user) as rbac:
            with pytest.raises(InsufficientPermissionsError):
                rbac.require_any([Permission.REVIEW_MANAGE, Permission.SYSTEM_CONFIG])
    
    def test_context_has_permission(self, mock_admin):
        """Should check permission without raising."""
        with RBACContext(mock_admin) as rbac:
            assert rbac.has(Permission.USER_MANAGE_ROLES)
            assert not rbac.has(Permission(Permission.DOCUMENT_CREATE))  # Has it too actually
    
    def test_context_can_access_resource_owner(self, mock_user):
        """Should allow access to own resource."""
        with RBACContext(mock_user) as rbac:
            assert rbac.can_access_resource(mock_user.id)
    
    def test_context_can_access_resource_with_bypass(self, mock_admin):
        """Should allow access with bypass permission."""
        with RBACContext(mock_admin) as rbac:
            assert rbac.can_access_resource(
                999,
                bypass_permission=Permission.DOCUMENT_READ_ALL,
            )


class TestRoleHierarchy:
    """Tests for role hierarchy and inheritance."""
    
    def test_admin_has_more_than_reviewer(self):
        """Admin should have more permissions than reviewer."""
        admin_perms = get_role_permissions(Role.ADMIN)
        reviewer_perms = get_role_permissions(Role.REVIEWER)
        
        assert len(admin_perms) > len(reviewer_perms)
    
    def test_reviewer_has_more_than_user(self):
        """Reviewer should have more permissions than user."""
        reviewer_perms = get_role_permissions(Role.REVIEWER)
        user_perms = get_role_permissions(Role.USER)
        
        assert len(reviewer_perms) > len(user_perms)
    
    def test_reviewer_inherits_user_permissions(self):
        """Reviewer should have all user permissions."""
        reviewer_perms = get_role_permissions(Role.REVIEWER)
        user_perms = get_role_permissions(Role.USER)
        
        # All user permissions should be in reviewer permissions
        for perm in user_perms:
            assert perm in reviewer_perms, f"Reviewer missing user permission: {perm}"


class TestPermissionCategories:
    """Tests for permission categories."""
    
    def test_document_permissions(self):
        """Document permissions should exist."""
        assert Permission.DOCUMENT_CREATE
        assert Permission.DOCUMENT_READ
        assert Permission.DOCUMENT_READ_ALL
        assert Permission.DOCUMENT_DELETE
        assert Permission.DOCUMENT_DELETE_ALL
    
    def test_audit_permissions(self):
        """Audit permissions should exist."""
        assert Permission.AUDIT_VIEW
        assert Permission.AUDIT_VIEW_ALL
        assert Permission.AUDIT_EXPORT
    
    def test_review_permissions(self):
        """Review permissions should exist."""
        assert Permission.REVIEW_VIEW
        assert Permission.REVIEW_ASSIGN
        assert Permission.REVIEW_SUBMIT
        assert Permission.REVIEW_MANAGE
    
    def test_user_permissions(self):
        """User management permissions should exist."""
        assert Permission.USER_VIEW
        assert Permission.USER_CREATE
        assert Permission.USER_UPDATE
        assert Permission.USER_DELETE
        assert Permission.USER_MANAGE_ROLES
    
    def test_system_permissions(self):
        """System permissions should exist."""
        assert Permission.SYSTEM_METRICS
        assert Permission.SYSTEM_LOGS
        assert Permission.SYSTEM_CONFIG
    
    def test_ml_permissions(self):
        """ML pipeline permissions should exist."""
        assert Permission.ML_RETRAIN
        assert Permission.ML_VIEW_MODELS


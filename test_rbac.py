"""
Tests for RBAC Module - Issue #4
"""

import pytest
from datetime import datetime, timedelta, timezone
from rbac import (
    RBACManager,
    UserRole,
    Permission,
    Resource,
    ResourceType,
    PermissionDeniedError,
    AccessControlEntry,
)


class TestRoleAssignment:
    """Test role assignment functionality"""

    def test_assign_role(self):
        """Test assigning a role to a user"""
        rbac = RBACManager()
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        assert rbac.get_user_role("user_1") == UserRole.ADMIN

    def test_assign_multiple_roles(self):
        """Test assigning roles to multiple users"""
        rbac = RBACManager()
        rbac.assign_role("user_1", UserRole.ADMIN, "system")
        rbac.assign_role("user_2", UserRole.MODERATOR, "user_1")
        rbac.assign_role("user_3", UserRole.USER, "user_1")

        assert rbac.get_user_role("user_1") == UserRole.ADMIN
        assert rbac.get_user_role("user_2") == UserRole.MODERATOR
        assert rbac.get_user_role("user_3") == UserRole.USER

    def test_reassign_role(self):
        """Test changing a user's role"""
        rbac = RBACManager()
        rbac.assign_role("user_1", UserRole.USER, "system")
        assert rbac.get_user_role("user_1") == UserRole.USER

        rbac.assign_role("user_1", UserRole.MODERATOR, "system")
        assert rbac.get_user_role("user_1") == UserRole.MODERATOR

    def test_get_nonexistent_user_role(self):
        """Test getting role for user with no role assigned"""
        rbac = RBACManager()
        assert rbac.get_user_role("nonexistent_user") is None


class TestRolePermissions:
    """Test role-based permissions"""

    def test_super_admin_has_all_permissions(self):
        """Test that SUPER_ADMIN has all permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.SUPER_ADMIN)

        # Should have all defined permissions
        assert Permission.ASSET_CREATE in permissions
        assert Permission.USER_DELETE in permissions
        assert Permission.SYSTEM_CONFIG in permissions
        assert len(permissions) == len(Permission)

    def test_admin_permissions(self):
        """Test ADMIN role permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.ADMIN)

        assert Permission.ASSET_CREATE in permissions
        assert Permission.ASSET_DELETE in permissions
        assert Permission.MODERATE_CONTENT in permissions
        assert Permission.ANALYTICS_VIEW in permissions

        # Should not have user creation permission
        assert Permission.USER_CREATE not in permissions

    def test_moderator_permissions(self):
        """Test MODERATOR role permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.MODERATOR)

        assert Permission.MODERATE_CONTENT in permissions
        assert Permission.ASSET_READ in permissions

        # Should not have delete or create permissions
        assert Permission.ASSET_CREATE not in permissions
        assert Permission.ASSET_DELETE not in permissions

    def test_content_creator_permissions(self):
        """Test CONTENT_CREATOR role permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.CONTENT_CREATOR)

        assert Permission.ASSET_CREATE in permissions
        assert Permission.ASSET_PUBLISH in permissions
        assert Permission.PUBLISH_GIPHY in permissions

        # Should not have moderation permissions
        assert Permission.MODERATE_CONTENT not in permissions

    def test_user_permissions(self):
        """Test USER role permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.USER)

        assert Permission.ASSET_CREATE in permissions
        assert Permission.ASSET_READ in permissions

        # Limited permissions
        assert Permission.ASSET_DELETE not in permissions
        assert Permission.MODERATE_CONTENT not in permissions

    def test_guest_permissions(self):
        """Test GUEST role permissions"""
        rbac = RBACManager()
        permissions = rbac.get_role_permissions(UserRole.GUEST)

        assert Permission.ASSET_READ in permissions

        # Very limited permissions
        assert Permission.ASSET_CREATE not in permissions
        assert len(permissions) == 1


class TestPermissionChecking:
    """Test permission checking functionality"""

    def test_has_permission_with_role(self):
        """Test checking permissions via role"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        assert rbac.has_permission("user_1", Permission.ASSET_CREATE)
        assert rbac.has_permission("user_1", Permission.MODERATE_CONTENT)

    def test_has_permission_denied(self):
        """Test permission denied for user without permission"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        assert rbac.has_permission("user_1", Permission.ASSET_CREATE)
        assert not rbac.has_permission("user_1", Permission.MODERATE_CONTENT)

    def test_has_permission_no_role(self):
        """Test permission denied for user with no role"""
        rbac = RBACManager(enable_audit=False)

        assert not rbac.has_permission("user_1", Permission.ASSET_CREATE)

    def test_require_permission_success(self):
        """Test require_permission doesn't raise when user has permission"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        # Should not raise
        rbac.require_permission("user_1", Permission.ASSET_CREATE)

    def test_require_permission_failure(self):
        """Test require_permission raises when user lacks permission"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        with pytest.raises(PermissionDeniedError):
            rbac.require_permission("user_1", Permission.MODERATE_CONTENT)


class TestResourceACL:
    """Test resource-level access control"""

    def test_grant_resource_access(self):
        """Test granting access to specific resource"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(resource_type=ResourceType.ASSET, resource_id="asset_123")

        # User doesn't have update permission by role
        assert not rbac.has_permission("user_1", Permission.ASSET_UPDATE)

        # Grant resource-specific access
        rbac.grant_resource_access(
            user_id="user_1",
            resource=resource,
            permissions={Permission.ASSET_UPDATE},
            granted_by="admin",
        )

        # Now user has permission on this specific resource
        assert rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)

        # But not on other resources
        other_resource = Resource(
            resource_type=ResourceType.ASSET, resource_id="asset_456"
        )
        assert not rbac.has_permission(
            "user_1", Permission.ASSET_UPDATE, other_resource
        )

    def test_revoke_resource_access(self):
        """Test revoking resource access"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(resource_type=ResourceType.ASSET, resource_id="asset_123")

        # Grant then revoke
        rbac.grant_resource_access(
            user_id="user_1",
            resource=resource,
            permissions={Permission.ASSET_UPDATE},
            granted_by="admin",
        )
        assert rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)

        rbac.revoke_resource_access(
            user_id="user_1", resource=resource, revoked_by="admin"
        )
        assert not rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)

    def test_owner_permissions(self):
        """Test that resource owners have automatic permissions"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(
            resource_type=ResourceType.ASSET, resource_id="asset_123", owner_id="user_1"
        )

        # Owner has read, update, delete on their own resources
        assert rbac.has_permission("user_1", Permission.ASSET_READ, resource)
        assert rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)
        assert rbac.has_permission("user_1", Permission.ASSET_DELETE, resource)

    def test_non_owner_no_automatic_permissions(self):
        """Test that non-owners don't get automatic permissions"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(
            resource_type=ResourceType.ASSET,
            resource_id="asset_123",
            owner_id="user_2",  # Different owner
        )

        # Non-owner doesn't have update/delete
        assert not rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)
        assert not rbac.has_permission("user_1", Permission.ASSET_DELETE, resource)

    def test_expired_acl_entry(self):
        """Test that expired ACL entries are not honored"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(resource_type=ResourceType.ASSET, resource_id="asset_123")

        # Grant access that expires in the past
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        rbac.grant_resource_access(
            user_id="user_1",
            resource=resource,
            permissions={Permission.ASSET_UPDATE},
            granted_by="admin",
            expires_at=past_time,
        )

        # Permission should be denied due to expiration
        assert not rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)

    def test_future_expiration_acl(self):
        """Test that ACL entries with future expiration work"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.USER, "system")

        resource = Resource(resource_type=ResourceType.ASSET, resource_id="asset_123")

        # Grant access that expires in the future
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        rbac.grant_resource_access(
            user_id="user_1",
            resource=resource,
            permissions={Permission.ASSET_UPDATE},
            granted_by="admin",
            expires_at=future_time,
        )

        # Permission should be granted
        assert rbac.has_permission("user_1", Permission.ASSET_UPDATE, resource)

    def test_get_resource_acl(self):
        """Test getting ACL for a resource"""
        rbac = RBACManager(enable_audit=False)

        resource = Resource(resource_type=ResourceType.ASSET, resource_id="asset_123")

        rbac.grant_resource_access(
            user_id="user_1",
            resource=resource,
            permissions={Permission.ASSET_UPDATE},
            granted_by="admin",
        )

        rbac.grant_resource_access(
            user_id="user_2",
            resource=resource,
            permissions={Permission.ASSET_READ},
            granted_by="admin",
        )

        acl = rbac.get_resource_acl(resource)
        assert len(acl) == 2

        user_ids = {entry.user_id for entry in acl}
        assert "user_1" in user_ids
        assert "user_2" in user_ids


class TestDynamicRoleManagement:
    """Test dynamic role and permission management"""

    def test_add_permission_to_role(self):
        """Test adding new permission to a role"""
        rbac = RBACManager()

        # User role doesn't have delete permission by default
        permissions = rbac.get_role_permissions(UserRole.USER)
        assert Permission.ASSET_DELETE not in permissions

        # Add delete permission to USER role
        rbac.add_permission_to_role(UserRole.USER, Permission.ASSET_DELETE)

        # Now USER role has delete permission
        permissions = rbac.get_role_permissions(UserRole.USER)
        assert Permission.ASSET_DELETE in permissions

    def test_remove_permission_from_role(self):
        """Test removing permission from a role"""
        rbac = RBACManager()

        # Admin has create permission
        permissions = rbac.get_role_permissions(UserRole.ADMIN)
        assert Permission.ASSET_CREATE in permissions

        # Remove create permission from ADMIN
        rbac.remove_permission_from_role(UserRole.ADMIN, Permission.ASSET_CREATE)

        # Now ADMIN doesn't have create permission
        permissions = rbac.get_role_permissions(UserRole.ADMIN)
        assert Permission.ASSET_CREATE not in permissions


class TestAuditLog:
    """Test audit logging functionality"""

    def test_audit_log_enabled(self):
        """Test that audit log records permission checks"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        rbac.has_permission("user_1", Permission.ASSET_CREATE)

        audit_log = rbac.get_audit_log()
        assert len(audit_log) > 0

        # Find the permission check entry
        check_entries = [e for e in audit_log if e.action == "check_permission"]
        assert len(check_entries) > 0

    def test_audit_log_disabled(self):
        """Test that audit log doesn't record when disabled"""
        rbac = RBACManager(enable_audit=False)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        rbac.has_permission("user_1", Permission.ASSET_CREATE)

        audit_log = rbac.get_audit_log()
        assert len(audit_log) == 0

    def test_audit_log_filters(self):
        """Test filtering audit log entries"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")
        rbac.assign_role("user_2", UserRole.USER, "system")

        rbac.has_permission("user_1", Permission.ASSET_CREATE)
        rbac.has_permission("user_2", Permission.ASSET_CREATE)

        # Filter by user
        user1_log = rbac.get_audit_log(user_id="user_1")
        assert all(
            entry.user_id == "user_1" or entry.user_id == "system"
            for entry in user1_log
        )

        # Filter by resource type
        system_log = rbac.get_audit_log(resource_type=ResourceType.SYSTEM)
        assert all(entry.resource_type == ResourceType.SYSTEM for entry in system_log)

    def test_audit_log_limit(self):
        """Test limiting audit log entries"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        # Generate many audit entries
        for i in range(20):
            rbac.has_permission("user_1", Permission.ASSET_CREATE)

        # Get limited entries
        audit_log = rbac.get_audit_log(limit=5)
        assert len(audit_log) <= 5

    def test_export_audit_log(self):
        """Test exporting audit log as JSON"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")
        rbac.has_permission("user_1", Permission.ASSET_CREATE)

        export = rbac.export_audit_log()
        assert isinstance(export, str)
        assert "user_1" in export
        assert "check_permission" in export

    def test_export_audit_log_time_range(self):
        """Test exporting audit log with time range"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")

        start = datetime.now(timezone.utc)
        rbac.has_permission("user_1", Permission.ASSET_CREATE)
        end = datetime.now(timezone.utc)

        export = rbac.export_audit_log(start_time=start, end_time=end)
        assert isinstance(export, str)

    def test_clear_audit_log(self):
        """Test clearing audit log"""
        rbac = RBACManager(enable_audit=True)
        rbac.assign_role("user_1", UserRole.ADMIN, "system")
        rbac.has_permission("user_1", Permission.ASSET_CREATE)

        assert len(rbac.get_audit_log()) > 0

        rbac.clear_audit_log()
        assert len(rbac.get_audit_log()) == 0


class TestComplexScenarios:
    """Test complex real-world scenarios"""

    def test_collaborative_editing(self):
        """Test scenario: Grant temporary editing access to collaborators"""
        rbac = RBACManager(enable_audit=False)

        # Owner creates an asset
        owner_id = "content_creator_1"
        collaborator_id = "user_1"

        rbac.assign_role(owner_id, UserRole.CONTENT_CREATOR, "system")
        rbac.assign_role(collaborator_id, UserRole.USER, "system")

        asset = Resource(
            resource_type=ResourceType.ASSET,
            resource_id="asset_collab",
            owner_id=owner_id,
        )

        # Owner has full control
        assert rbac.has_permission(owner_id, Permission.ASSET_UPDATE, asset)
        assert rbac.has_permission(owner_id, Permission.ASSET_DELETE, asset)

        # Collaborator has no access initially
        assert not rbac.has_permission(collaborator_id, Permission.ASSET_UPDATE, asset)

        # Grant temporary editing access (24 hours)
        expiration = datetime.now(timezone.utc) + timedelta(hours=24)
        rbac.grant_resource_access(
            user_id=collaborator_id,
            resource=asset,
            permissions={Permission.ASSET_UPDATE},
            granted_by=owner_id,
            expires_at=expiration,
        )

        # Collaborator can now edit
        assert rbac.has_permission(collaborator_id, Permission.ASSET_UPDATE, asset)

        # But still can't delete (owner privilege)
        assert not rbac.has_permission(collaborator_id, Permission.ASSET_DELETE, asset)

    def test_moderation_workflow(self):
        """Test scenario: Moderator reviewing user content"""
        rbac = RBACManager(enable_audit=True)

        user_id = "user_1"
        moderator_id = "moderator_1"

        rbac.assign_role(user_id, UserRole.USER, "system")
        rbac.assign_role(moderator_id, UserRole.MODERATOR, "system")

        asset = Resource(
            resource_type=ResourceType.ASSET,
            resource_id="asset_flagged",
            owner_id=user_id,
        )

        # Moderator can read any content
        assert rbac.has_permission(moderator_id, Permission.ASSET_READ, asset)

        # Moderator can update (for moderation purposes)
        assert rbac.has_permission(moderator_id, Permission.ASSET_UPDATE, asset)

        # Moderator can moderate
        assert rbac.has_permission(moderator_id, Permission.MODERATE_CONTENT)

        # User owns their asset
        assert rbac.has_permission(user_id, Permission.ASSET_UPDATE, asset)

    def test_role_hierarchy(self):
        """Test that higher roles have more permissions"""
        rbac = RBACManager()

        super_admin_perms = rbac.get_role_permissions(UserRole.SUPER_ADMIN)
        admin_perms = rbac.get_role_permissions(UserRole.ADMIN)
        moderator_perms = rbac.get_role_permissions(UserRole.MODERATOR)
        user_perms = rbac.get_role_permissions(UserRole.USER)

        # Super admin has most permissions
        assert len(super_admin_perms) >= len(admin_perms)

        # Admin has more than moderator
        assert len(admin_perms) > len(moderator_perms)

        # Moderator has more than user
        assert len(moderator_perms) > len(user_perms)

    def test_multiple_acl_entries_same_resource(self):
        """Test multiple users with different permissions on same resource"""
        rbac = RBACManager(enable_audit=False)

        rbac.assign_role("user_1", UserRole.USER, "system")
        rbac.assign_role("user_2", UserRole.USER, "system")
        rbac.assign_role("user_3", UserRole.USER, "system")

        asset = Resource(
            resource_type=ResourceType.ASSET,
            resource_id="asset_shared",
            owner_id="admin",
        )

        # Grant different permissions to different users
        rbac.grant_resource_access("user_1", asset, {Permission.ASSET_READ}, "admin")
        rbac.grant_resource_access(
            "user_2", asset, {Permission.ASSET_READ, Permission.ASSET_UPDATE}, "admin"
        )
        rbac.grant_resource_access(
            "user_3",
            asset,
            {Permission.ASSET_READ, Permission.ASSET_UPDATE, Permission.ASSET_DELETE},
            "admin",
        )

        # Verify each user has correct permissions
        assert rbac.has_permission("user_1", Permission.ASSET_READ, asset)
        assert not rbac.has_permission("user_1", Permission.ASSET_UPDATE, asset)

        assert rbac.has_permission("user_2", Permission.ASSET_READ, asset)
        assert rbac.has_permission("user_2", Permission.ASSET_UPDATE, asset)
        assert not rbac.has_permission("user_2", Permission.ASSET_DELETE, asset)

        assert rbac.has_permission("user_3", Permission.ASSET_READ, asset)
        assert rbac.has_permission("user_3", Permission.ASSET_UPDATE, asset)
        assert rbac.has_permission("user_3", Permission.ASSET_DELETE, asset)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

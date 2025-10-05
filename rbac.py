"""
Role-Based Access Control (RBAC) Module

Extends the authentication module with comprehensive RBAC capabilities including:
- Fine-grained permission management
- Resource-level access control
- Dynamic role assignments
- Permission inheritance and hierarchies
- Audit trail for access decisions

Issue: #4
Slug: auth-rbac
Priority: P0
"""

from typing import Set, Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json


class UserRole(Enum):
    """User roles in the system"""

    SUPER_ADMIN = "super_admin"
    ADMIN = "admin"
    MODERATOR = "moderator"
    CONTENT_CREATOR = "content_creator"
    USER = "user"
    GUEST = "guest"


class Permission(Enum):
    """System permissions"""

    # Asset permissions
    ASSET_CREATE = "asset:create"
    ASSET_READ = "asset:read"
    ASSET_UPDATE = "asset:update"
    ASSET_DELETE = "asset:delete"
    ASSET_PUBLISH = "asset:publish"

    # User management
    USER_CREATE = "user:create"
    USER_READ = "user:read"
    USER_UPDATE = "user:update"
    USER_DELETE = "user:delete"
    USER_ASSIGN_ROLE = "user:assign_role"

    # Moderation
    MODERATE_CONTENT = "moderate:content"
    MODERATE_USERS = "moderate:users"
    MODERATE_REPORTS = "moderate:reports"

    # Analytics
    ANALYTICS_VIEW = "analytics:view"
    ANALYTICS_EXPORT = "analytics:export"

    # System administration
    SYSTEM_CONFIG = "system:config"
    SYSTEM_AUDIT = "system:audit"
    SYSTEM_MANAGE_ROLES = "system:manage_roles"

    # Publishing
    PUBLISH_GIPHY = "publish:giphy"
    PUBLISH_TENOR = "publish:tenor"
    PUBLISH_SLACK = "publish:slack"
    PUBLISH_DISCORD = "publish:discord"


class ResourceType(Enum):
    """Resource types for access control"""

    ASSET = "asset"
    USER = "user"
    CHANNEL = "channel"
    REPORT = "report"
    ANALYTICS = "analytics"
    SYSTEM = "system"


@dataclass
class Resource:
    """Represents a resource that can be access-controlled"""

    resource_type: ResourceType
    resource_id: str
    owner_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AccessControlEntry:
    """Access control entry for a resource"""

    user_id: str
    resource: Resource
    permissions: Set[Permission]
    granted_at: datetime
    granted_by: str
    expires_at: Optional[datetime] = None


@dataclass
class AuditLogEntry:
    """Audit log entry for access control decisions"""

    timestamp: datetime
    user_id: str
    action: str
    resource_type: ResourceType
    resource_id: str
    permission: Permission
    granted: bool
    reason: str
    metadata: Dict[str, Any] = field(default_factory=dict)


class RBACManager:
    """
    Role-Based Access Control Manager

    Manages roles, permissions, and access control for resources.
    Provides fine-grained permission checking and audit logging.
    """

    def __init__(self, enable_audit: bool = True):
        """
        Initialize RBAC manager

        Args:
            enable_audit: Enable audit logging for access decisions
        """
        self.enable_audit = enable_audit

        # Define default role permissions
        self._role_permissions: Dict[UserRole, Set[Permission]] = {
            UserRole.SUPER_ADMIN: {perm for perm in Permission},  # All permissions
            UserRole.ADMIN: {
                Permission.ASSET_CREATE,
                Permission.ASSET_READ,
                Permission.ASSET_UPDATE,
                Permission.ASSET_DELETE,
                Permission.ASSET_PUBLISH,
                Permission.USER_READ,
                Permission.USER_UPDATE,
                Permission.MODERATE_CONTENT,
                Permission.MODERATE_REPORTS,
                Permission.ANALYTICS_VIEW,
                Permission.ANALYTICS_EXPORT,
                Permission.PUBLISH_GIPHY,
                Permission.PUBLISH_TENOR,
                Permission.PUBLISH_SLACK,
                Permission.PUBLISH_DISCORD,
            },
            UserRole.MODERATOR: {
                Permission.ASSET_READ,
                Permission.ASSET_UPDATE,
                Permission.MODERATE_CONTENT,
                Permission.MODERATE_REPORTS,
                Permission.ANALYTICS_VIEW,
            },
            UserRole.CONTENT_CREATOR: {
                Permission.ASSET_CREATE,
                Permission.ASSET_READ,
                Permission.ASSET_UPDATE,
                Permission.ASSET_PUBLISH,
                Permission.ANALYTICS_VIEW,
                Permission.PUBLISH_GIPHY,
                Permission.PUBLISH_TENOR,
                Permission.PUBLISH_SLACK,
                Permission.PUBLISH_DISCORD,
            },
            UserRole.USER: {
                Permission.ASSET_CREATE,
                Permission.ASSET_READ,
            },
            UserRole.GUEST: {
                Permission.ASSET_READ,
            },
        }

        # User role assignments: user_id -> role
        self._user_roles: Dict[str, UserRole] = {}

        # Resource-specific ACLs: resource_id -> List[AccessControlEntry]
        self._resource_acls: Dict[str, List[AccessControlEntry]] = {}

        # Audit log
        self._audit_log: List[AuditLogEntry] = []

    def assign_role(self, user_id: str, role: UserRole, assigned_by: str) -> None:
        """
        Assign role to user

        Args:
            user_id: User ID
            role: Role to assign
            assigned_by: ID of user assigning the role
        """
        self._user_roles[user_id] = role

        if self.enable_audit:
            self._log_audit(
                user_id=assigned_by,
                action="assign_role",
                resource_type=ResourceType.USER,
                resource_id=user_id,
                permission=Permission.USER_ASSIGN_ROLE,
                granted=True,
                reason=f"Assigned role {role.value}",
                metadata={"new_role": role.value},
            )

    def get_user_role(self, user_id: str) -> Optional[UserRole]:
        """Get user's current role"""
        return self._user_roles.get(user_id)

    def get_role_permissions(self, role: UserRole) -> Set[Permission]:
        """Get all permissions for a role"""
        return self._role_permissions.get(role, set()).copy()

    def add_permission_to_role(self, role: UserRole, permission: Permission) -> None:
        """Add permission to a role"""
        if role not in self._role_permissions:
            self._role_permissions[role] = set()
        self._role_permissions[role].add(permission)

    def remove_permission_from_role(
        self, role: UserRole, permission: Permission
    ) -> None:
        """Remove permission from a role"""
        if role in self._role_permissions:
            self._role_permissions[role].discard(permission)

    def has_permission(
        self, user_id: str, permission: Permission, resource: Optional[Resource] = None
    ) -> bool:
        """
        Check if user has permission

        Args:
            user_id: User ID
            permission: Permission to check
            resource: Optional resource for resource-level access control

        Returns:
            True if user has permission, False otherwise
        """
        # Check role-based permissions
        role = self._user_roles.get(user_id)
        if not role:
            self._log_audit(
                user_id=user_id,
                action="check_permission",
                resource_type=(
                    resource.resource_type if resource else ResourceType.SYSTEM
                ),
                resource_id=resource.resource_id if resource else "system",
                permission=permission,
                granted=False,
                reason="No role assigned",
            )
            return False

        role_permissions = self._role_permissions.get(role, set())
        has_role_permission = permission in role_permissions

        # Check resource-specific ACL if resource provided
        has_resource_permission = False
        if resource:
            has_resource_permission = self._check_resource_acl(
                user_id=user_id, resource=resource, permission=permission
            )

            # Also check if user owns the resource
            if resource.owner_id == user_id:
                # Owners have read, update, and delete permissions on their resources
                owner_permissions = {
                    Permission.ASSET_READ,
                    Permission.ASSET_UPDATE,
                    Permission.ASSET_DELETE,
                }
                has_resource_permission = has_resource_permission or (
                    permission in owner_permissions
                )

        granted = has_role_permission or has_resource_permission

        if self.enable_audit:
            self._log_audit(
                user_id=user_id,
                action="check_permission",
                resource_type=(
                    resource.resource_type if resource else ResourceType.SYSTEM
                ),
                resource_id=resource.resource_id if resource else "system",
                permission=permission,
                granted=granted,
                reason=(
                    "Role permission"
                    if has_role_permission
                    else (
                        "Resource ACL"
                        if has_resource_permission
                        else "Permission denied"
                    )
                ),
                metadata={"role": role.value if role else None},
            )

        return granted

    def require_permission(
        self, user_id: str, permission: Permission, resource: Optional[Resource] = None
    ) -> None:
        """
        Require user to have permission, raise exception if not

        Args:
            user_id: User ID
            permission: Required permission
            resource: Optional resource for resource-level access control

        Raises:
            PermissionDeniedError: If user lacks permission
        """
        if not self.has_permission(user_id, permission, resource):
            raise PermissionDeniedError(
                f"User {user_id} lacks permission: {permission.value}"
            )

    def grant_resource_access(
        self,
        user_id: str,
        resource: Resource,
        permissions: Set[Permission],
        granted_by: str,
        expires_at: Optional[datetime] = None,
    ) -> None:
        """
        Grant specific permissions on a resource to a user

        Args:
            user_id: User ID to grant access to
            resource: Resource to grant access on
            permissions: Set of permissions to grant
            granted_by: ID of user granting access
            expires_at: Optional expiration time for access
        """
        acl_key = f"{resource.resource_type.value}:{resource.resource_id}"

        if acl_key not in self._resource_acls:
            self._resource_acls[acl_key] = []

        # Remove existing ACL entry for this user if exists
        self._resource_acls[acl_key] = [
            entry for entry in self._resource_acls[acl_key] if entry.user_id != user_id
        ]

        # Add new ACL entry
        entry = AccessControlEntry(
            user_id=user_id,
            resource=resource,
            permissions=permissions,
            granted_at=datetime.utcnow(),
            granted_by=granted_by,
            expires_at=expires_at,
        )
        self._resource_acls[acl_key].append(entry)

        if self.enable_audit:
            self._log_audit(
                user_id=granted_by,
                action="grant_resource_access",
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                permission=Permission.SYSTEM_CONFIG,  # Meta permission
                granted=True,
                reason=f"Granted access to user {user_id}",
                metadata={
                    "target_user": user_id,
                    "permissions": [p.value for p in permissions],
                },
            )

    def revoke_resource_access(
        self, user_id: str, resource: Resource, revoked_by: str
    ) -> None:
        """
        Revoke all permissions on a resource from a user

        Args:
            user_id: User ID to revoke access from
            resource: Resource to revoke access on
            revoked_by: ID of user revoking access
        """
        acl_key = f"{resource.resource_type.value}:{resource.resource_id}"

        if acl_key in self._resource_acls:
            self._resource_acls[acl_key] = [
                entry
                for entry in self._resource_acls[acl_key]
                if entry.user_id != user_id
            ]

        if self.enable_audit:
            self._log_audit(
                user_id=revoked_by,
                action="revoke_resource_access",
                resource_type=resource.resource_type,
                resource_id=resource.resource_id,
                permission=Permission.SYSTEM_CONFIG,  # Meta permission
                granted=True,
                reason=f"Revoked access from user {user_id}",
                metadata={"target_user": user_id},
            )

    def _check_resource_acl(
        self, user_id: str, resource: Resource, permission: Permission
    ) -> bool:
        """Check resource-specific ACL"""
        acl_key = f"{resource.resource_type.value}:{resource.resource_id}"

        if acl_key not in self._resource_acls:
            return False

        now = datetime.utcnow()

        for entry in self._resource_acls[acl_key]:
            if entry.user_id != user_id:
                continue

            # Check if ACL entry expired
            if entry.expires_at and now > entry.expires_at:
                continue

            if permission in entry.permissions:
                return True

        return False

    def get_resource_acl(self, resource: Resource) -> List[AccessControlEntry]:
        """Get all ACL entries for a resource"""
        acl_key = f"{resource.resource_type.value}:{resource.resource_id}"
        return self._resource_acls.get(acl_key, []).copy()

    def _log_audit(
        self,
        user_id: str,
        action: str,
        resource_type: ResourceType,
        resource_id: str,
        permission: Permission,
        granted: bool,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Log audit entry"""
        if not self.enable_audit:
            return

        entry = AuditLogEntry(
            timestamp=datetime.utcnow(),
            user_id=user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            permission=permission,
            granted=granted,
            reason=reason,
            metadata=metadata or {},
        )
        self._audit_log.append(entry)

    def get_audit_log(
        self,
        user_id: Optional[str] = None,
        resource_type: Optional[ResourceType] = None,
        limit: int = 100,
    ) -> List[AuditLogEntry]:
        """
        Get audit log entries with optional filters

        Args:
            user_id: Filter by user ID
            resource_type: Filter by resource type
            limit: Maximum entries to return

        Returns:
            List of audit log entries
        """
        entries = self._audit_log.copy()

        if user_id:
            entries = [e for e in entries if e.user_id == user_id]

        if resource_type:
            entries = [e for e in entries if e.resource_type == resource_type]

        # Return most recent first
        entries.reverse()

        return entries[:limit]

    def export_audit_log(
        self, start_time: Optional[datetime] = None, end_time: Optional[datetime] = None
    ) -> str:
        """
        Export audit log as JSON

        Args:
            start_time: Start of time range
            end_time: End of time range

        Returns:
            JSON string of audit log entries
        """
        entries = self._audit_log.copy()

        if start_time:
            entries = [e for e in entries if e.timestamp >= start_time]

        if end_time:
            entries = [e for e in entries if e.timestamp <= end_time]

        serialized = []
        for entry in entries:
            serialized.append(
                {
                    "timestamp": entry.timestamp.isoformat(),
                    "user_id": entry.user_id,
                    "action": entry.action,
                    "resource_type": entry.resource_type.value,
                    "resource_id": entry.resource_id,
                    "permission": entry.permission.value,
                    "granted": entry.granted,
                    "reason": entry.reason,
                    "metadata": entry.metadata,
                }
            )

        return json.dumps(serialized, indent=2)

    def clear_audit_log(self) -> None:
        """Clear audit log (use with caution)"""
        self._audit_log.clear()


class PermissionDeniedError(Exception):
    """Raised when user lacks required permission"""

    pass


# Example usage
if __name__ == "__main__":
    rbac = RBACManager(enable_audit=True)

    # Assign roles to users
    rbac.assign_role("user_1", UserRole.ADMIN, "system")
    rbac.assign_role("user_2", UserRole.CONTENT_CREATOR, "user_1")
    rbac.assign_role("user_3", UserRole.USER, "user_1")

    # Check permissions
    print(
        f"User 1 can create assets: {rbac.has_permission('user_1', Permission.ASSET_CREATE)}"
    )
    print(
        f"User 2 can create assets: {rbac.has_permission('user_2', Permission.ASSET_CREATE)}"
    )
    print(
        f"User 3 can create assets: {rbac.has_permission('user_3', Permission.ASSET_CREATE)}"
    )
    print(
        f"User 3 can moderate: {rbac.has_permission('user_3', Permission.MODERATE_CONTENT)}"
    )

    # Resource-level access control
    asset = Resource(
        resource_type=ResourceType.ASSET, resource_id="asset_123", owner_id="user_2"
    )

    # Grant specific permission to user_3 on this asset
    rbac.grant_resource_access(
        user_id="user_3",
        resource=asset,
        permissions={Permission.ASSET_UPDATE},
        granted_by="user_1",
    )

    # Check resource-specific permission
    print(
        f"User 3 can update asset_123: {rbac.has_permission('user_3', Permission.ASSET_UPDATE, asset)}"
    )

    # Owner permissions
    print(
        f"User 2 (owner) can update asset_123: {rbac.has_permission('user_2', Permission.ASSET_UPDATE, asset)}"
    )

    # View audit log
    print("\nAudit Log:")
    for entry in rbac.get_audit_log(limit=10):
        print(
            f"{entry.timestamp}: {entry.action} - {entry.reason} (granted={entry.granted})"
        )

    # Export audit log
    audit_export = rbac.export_audit_log()
    print(f"\nAudit export:\n{audit_export}")

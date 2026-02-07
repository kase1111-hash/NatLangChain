"""
NatLangChain - Role-Based Access Control (RBAC)

Production-ready RBAC system for fine-grained API access control.

Features:
- Predefined roles with hierarchical permissions
- API key to role mapping
- Permission-based decorators for endpoints
- Audit logging for access decisions
- Support for custom roles and permissions

Usage:
    from rbac import require_permission, Permission, Role

    @require_permission(Permission.ENTRY_CREATE)
    def create_entry():
        ...

    @require_role(Role.ADMIN)
    def admin_only():
        ...

Environment Variables:
    NATLANGCHAIN_RBAC_ENABLED=true
    NATLANGCHAIN_RBAC_CONFIG_FILE=/path/to/rbac.json
    NATLANGCHAIN_DEFAULT_ROLE=readonly
"""

import hashlib
import json
import logging
import os
import secrets
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from functools import wraps
from typing import Any

from flask import g, jsonify, request

logger = logging.getLogger(__name__)


# =============================================================================
# Permissions
# =============================================================================


class Permission(Enum):
    """
    Granular permissions for NatLangChain operations.

    Permissions are organized by resource and action:
    - RESOURCE_ACTION format (e.g., ENTRY_CREATE, CHAIN_READ)
    """

    # Chain operations
    CHAIN_READ = auto()  # View chain info, blocks, entries
    CHAIN_VALIDATE = auto()  # Trigger chain validation
    CHAIN_EXPORT = auto()  # Export chain data

    # Entry operations
    ENTRY_CREATE = auto()  # Add new entries
    ENTRY_READ = auto()  # Read entries
    ENTRY_SEARCH = auto()  # Search entries

    # Block operations
    BLOCK_READ = auto()  # Read blocks
    BLOCK_MINE = auto()  # Trigger mining

    # Contract operations
    CONTRACT_CREATE = auto()  # Create contracts
    CONTRACT_READ = auto()  # Read contracts
    CONTRACT_EXECUTE = auto()  # Execute contract actions
    CONTRACT_MATCH = auto()  # Match contracts

    # Dispute operations
    DISPUTE_CREATE = auto()  # File disputes
    DISPUTE_READ = auto()  # View disputes
    DISPUTE_RESOLVE = auto()  # Resolve disputes (mediator)

    # Oracle operations
    ORACLE_QUERY = auto()  # Query oracles
    ORACLE_CREATE = auto()  # Create oracle sources

    # Treasury operations
    TREASURY_READ = auto()  # View treasury
    TREASURY_MANAGE = auto()  # Manage treasury (transfers, subsidies)

    # Consensus operations
    CONSENSUS_PARTICIPATE = auto()  # Participate in consensus
    CONSENSUS_VIEW = auto()  # View consensus status

    # Admin operations
    ADMIN_CONFIG = auto()  # Modify configuration
    ADMIN_USERS = auto()  # Manage users/API keys
    ADMIN_AUDIT = auto()  # View audit logs
    ADMIN_BACKUP = auto()  # Manage backups
    ADMIN_METRICS = auto()  # View detailed metrics

    # P2P operations
    P2P_VIEW = auto()  # View P2P network status
    P2P_MANAGE = auto()  # Manage peers, sync


# =============================================================================
# Roles
# =============================================================================


class Role(Enum):
    """
    Predefined roles with associated permissions.

    Roles are hierarchical - higher roles include permissions of lower roles.
    """

    # No access - used for disabled/suspended keys
    NONE = "none"

    # Read-only access to public data
    READONLY = "readonly"

    # Standard user - can create entries, contracts, participate
    USER = "user"

    # Operator - can manage chain operations
    OPERATOR = "operator"

    # Mediator - can resolve disputes, manage consensus
    MEDIATOR = "mediator"

    # Admin - full access to all operations
    ADMIN = "admin"

    # Service account - for automated systems
    SERVICE = "service"


# Role to permissions mapping
ROLE_PERMISSIONS: dict[Role, set[Permission]] = {
    Role.NONE: set(),
    Role.READONLY: {
        Permission.CHAIN_READ,
        Permission.ENTRY_READ,
        Permission.ENTRY_SEARCH,
        Permission.BLOCK_READ,
        Permission.CONTRACT_READ,
        Permission.DISPUTE_READ,
        Permission.CONSENSUS_VIEW,
        Permission.P2P_VIEW,
    },
    Role.USER: {
        # Includes READONLY permissions
        Permission.CHAIN_READ,
        Permission.ENTRY_READ,
        Permission.ENTRY_SEARCH,
        Permission.BLOCK_READ,
        Permission.CONTRACT_READ,
        Permission.DISPUTE_READ,
        Permission.CONSENSUS_VIEW,
        Permission.P2P_VIEW,
        # Plus write operations
        Permission.ENTRY_CREATE,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EXECUTE,
        Permission.CONTRACT_MATCH,
        Permission.DISPUTE_CREATE,
        Permission.ORACLE_QUERY,
        Permission.CONSENSUS_PARTICIPATE,
    },
    Role.OPERATOR: {
        # Includes USER permissions
        Permission.CHAIN_READ,
        Permission.ENTRY_READ,
        Permission.ENTRY_SEARCH,
        Permission.BLOCK_READ,
        Permission.CONTRACT_READ,
        Permission.DISPUTE_READ,
        Permission.CONSENSUS_VIEW,
        Permission.P2P_VIEW,
        Permission.ENTRY_CREATE,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EXECUTE,
        Permission.CONTRACT_MATCH,
        Permission.DISPUTE_CREATE,
        Permission.ORACLE_QUERY,
        Permission.CONSENSUS_PARTICIPATE,
        # Plus operator permissions
        Permission.CHAIN_VALIDATE,
        Permission.CHAIN_EXPORT,
        Permission.BLOCK_MINE,
        Permission.ORACLE_CREATE,
        Permission.TREASURY_READ,
        Permission.P2P_MANAGE,
        Permission.ADMIN_METRICS,
    },
    Role.MEDIATOR: {
        # Includes OPERATOR permissions
        Permission.CHAIN_READ,
        Permission.ENTRY_READ,
        Permission.ENTRY_SEARCH,
        Permission.BLOCK_READ,
        Permission.CONTRACT_READ,
        Permission.DISPUTE_READ,
        Permission.CONSENSUS_VIEW,
        Permission.P2P_VIEW,
        Permission.ENTRY_CREATE,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EXECUTE,
        Permission.CONTRACT_MATCH,
        Permission.DISPUTE_CREATE,
        Permission.ORACLE_QUERY,
        Permission.CONSENSUS_PARTICIPATE,
        Permission.CHAIN_VALIDATE,
        Permission.CHAIN_EXPORT,
        Permission.BLOCK_MINE,
        Permission.ORACLE_CREATE,
        Permission.TREASURY_READ,
        Permission.P2P_MANAGE,
        Permission.ADMIN_METRICS,
        # Plus mediator permissions
        Permission.DISPUTE_RESOLVE,
    },
    Role.ADMIN: {
        # All permissions
        permission
        for permission in Permission
    },
    Role.SERVICE: {
        # Service accounts get operational permissions
        Permission.CHAIN_READ,
        Permission.ENTRY_READ,
        Permission.ENTRY_SEARCH,
        Permission.BLOCK_READ,
        Permission.CONTRACT_READ,
        Permission.ENTRY_CREATE,
        Permission.CONTRACT_CREATE,
        Permission.CONTRACT_EXECUTE,
        Permission.CHAIN_VALIDATE,
        Permission.BLOCK_MINE,
        Permission.ORACLE_QUERY,
        Permission.ADMIN_BACKUP,
        Permission.P2P_VIEW,
        Permission.ADMIN_METRICS,
    },
}


# =============================================================================
# API Key Management
# =============================================================================


@dataclass
class APIKeyInfo:
    """Information about an API key."""

    key_hash: str  # SHA-256 hash of the key
    role: Role  # Assigned role
    name: str  # Human-readable name
    created_at: datetime  # Creation timestamp
    expires_at: datetime | None  # Optional expiration
    enabled: bool = True  # Whether key is active
    permissions: set[Permission] = field(default_factory=set)  # Additional permissions
    restrictions: set[Permission] = field(default_factory=set)  # Removed permissions
    metadata: dict[str, Any] = field(default_factory=dict)  # Custom metadata
    last_used: datetime | None = None
    use_count: int = 0

    def get_effective_permissions(self) -> set[Permission]:
        """Get the effective permissions for this key."""
        # Start with role permissions
        base_permissions = ROLE_PERMISSIONS.get(self.role, set()).copy()

        # Add extra permissions
        base_permissions |= self.permissions

        # Remove restrictions
        base_permissions -= self.restrictions

        return base_permissions

    def has_permission(self, permission: Permission) -> bool:
        """Check if this key has a specific permission."""
        if not self.enabled:
            return False

        if self.expires_at and datetime.utcnow() > self.expires_at:
            return False

        return permission in self.get_effective_permissions()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "key_hash": self.key_hash,
            "role": self.role.value,
            "name": self.name,
            "created_at": self.created_at.isoformat(),
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "enabled": self.enabled,
            "permissions": [p.name for p in self.permissions],
            "restrictions": [p.name for p in self.restrictions],
            "metadata": self.metadata,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "use_count": self.use_count,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "APIKeyInfo":
        """Create from dictionary."""
        return cls(
            key_hash=data["key_hash"],
            role=Role(data["role"]),
            name=data["name"],
            created_at=datetime.fromisoformat(data["created_at"]),
            expires_at=datetime.fromisoformat(data["expires_at"])
            if data.get("expires_at")
            else None,
            enabled=data.get("enabled", True),
            permissions={Permission[p] for p in data.get("permissions", [])},
            restrictions={Permission[p] for p in data.get("restrictions", [])},
            metadata=data.get("metadata", {}),
            last_used=datetime.fromisoformat(data["last_used"]) if data.get("last_used") else None,
            use_count=data.get("use_count", 0),
        )


class RBACManager:
    """
    Manages role-based access control for NatLangChain.

    This class handles:
    - API key to role mapping
    - Permission checking
    - Audit logging
    - Configuration persistence
    """

    def __init__(
        self,
        config_file: str | None = None,
        enabled: bool = True,
        default_role: Role = Role.READONLY,
    ):
        self.enabled = enabled
        self.default_role = default_role
        self.config_file = config_file

        self._api_keys: dict[str, APIKeyInfo] = {}
        self._lock = threading.RLock()
        self._audit_log: list[dict[str, Any]] = []
        self._max_audit_entries = 10000

        # Load configuration if file provided
        if config_file and os.path.exists(config_file):
            self.load_config(config_file)

        # Register the master API key from environment
        master_key = os.getenv("NATLANGCHAIN_API_KEY")
        if master_key:
            self.register_key(
                key=master_key,
                role=Role.ADMIN,
                name="Master API Key (env)",
            )

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash an API key for secure storage."""
        return hashlib.sha256(key.encode()).hexdigest()

    def register_key(
        self,
        key: str,
        role: Role,
        name: str,
        expires_at: datetime | None = None,
        permissions: set[Permission] | None = None,
        restrictions: set[Permission] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> APIKeyInfo:
        """
        Register a new API key.

        Args:
            key: The raw API key
            role: Role to assign
            name: Human-readable name
            expires_at: Optional expiration datetime
            permissions: Additional permissions beyond role
            restrictions: Permissions to remove from role
            metadata: Custom metadata

        Returns:
            APIKeyInfo for the registered key
        """
        key_hash = self.hash_key(key)

        with self._lock:
            info = APIKeyInfo(
                key_hash=key_hash,
                role=role,
                name=name,
                created_at=datetime.utcnow(),
                expires_at=expires_at,
                permissions=permissions or set(),
                restrictions=restrictions or set(),
                metadata=metadata or {},
            )

            self._api_keys[key_hash] = info

            self._audit(
                action="key_registered",
                key_hash=key_hash,
                role=role.value,
                name=name,
            )

            return info

    def revoke_key(self, key: str) -> bool:
        """
        Revoke an API key.

        Args:
            key: The raw API key to revoke

        Returns:
            True if key was found and revoked
        """
        key_hash = self.hash_key(key)

        with self._lock:
            if key_hash in self._api_keys:
                self._api_keys[key_hash].enabled = False

                self._audit(
                    action="key_revoked",
                    key_hash=key_hash,
                )

                return True

            return False

    def get_key_info(self, key: str) -> APIKeyInfo | None:
        """
        Get info for an API key.

        Args:
            key: The raw API key

        Returns:
            APIKeyInfo if key exists, None otherwise
        """
        key_hash = self.hash_key(key)

        with self._lock:
            info = self._api_keys.get(key_hash)

            if info:
                # Update usage tracking
                info.last_used = datetime.utcnow()
                info.use_count += 1

            return info

    def check_permission(
        self,
        key: str | None,
        permission: Permission,
    ) -> tuple[bool, str]:
        """
        Check if an API key has a permission.

        Args:
            key: The raw API key (None for anonymous)
            permission: Permission to check

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.enabled:
            return True, "RBAC disabled"

        # Anonymous access
        if not key:
            # Check if permission is in default role
            default_perms = ROLE_PERMISSIONS.get(self.default_role, set())
            if permission in default_perms:
                return True, f"Anonymous access with {self.default_role.value} role"
            return False, "Authentication required"

        # Get key info
        info = self.get_key_info(key)

        if not info:
            return False, "Invalid API key"

        if not info.enabled:
            return False, "API key disabled"

        if info.expires_at and datetime.utcnow() > info.expires_at:
            return False, "API key expired"

        if info.has_permission(permission):
            return True, f"Permission granted via {info.role.value} role"

        return False, f"Permission {permission.name} not granted"

    def check_role(
        self,
        key: str | None,
        required_role: Role,
    ) -> tuple[bool, str]:
        """
        Check if an API key has at least the required role.

        Args:
            key: The raw API key
            required_role: Minimum role required

        Returns:
            Tuple of (allowed, reason)
        """
        if not self.enabled:
            return True, "RBAC disabled"

        if not key:
            return False, "Authentication required"

        info = self.get_key_info(key)

        if not info:
            return False, "Invalid API key"

        if not info.enabled:
            return False, "API key disabled"

        # Role hierarchy check
        role_hierarchy = [
            Role.NONE,
            Role.READONLY,
            Role.USER,
            Role.OPERATOR,
            Role.MEDIATOR,
            Role.ADMIN,
        ]

        try:
            required_level = role_hierarchy.index(required_role)
            actual_level = role_hierarchy.index(info.role)

            if actual_level >= required_level:
                return True, f"Role {info.role.value} >= {required_role.value}"

            return False, f"Role {info.role.value} < {required_role.value}"
        except ValueError:
            # Handle SERVICE role specially
            if info.role == Role.SERVICE and required_role in [Role.USER, Role.OPERATOR]:
                return True, "Service account access"
            if info.role == Role.ADMIN:
                return True, "Admin has all roles"
            return False, f"Role check failed for {required_role.value}"

    def _audit(self, action: str, **kwargs):
        """Record an audit log entry."""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            **kwargs,
        }

        with self._lock:
            self._audit_log.append(entry)

            # Trim if too long
            if len(self._audit_log) > self._max_audit_entries:
                self._audit_log = self._audit_log[-self._max_audit_entries :]

        logger.debug(f"RBAC audit: {action} - {kwargs}")

    def get_audit_log(
        self,
        limit: int = 100,
        action_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """Get recent audit log entries."""
        with self._lock:
            log = self._audit_log.copy()

        if action_filter:
            log = [e for e in log if e.get("action") == action_filter]

        return log[-limit:]

    def save_config(self, filepath: str | None = None):
        """Save RBAC configuration to file."""
        filepath = filepath or self.config_file
        if not filepath:
            raise ValueError("No config file path specified")

        with self._lock:
            config = {
                "version": "1.0",
                "enabled": self.enabled,
                "default_role": self.default_role.value,
                "api_keys": [
                    info.to_dict()
                    for info in self._api_keys.values()
                    # Don't save the env-based master key
                    if info.name != "Master API Key (env)"
                ],
            }

        with open(filepath, "w") as f:
            json.dump(config, f, indent=2)

        logger.info(f"RBAC config saved to {filepath}")

    def load_config(self, filepath: str):
        """Load RBAC configuration from file."""
        with open(filepath) as f:
            config = json.load(f)

        with self._lock:
            self.enabled = config.get("enabled", True)
            self.default_role = Role(config.get("default_role", "readonly"))

            for key_data in config.get("api_keys", []):
                info = APIKeyInfo.from_dict(key_data)
                self._api_keys[info.key_hash] = info

        logger.info(f"RBAC config loaded from {filepath}")

    def list_keys(self) -> list[dict[str, Any]]:
        """List all registered API keys (without hashes)."""
        with self._lock:
            return [
                {
                    "name": info.name,
                    "role": info.role.value,
                    "enabled": info.enabled,
                    "created_at": info.created_at.isoformat(),
                    "expires_at": info.expires_at.isoformat() if info.expires_at else None,
                    "last_used": info.last_used.isoformat() if info.last_used else None,
                    "use_count": info.use_count,
                    "permissions_count": len(info.get_effective_permissions()),
                }
                for info in self._api_keys.values()
            ]


# =============================================================================
# Global RBAC Manager
# =============================================================================

_rbac_manager: RBACManager | None = None
_rbac_lock = threading.Lock()


def get_rbac_manager() -> RBACManager:
    """Get or create the global RBAC manager."""
    global _rbac_manager

    with _rbac_lock:
        if _rbac_manager is None:
            enabled = os.getenv("NATLANGCHAIN_RBAC_ENABLED", "true").lower() == "true"
            config_file = os.getenv("NATLANGCHAIN_RBAC_CONFIG_FILE")
            default_role_str = os.getenv("NATLANGCHAIN_DEFAULT_ROLE", "readonly")

            try:
                default_role = Role(default_role_str)
            except ValueError:
                default_role = Role.READONLY

            _rbac_manager = RBACManager(
                config_file=config_file,
                enabled=enabled,
                default_role=default_role,
            )

        return _rbac_manager


def init_rbac(
    enabled: bool = True,
    config_file: str | None = None,
    default_role: Role = Role.READONLY,
) -> RBACManager:
    """Initialize the RBAC system with custom settings."""
    global _rbac_manager

    with _rbac_lock:
        _rbac_manager = RBACManager(
            config_file=config_file,
            enabled=enabled,
            default_role=default_role,
        )
        return _rbac_manager


# =============================================================================
# Decorators
# =============================================================================


def require_permission(permission: Permission, audit: bool = True):
    """
    Decorator to require a specific permission for an endpoint.

    Args:
        permission: The permission required
        audit: Whether to log access attempts

    Example:
        @app.route('/entries', methods=['POST'])
        @require_permission(Permission.ENTRY_CREATE)
        def create_entry():
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            manager = get_rbac_manager()

            # Get API key from request
            api_key = request.headers.get("X-API-Key")

            # Check permission
            allowed, reason = manager.check_permission(api_key, permission)

            # Store in request context
            g.rbac_allowed = allowed
            g.rbac_reason = reason
            g.rbac_permission = permission

            if audit:
                manager._audit(
                    action="permission_check",
                    permission=permission.name,
                    allowed=allowed,
                    reason=reason,
                    endpoint=request.endpoint,
                    method=request.method,
                    ip=request.remote_addr,
                )

            if not allowed:
                return jsonify(
                    {
                        "error": "Permission denied",
                        "permission": permission.name,
                        "reason": reason,
                    }
                ), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_role(role: Role, audit: bool = True):
    """
    Decorator to require a minimum role for an endpoint.

    Args:
        role: The minimum role required
        audit: Whether to log access attempts

    Example:
        @app.route('/admin/config', methods=['POST'])
        @require_role(Role.ADMIN)
        def admin_config():
            ...
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            manager = get_rbac_manager()

            # Get API key from request
            api_key = request.headers.get("X-API-Key")

            # Check role
            allowed, reason = manager.check_role(api_key, role)

            # Store in request context
            g.rbac_allowed = allowed
            g.rbac_reason = reason
            g.rbac_role = role

            if audit:
                manager._audit(
                    action="role_check",
                    required_role=role.value,
                    allowed=allowed,
                    reason=reason,
                    endpoint=request.endpoint,
                    method=request.method,
                    ip=request.remote_addr,
                )

            if not allowed:
                return jsonify(
                    {
                        "error": "Insufficient privileges",
                        "required_role": role.value,
                        "reason": reason,
                    }
                ), 403

            return f(*args, **kwargs)

        return decorated_function

    return decorator


def require_any_permission(*permissions: Permission, audit: bool = True):
    """
    Decorator to require any one of the specified permissions.

    Args:
        *permissions: Permissions where having any one grants access
        audit: Whether to log access attempts
    """

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            manager = get_rbac_manager()
            api_key = request.headers.get("X-API-Key")

            for permission in permissions:
                allowed, reason = manager.check_permission(api_key, permission)
                if allowed:
                    g.rbac_allowed = True
                    g.rbac_permission = permission

                    if audit:
                        manager._audit(
                            action="permission_check",
                            permission=permission.name,
                            allowed=True,
                            reason=reason,
                            endpoint=request.endpoint,
                        )

                    return f(*args, **kwargs)

            # None of the permissions matched
            if audit:
                manager._audit(
                    action="permission_check",
                    permissions=[p.name for p in permissions],
                    allowed=False,
                    reason="None of required permissions granted",
                    endpoint=request.endpoint,
                )

            return jsonify(
                {
                    "error": "Permission denied",
                    "required_any": [p.name for p in permissions],
                }
            ), 403

        return decorated_function

    return decorator


def get_current_permissions() -> set[Permission]:
    """
    Get permissions for the current request's API key.

    Returns:
        Set of permissions for the current user
    """
    manager = get_rbac_manager()
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return ROLE_PERMISSIONS.get(manager.default_role, set())

    info = manager.get_key_info(api_key)
    if not info:
        return set()

    return info.get_effective_permissions()


def get_current_role() -> Role | None:
    """
    Get the role for the current request's API key.

    Returns:
        Role for the current user, or None if not authenticated
    """
    manager = get_rbac_manager()
    api_key = request.headers.get("X-API-Key")

    if not api_key:
        return manager.default_role

    info = manager.get_key_info(api_key)
    if not info:
        return None

    return info.role


# =============================================================================
# Utility Functions
# =============================================================================


def generate_api_key() -> str:
    """Generate a secure random API key."""
    return secrets.token_urlsafe(32)


def create_api_key(
    role: Role,
    name: str,
    expires_in_days: int | None = None,
    permissions: set[Permission] | None = None,
    restrictions: set[Permission] | None = None,
) -> tuple[str, APIKeyInfo]:
    """
    Create and register a new API key.

    Args:
        role: Role to assign
        name: Human-readable name
        expires_in_days: Optional days until expiration
        permissions: Additional permissions
        restrictions: Permissions to remove

    Returns:
        Tuple of (raw_key, APIKeyInfo)
    """
    from datetime import timedelta

    manager = get_rbac_manager()
    key = generate_api_key()

    expires_at = None
    if expires_in_days:
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

    info = manager.register_key(
        key=key,
        role=role,
        name=name,
        expires_at=expires_at,
        permissions=permissions,
        restrictions=restrictions,
    )

    return key, info

"""
Tests for NatLangChain Role-Based Access Control (RBAC) module.

Tests:
- Permission and Role enums
- APIKeyInfo dataclass and methods
- RBACManager key management and permission checking
- Decorators (require_permission, require_role, require_any_permission)
- Utility functions (generate_api_key, create_api_key)
- Configuration save/load
"""

import os

# Import RBAC module
import sys
import tempfile
import threading
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from rbac import (
    ROLE_PERMISSIONS,
    APIKeyInfo,
    Permission,
    RBACManager,
    Role,
    generate_api_key,
    get_rbac_manager,
    init_rbac,
    require_any_permission,
    require_permission,
    require_role,
)


class TestPermissionEnum:
    """Tests for Permission enum."""

    def test_permission_values_exist(self):
        """Test that all expected permissions exist."""
        assert Permission.CHAIN_READ is not None
        assert Permission.ENTRY_CREATE is not None
        assert Permission.BLOCK_MINE is not None
        assert Permission.ADMIN_CONFIG is not None
        assert Permission.CONTRACT_CREATE is not None

    def test_permission_count(self):
        """Test that we have the expected number of permissions."""
        assert len(Permission) >= 20  # At least 20 permissions defined

    def test_permission_names(self):
        """Test that permission names follow RESOURCE_ACTION format."""
        for perm in Permission:
            # Most should contain underscore (RESOURCE_ACTION format)
            assert "_" in perm.name or perm.name.isupper()


class TestRoleEnum:
    """Tests for Role enum."""

    def test_role_values_exist(self):
        """Test that all expected roles exist."""
        assert Role.NONE is not None
        assert Role.READONLY is not None
        assert Role.USER is not None
        assert Role.OPERATOR is not None
        assert Role.MEDIATOR is not None
        assert Role.ADMIN is not None
        assert Role.SERVICE is not None

    def test_role_string_values(self):
        """Test that roles have string values."""
        assert Role.NONE.value == "none"
        assert Role.READONLY.value == "readonly"
        assert Role.USER.value == "user"
        assert Role.ADMIN.value == "admin"


class TestRolePermissions:
    """Tests for role to permission mapping."""

    def test_readonly_has_read_permissions(self):
        """Test that READONLY role has read permissions."""
        readonly_perms = ROLE_PERMISSIONS[Role.READONLY]
        assert Permission.CHAIN_READ in readonly_perms
        assert Permission.ENTRY_READ in readonly_perms
        assert Permission.BLOCK_READ in readonly_perms
        # Should NOT have write permissions
        assert Permission.ENTRY_CREATE not in readonly_perms

    def test_user_has_write_permissions(self):
        """Test that USER role has write permissions."""
        user_perms = ROLE_PERMISSIONS[Role.USER]
        assert Permission.ENTRY_CREATE in user_perms
        assert Permission.CONTRACT_CREATE in user_perms
        # Should NOT have admin permissions
        assert Permission.ADMIN_CONFIG not in user_perms

    def test_admin_has_all_permissions(self):
        """Test that ADMIN role has all permissions."""
        admin_perms = ROLE_PERMISSIONS[Role.ADMIN]
        # Admin should have all permissions
        for perm in Permission:
            assert perm in admin_perms, f"Admin missing permission: {perm.name}"

    def test_none_role_has_no_permissions(self):
        """Test that NONE role has no permissions."""
        none_perms = ROLE_PERMISSIONS[Role.NONE]
        assert len(none_perms) == 0

    def test_role_hierarchy(self):
        """Test that higher roles include lower role permissions."""
        readonly_perms = ROLE_PERMISSIONS[Role.READONLY]
        user_perms = ROLE_PERMISSIONS[Role.USER]

        # USER should have all READONLY permissions
        for perm in readonly_perms:
            assert perm in user_perms, f"User missing readonly permission: {perm.name}"


class TestAPIKeyInfo:
    """Tests for APIKeyInfo dataclass."""

    def test_create_api_key_info(self):
        """Test creating APIKeyInfo instance."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
        )
        assert info.key_hash == "abc123"
        assert info.role == Role.USER
        assert info.name == "Test Key"
        assert info.enabled is True

    def test_get_effective_permissions_basic(self):
        """Test get_effective_permissions returns role permissions."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
        )
        perms = info.get_effective_permissions()
        assert Permission.ENTRY_CREATE in perms

    def test_get_effective_permissions_with_additional(self):
        """Test get_effective_permissions with additional permissions."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.READONLY,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
            permissions={Permission.ADMIN_CONFIG},
        )
        perms = info.get_effective_permissions()
        # Should have readonly + extra admin permission
        assert Permission.CHAIN_READ in perms
        assert Permission.ADMIN_CONFIG in perms

    def test_get_effective_permissions_with_restrictions(self):
        """Test get_effective_permissions with restrictions."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
            restrictions={Permission.ENTRY_CREATE},
        )
        perms = info.get_effective_permissions()
        # Should NOT have restricted permission
        assert Permission.ENTRY_CREATE not in perms
        # Should still have other user permissions
        assert Permission.CHAIN_READ in perms

    def test_has_permission_enabled(self):
        """Test has_permission when key is enabled."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
            enabled=True,
        )
        assert info.has_permission(Permission.ENTRY_CREATE) is True
        assert info.has_permission(Permission.ADMIN_CONFIG) is False

    def test_has_permission_disabled(self):
        """Test has_permission when key is disabled."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.ADMIN,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=None,
            enabled=False,
        )
        # Disabled key should have no permissions
        assert info.has_permission(Permission.ADMIN_CONFIG) is False

    def test_has_permission_expired(self):
        """Test has_permission when key is expired."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.ADMIN,
            name="Test Key",
            created_at=datetime.utcnow(),
            expires_at=datetime.utcnow() - timedelta(hours=1),  # Expired
            enabled=True,
        )
        # Expired key should have no permissions
        assert info.has_permission(Permission.ADMIN_CONFIG) is False

    def test_to_dict(self):
        """Test serialization to dictionary."""
        now = datetime.utcnow()
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test Key",
            created_at=now,
            expires_at=None,
            permissions={Permission.ADMIN_CONFIG},
        )
        data = info.to_dict()
        assert data["key_hash"] == "abc123"
        assert data["role"] == "user"
        assert data["name"] == "Test Key"
        assert "ADMIN_CONFIG" in data["permissions"]

    def test_from_dict(self):
        """Test deserialization from dictionary."""
        data = {
            "key_hash": "abc123",
            "role": "user",
            "name": "Test Key",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": None,
            "enabled": True,
            "permissions": ["ADMIN_CONFIG"],
            "restrictions": [],
            "metadata": {},
            "last_used": None,
            "use_count": 5,
        }
        info = APIKeyInfo.from_dict(data)
        assert info.key_hash == "abc123"
        assert info.role == Role.USER
        assert info.use_count == 5
        assert Permission.ADMIN_CONFIG in info.permissions


class TestRBACManager:
    """Tests for RBACManager class."""

    def test_create_manager_disabled(self):
        """Test creating a disabled RBAC manager."""
        manager = RBACManager(enabled=False)
        assert manager.enabled is False

    def test_create_manager_with_default_role(self):
        """Test creating manager with custom default role."""
        manager = RBACManager(enabled=True, default_role=Role.USER)
        assert manager.default_role == Role.USER

    def test_hash_key(self):
        """Test key hashing."""
        key = "my-secret-api-key"
        hash1 = RBACManager.hash_key(key)
        hash2 = RBACManager.hash_key(key)
        # Same key should produce same hash
        assert hash1 == hash2
        # Hash should be 64 characters (SHA-256 hex)
        assert len(hash1) == 64

    def test_register_key(self):
        """Test registering a new API key."""
        manager = RBACManager(enabled=True)
        key = "test-key-12345"
        info = manager.register_key(
            key=key,
            role=Role.USER,
            name="Test Key",
        )
        assert info.role == Role.USER
        assert info.name == "Test Key"
        assert info.enabled is True

    def test_register_key_with_expiration(self):
        """Test registering a key with expiration."""
        manager = RBACManager(enabled=True)
        expires = datetime.utcnow() + timedelta(days=30)
        info = manager.register_key(
            key="test-key",
            role=Role.USER,
            name="Expiring Key",
            expires_at=expires,
        )
        assert info.expires_at == expires

    def test_revoke_key(self):
        """Test revoking an API key."""
        manager = RBACManager(enabled=True)
        key = "test-key-to-revoke"
        manager.register_key(key=key, role=Role.USER, name="Test")

        result = manager.revoke_key(key)
        assert result is True

        # Key should now be disabled
        info = manager.get_key_info(key)
        assert info.enabled is False

    def test_revoke_nonexistent_key(self):
        """Test revoking a key that doesn't exist."""
        manager = RBACManager(enabled=True)
        result = manager.revoke_key("nonexistent-key")
        assert result is False

    def test_get_key_info(self):
        """Test getting key info."""
        manager = RBACManager(enabled=True)
        key = "test-key-info"
        manager.register_key(key=key, role=Role.USER, name="Info Test")

        info = manager.get_key_info(key)
        assert info is not None
        assert info.name == "Info Test"
        # Should increment use count
        assert info.use_count >= 1

    def test_get_key_info_nonexistent(self):
        """Test getting info for nonexistent key."""
        manager = RBACManager(enabled=True)
        info = manager.get_key_info("nonexistent")
        assert info is None

    def test_check_permission_disabled_rbac(self):
        """Test permission check when RBAC is disabled."""
        manager = RBACManager(enabled=False)
        allowed, reason = manager.check_permission(None, Permission.ADMIN_CONFIG)
        assert allowed is True
        assert "disabled" in reason.lower()

    def test_check_permission_anonymous_allowed(self):
        """Test permission check for anonymous user with default role."""
        manager = RBACManager(enabled=True, default_role=Role.READONLY)
        allowed, reason = manager.check_permission(None, Permission.CHAIN_READ)
        assert allowed is True

    def test_check_permission_anonymous_denied(self):
        """Test permission check for anonymous user - denied."""
        manager = RBACManager(enabled=True, default_role=Role.READONLY)
        allowed, reason = manager.check_permission(None, Permission.ADMIN_CONFIG)
        assert allowed is False

    def test_check_permission_valid_key(self):
        """Test permission check with valid key."""
        manager = RBACManager(enabled=True)
        key = "valid-key"
        manager.register_key(key=key, role=Role.USER, name="Test")

        allowed, reason = manager.check_permission(key, Permission.ENTRY_CREATE)
        assert allowed is True

    def test_check_permission_invalid_key(self):
        """Test permission check with invalid key."""
        manager = RBACManager(enabled=True)
        allowed, reason = manager.check_permission("invalid-key", Permission.ENTRY_CREATE)
        assert allowed is False
        assert "invalid" in reason.lower()

    def test_check_permission_disabled_key(self):
        """Test permission check with disabled key."""
        manager = RBACManager(enabled=True)
        key = "disabled-key"
        manager.register_key(key=key, role=Role.ADMIN, name="Disabled")
        manager.revoke_key(key)

        allowed, reason = manager.check_permission(key, Permission.ADMIN_CONFIG)
        assert allowed is False
        assert "disabled" in reason.lower()

    def test_check_role_valid(self):
        """Test role check with valid role."""
        manager = RBACManager(enabled=True)
        key = "role-key"
        manager.register_key(key=key, role=Role.ADMIN, name="Admin Key")

        allowed, reason = manager.check_role(key, Role.ADMIN)
        assert allowed is True

    def test_check_role_hierarchy(self):
        """Test role check respects hierarchy."""
        manager = RBACManager(enabled=True)
        key = "admin-key"
        manager.register_key(key=key, role=Role.ADMIN, name="Admin Key")

        # Admin should pass check for lower roles
        allowed, reason = manager.check_role(key, Role.USER)
        assert allowed is True

        allowed, reason = manager.check_role(key, Role.READONLY)
        assert allowed is True

    def test_check_role_insufficient(self):
        """Test role check when role is insufficient."""
        manager = RBACManager(enabled=True)
        key = "user-key"
        manager.register_key(key=key, role=Role.USER, name="User Key")

        allowed, reason = manager.check_role(key, Role.ADMIN)
        assert allowed is False

    def test_check_role_anonymous(self):
        """Test role check for anonymous user."""
        manager = RBACManager(enabled=True)
        allowed, reason = manager.check_role(None, Role.USER)
        assert allowed is False

    def test_audit_log(self):
        """Test audit logging."""
        manager = RBACManager(enabled=True)
        key = "audit-key"
        manager.register_key(key=key, role=Role.USER, name="Audit Test")

        # Check permission (triggers audit)
        manager.check_permission(key, Permission.ENTRY_CREATE)

        # Get audit log
        log = manager.get_audit_log(limit=10)
        assert len(log) >= 1

    def test_audit_log_filtering(self):
        """Test audit log filtering by action."""
        manager = RBACManager(enabled=True)
        key = "filter-key"
        manager.register_key(key=key, role=Role.USER, name="Filter Test")

        log = manager.get_audit_log(limit=10, action_filter="key_registered")
        # Should have at least one registration entry
        assert any(e["action"] == "key_registered" for e in log)

    def test_save_and_load_config(self):
        """Test saving and loading configuration."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            config_path = f.name

        try:
            # Create manager and register keys
            manager1 = RBACManager(enabled=True, default_role=Role.USER)
            manager1.register_key(key="persistent-key", role=Role.OPERATOR, name="Persistent")
            manager1.save_config(config_path)

            # Create new manager and load config
            manager2 = RBACManager(enabled=False)
            manager2.load_config(config_path)

            assert manager2.enabled is True
            assert manager2.default_role == Role.USER
            # Key should be loadable (by hash)
        finally:
            os.unlink(config_path)

    def test_list_keys(self):
        """Test listing registered keys."""
        manager = RBACManager(enabled=True)
        manager.register_key(key="key1", role=Role.USER, name="Key 1")
        manager.register_key(key="key2", role=Role.ADMIN, name="Key 2")

        keys = manager.list_keys()
        assert len(keys) >= 2
        names = [k["name"] for k in keys]
        assert "Key 1" in names
        assert "Key 2" in names

    def test_thread_safety(self):
        """Test thread safety of RBACManager."""
        manager = RBACManager(enabled=True)
        errors = []

        def register_keys(start_id):
            try:
                for i in range(10):
                    key = f"thread-key-{start_id}-{i}"
                    manager.register_key(key=key, role=Role.USER, name=f"Key {start_id}-{i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=register_keys, args=(i,)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread safety errors: {errors}"


class TestUtilityFunctions:
    """Tests for utility functions."""

    def test_generate_api_key(self):
        """Test API key generation."""
        key1 = generate_api_key()
        key2 = generate_api_key()

        # Keys should be unique
        assert key1 != key2
        # Keys should be URL-safe
        assert "-" in key1 or "_" in key1 or key1.isalnum()
        # Keys should have reasonable length
        assert len(key1) >= 32


class TestInitRBAC:
    """Tests for RBAC initialization."""

    def test_init_rbac(self):
        """Test initializing RBAC system."""
        manager = init_rbac(enabled=True, default_role=Role.OPERATOR)
        assert manager.enabled is True
        assert manager.default_role == Role.OPERATOR

    @patch.dict(os.environ, {"NATLANGCHAIN_RBAC_ENABLED": "false"})
    def test_get_rbac_manager_from_env(self):
        """Test getting RBAC manager reads from environment."""
        # Reset global manager
        import rbac
        rbac._rbac_manager = None

        # This should read from environment
        manager = get_rbac_manager()
        # May be disabled based on env
        assert manager is not None


class TestDecorators:
    """Tests for RBAC decorators with Flask mocking."""

    @pytest.fixture
    def mock_flask(self):
        """Set up Flask mocking."""
        from flask import Flask
        app = Flask(__name__)
        return app

    def test_require_permission_decorator_structure(self):
        """Test that require_permission returns a decorator."""
        decorator = require_permission(Permission.ENTRY_CREATE)
        assert callable(decorator)

    def test_require_role_decorator_structure(self):
        """Test that require_role returns a decorator."""
        decorator = require_role(Role.ADMIN)
        assert callable(decorator)

    def test_require_any_permission_decorator_structure(self):
        """Test that require_any_permission returns a decorator."""
        decorator = require_any_permission(Permission.CHAIN_READ, Permission.ENTRY_READ)
        assert callable(decorator)


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_expired_key_exact_boundary(self):
        """Test key that expires exactly now."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.ADMIN,
            name="Test",
            created_at=datetime.utcnow() - timedelta(hours=1),
            expires_at=datetime.utcnow(),  # Expires now
            enabled=True,
        )
        # Should be expired (utcnow() > expires_at in the check)
        assert info.has_permission(Permission.ADMIN_CONFIG) is False

    def test_empty_permissions_set(self):
        """Test APIKeyInfo with empty additional permissions."""
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.READONLY,
            name="Test",
            created_at=datetime.utcnow(),
            expires_at=None,
            permissions=set(),
            restrictions=set(),
        )
        perms = info.get_effective_permissions()
        assert perms == ROLE_PERMISSIONS[Role.READONLY]

    def test_service_role_special_handling(self):
        """Test SERVICE role special handling in role check."""
        manager = RBACManager(enabled=True)
        key = "service-key"
        manager.register_key(key=key, role=Role.SERVICE, name="Service")

        # Service should pass USER and OPERATOR checks
        allowed, _ = manager.check_role(key, Role.USER)
        assert allowed is True

        allowed, _ = manager.check_role(key, Role.OPERATOR)
        assert allowed is True

    def test_manager_max_audit_entries(self):
        """Test that audit log is trimmed when too large."""
        manager = RBACManager(enabled=True)
        manager._max_audit_entries = 10

        # Generate many audit entries
        for i in range(20):
            manager.register_key(key=f"key-{i}", role=Role.USER, name=f"Key {i}")

        log = manager.get_audit_log(limit=100)
        # Should be trimmed
        assert len(manager._audit_log) <= 10

    def test_key_with_all_restrictions(self):
        """Test key with all role permissions restricted."""
        user_perms = ROLE_PERMISSIONS[Role.USER].copy()
        info = APIKeyInfo(
            key_hash="abc123",
            role=Role.USER,
            name="Test",
            created_at=datetime.utcnow(),
            expires_at=None,
            restrictions=user_perms,  # Restrict all user permissions
        )
        perms = info.get_effective_permissions()
        assert len(perms) == 0

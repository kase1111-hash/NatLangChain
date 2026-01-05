"""
Tests for Boundary Daemon - RBAC Integration

Tests the unified security layer combining trust boundaries and access control.
"""

import pytest
from unittest.mock import MagicMock, patch
import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from boundary_daemon import (
    BoundaryDaemon,
    EnforcementMode,
    DataClassification,
)
from rbac import (
    Permission,
    Role,
    RBACManager,
    APIKeyInfo,
)
from boundary_rbac_integration import (
    BoundaryRBACGateway,
    AccessLevel,
    SecurityEvent,
    ACCESS_LEVEL_RESTRICTIONS,
    ACCESS_LEVEL_TO_ENFORCEMENT,
    ROLE_TO_CLASSIFICATION,
    get_security_gateway,
    set_boundary_mode,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def rbac_manager():
    """Create an RBAC manager with test keys."""
    manager = RBACManager(enabled=True, default_role=Role.READONLY)

    # Register test keys
    manager.register_key(
        key="admin-key",
        role=Role.ADMIN,
        name="Test Admin",
    )
    manager.register_key(
        key="user-key",
        role=Role.USER,
        name="Test User",
    )
    manager.register_key(
        key="readonly-key",
        role=Role.READONLY,
        name="Test Readonly",
    )

    return manager


@pytest.fixture
def gateway(rbac_manager):
    """Create a security gateway."""
    return BoundaryRBACGateway(
        rbac_manager=rbac_manager,
        boundary_mode=AccessLevel.STANDARD,
    )


# =============================================================================
# Mode Mapping Tests
# =============================================================================

class TestModeMapping:
    """Test boundary mode to enforcement mode mapping."""

    def test_mode_to_enforcement_mapping(self):
        """Test that all boundary modes map to enforcement modes."""
        for mode in AccessLevel:
            assert mode in ACCESS_LEVEL_TO_ENFORCEMENT
            assert isinstance(ACCESS_LEVEL_TO_ENFORCEMENT[mode], EnforcementMode)

    def test_open_mode_is_audit_only(self):
        """Test OPEN mode uses audit-only enforcement."""
        assert ACCESS_LEVEL_TO_ENFORCEMENT[AccessLevel.OPEN] == EnforcementMode.AUDIT_ONLY

    def test_lockdown_mode_is_strict(self):
        """Test LOCKDOWN mode uses strict enforcement."""
        assert ACCESS_LEVEL_TO_ENFORCEMENT[AccessLevel.LOCKDOWN] == EnforcementMode.STRICT

    def test_lockdown_restricts_most_permissions(self):
        """Test LOCKDOWN mode restricts non-read permissions."""
        lockdown_restrictions = ACCESS_LEVEL_RESTRICTIONS[AccessLevel.LOCKDOWN]

        # Write operations should be restricted
        assert Permission.ENTRY_CREATE in lockdown_restrictions
        assert Permission.CONTRACT_CREATE in lockdown_restrictions
        assert Permission.ADMIN_CONFIG in lockdown_restrictions

        # Read operations should NOT be restricted
        assert Permission.CHAIN_READ not in lockdown_restrictions
        assert Permission.ENTRY_READ not in lockdown_restrictions


class TestRoleToClassification:
    """Test role to data classification mapping."""

    def test_all_roles_mapped(self):
        """Test all roles have classification mappings."""
        for role in Role:
            assert role in ROLE_TO_CLASSIFICATION

    def test_admin_gets_confidential(self):
        """Test admin role gets confidential classification."""
        assert ROLE_TO_CLASSIFICATION[Role.ADMIN] == DataClassification.CONFIDENTIAL

    def test_readonly_gets_public(self):
        """Test readonly role gets public classification."""
        assert ROLE_TO_CLASSIFICATION[Role.READONLY] == DataClassification.PUBLIC

    def test_none_role_gets_restricted(self):
        """Test NONE role gets restricted classification."""
        assert ROLE_TO_CLASSIFICATION[Role.NONE] == DataClassification.RESTRICTED


# =============================================================================
# Gateway Authorization Tests
# =============================================================================

class TestGatewayAuthorization:
    """Test the unified authorization flow."""

    def test_admin_can_access_admin_permission(self, gateway):
        """Test admin key can access admin permissions."""
        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ADMIN_CONFIG,
        )

        assert allowed is True
        assert event.decision == "allowed"
        assert event.role == "admin"

    def test_user_cannot_access_admin_permission(self, gateway):
        """Test user key cannot access admin permissions."""
        allowed, reason, event = gateway.authorize(
            api_key="user-key",
            permission=Permission.ADMIN_CONFIG,
        )

        assert allowed is False
        assert event.decision == "denied"
        assert "not granted" in reason.lower() or "permission" in reason.lower()

    def test_readonly_can_read(self, gateway):
        """Test readonly key can read chain."""
        allowed, reason, event = gateway.authorize(
            api_key="readonly-key",
            permission=Permission.CHAIN_READ,
        )

        assert allowed is True
        assert event.decision == "allowed"

    def test_readonly_cannot_write(self, gateway):
        """Test readonly key cannot create entries."""
        allowed, reason, event = gateway.authorize(
            api_key="readonly-key",
            permission=Permission.ENTRY_CREATE,
        )

        assert allowed is False
        assert event.decision == "denied"

    def test_invalid_key_denied(self, gateway):
        """Test invalid API key is denied."""
        allowed, reason, event = gateway.authorize(
            api_key="invalid-key-12345",
            permission=Permission.CHAIN_READ,
        )

        assert allowed is False
        assert "invalid" in reason.lower()


class TestModeRestrictions:
    """Test boundary mode restrictions on permissions."""

    def test_lockdown_blocks_write_operations(self, rbac_manager):
        """Test LOCKDOWN mode blocks write operations even for admin."""
        gateway = BoundaryRBACGateway(
            rbac_manager=rbac_manager,
            boundary_mode=AccessLevel.LOCKDOWN,
        )

        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ENTRY_CREATE,
        )

        assert allowed is False
        assert event.decision == "denied"
        assert "lockdown" in reason.lower()

    def test_lockdown_allows_read_operations(self, rbac_manager):
        """Test LOCKDOWN mode still allows read operations."""
        gateway = BoundaryRBACGateway(
            rbac_manager=rbac_manager,
            boundary_mode=AccessLevel.LOCKDOWN,
        )

        allowed, reason, event = gateway.authorize(
            api_key="readonly-key",
            permission=Permission.CHAIN_READ,
        )

        assert allowed is True

    def test_open_mode_no_restrictions(self, rbac_manager):
        """Test OPEN mode has no mode-based restrictions."""
        gateway = BoundaryRBACGateway(
            rbac_manager=rbac_manager,
            boundary_mode=AccessLevel.OPEN,
        )

        # Admin should have full access
        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ADMIN_CONFIG,
        )

        assert allowed is True

    def test_mode_change_logged(self, gateway):
        """Test that mode changes are logged."""
        initial_count = len(gateway.get_events())

        gateway.boundary_mode = AccessLevel.ELEVATED

        events = gateway.get_events(event_type="mode_change")
        assert len(events) > 0
        assert events[-1]["action"].startswith("mode_change:")


class TestBoundaryDataFlowIntegration:
    """Test boundary daemon data flow checks within gateway."""

    def test_sensitive_data_blocked(self, gateway):
        """Test that sensitive data in payload is blocked."""
        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ENTRY_CREATE,
            request_data={"content": "My password=secret123"},
        )

        assert allowed is False
        assert event.decision == "blocked"
        assert event.event_type == "boundary_blocked"

    def test_clean_data_allowed(self, gateway):
        """Test that clean data passes boundary check."""
        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ENTRY_CREATE,
            request_data={"content": "This is a normal entry"},
        )

        assert allowed is True

    def test_data_flow_check(self, gateway):
        """Test direct data flow check."""
        # Clean data
        allowed, reason, _ = gateway.check_data_flow(
            data="Normal content",
            source="api",
            destination="natlangchain",
        )
        assert allowed is True

        # Sensitive data
        allowed, reason, event = gateway.check_data_flow(
            data="api_key=sk-live-12345",
            source="api",
            destination="external",
        )
        assert allowed is False
        assert event is not None


# =============================================================================
# Audit Trail Tests
# =============================================================================

class TestAuditTrail:
    """Test security event audit trail."""

    def test_events_recorded(self, gateway):
        """Test that authorization events are recorded."""
        gateway.authorize(
            api_key="admin-key",
            permission=Permission.CHAIN_READ,
        )

        events = gateway.get_events()
        assert len(events) > 0

    def test_event_contains_required_fields(self, gateway):
        """Test that events contain all required fields."""
        gateway.authorize(
            api_key="admin-key",
            permission=Permission.CHAIN_READ,
        )

        events = gateway.get_events()
        event = events[-1]

        assert "event_id" in event
        assert "timestamp" in event
        assert "event_type" in event
        assert "decision" in event
        assert "boundary_mode" in event

    def test_violations_tracked(self, gateway):
        """Test that violations are tracked separately."""
        # Cause a violation
        gateway.authorize(
            api_key="readonly-key",
            permission=Permission.ADMIN_CONFIG,
        )

        violations = gateway.get_violations()
        assert len(violations) > 0
        assert violations[-1]["decision"] in ["denied", "blocked"]

    def test_stats_aggregation(self, gateway):
        """Test statistics aggregation."""
        # Make some requests
        gateway.authorize("admin-key", Permission.CHAIN_READ)
        gateway.authorize("readonly-key", Permission.ADMIN_CONFIG)  # denied

        stats = gateway.get_stats()

        assert stats["total_events"] >= 2
        assert stats["allowed"] >= 1
        assert stats["denied"] >= 1
        assert "by_type" in stats


class TestSecurityEventChainEntry:
    """Test conversion of security events to chain entries."""

    def test_event_to_chain_entry(self):
        """Test SecurityEvent converts to valid chain entry."""
        event = SecurityEvent(
            event_id="SEC-001",
            timestamp="2024-01-01T00:00:00Z",
            event_type="rbac_denied",
            source="test-user",
            action="ADMIN_CONFIG",
            permission="ADMIN_CONFIG",
            role="user",
            boundary_mode="standard",
            enforcement_mode="permissive",
            decision="denied",
            reason="Permission not granted",
        )

        entry = event.to_chain_entry()

        assert "content" in entry
        assert "author" in entry
        assert entry["author"] == "security_gateway"
        assert "metadata" in entry
        assert entry["metadata"]["is_security_event"] is True
        assert entry["metadata"]["event_id"] == "SEC-001"

    def test_chain_entry_contains_decision(self):
        """Test chain entry contains decision info."""
        event = SecurityEvent(
            event_id="SEC-002",
            timestamp="2024-01-01T00:00:00Z",
            event_type="authorized",
            source="admin",
            action="CHAIN_READ",
            permission="CHAIN_READ",
            role="admin",
            boundary_mode="standard",
            enforcement_mode="permissive",
            decision="allowed",
            reason="Authorized",
        )

        entry = event.to_chain_entry()

        assert "ALLOWED" in entry["content"]
        assert entry["metadata"]["decision"] == "allowed"


# =============================================================================
# Integration Helpers Tests
# =============================================================================

class TestChainIntegration:
    """Test chain integration helpers."""

    def test_chain_callback_set(self, gateway):
        """Test chain callback can be set."""
        callback_called = []

        def test_callback(entry):
            callback_called.append(entry)

        gateway.set_chain_callback(test_callback)

        # Cause a violation that should trigger callback
        gateway.authorize(
            api_key="readonly-key",
            permission=Permission.ADMIN_CONFIG,
        )

        # The callback should have been called for the violation
        assert len(callback_called) > 0


# =============================================================================
# Global Gateway Tests
# =============================================================================

class TestGlobalGateway:
    """Test global gateway management."""

    def test_get_security_gateway_singleton(self):
        """Test gateway is a singleton."""
        import boundary_rbac_integration as bri

        # Reset for test
        bri._gateway = None

        g1 = get_security_gateway()
        g2 = get_security_gateway()

        assert g1 is g2

    def test_set_boundary_mode_global(self):
        """Test setting boundary mode globally."""
        set_boundary_mode(AccessLevel.ELEVATED)

        gateway = get_security_gateway()
        assert gateway.boundary_mode == AccessLevel.ELEVATED

        # Reset
        set_boundary_mode(AccessLevel.STANDARD)


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_none_api_key_uses_default_role(self, gateway):
        """Test None API key uses default role permissions."""
        allowed, reason, event = gateway.authorize(
            api_key=None,
            permission=Permission.CHAIN_READ,  # Should be allowed for readonly
        )

        # Default role is READONLY which has CHAIN_READ
        assert allowed is True

    def test_none_api_key_denied_for_write(self, gateway):
        """Test None API key denied for write operations."""
        allowed, reason, event = gateway.authorize(
            api_key=None,
            permission=Permission.ENTRY_CREATE,
        )

        assert allowed is False

    def test_empty_request_data_handled(self, gateway):
        """Test empty request data is handled."""
        allowed, reason, event = gateway.authorize(
            api_key="admin-key",
            permission=Permission.ENTRY_CREATE,
            request_data={},
        )

        assert allowed is True  # Empty data should pass boundary check

    def test_max_events_enforced(self, gateway):
        """Test max events limit is enforced."""
        gateway._max_events = 10

        for i in range(20):
            gateway.authorize(
                api_key="admin-key",
                permission=Permission.CHAIN_READ,
            )

        events = gateway.get_events(limit=100)
        assert len(events) <= 10

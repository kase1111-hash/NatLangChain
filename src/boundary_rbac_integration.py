"""
NatLangChain - Boundary Daemon RBAC Integration

Integrates the boundary-daemon trust enforcement layer with NatLangChain's
role-based access control system.

Features:
- RBAC decisions routed through boundary-daemon policies
- Audit events fed to boundary-daemon's hash chain
- Boundary modes control API access levels
- Unified security layer for both trust and access control

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │                   API Request                           │
    └─────────────────────┬───────────────────────────────────┘
                          │
    ┌─────────────────────▼───────────────────────────────────┐
    │              BoundaryRBACGateway                        │
    │  ┌──────────────────┐  ┌──────────────────────────────┐ │
    │  │  Boundary Daemon │◄─┤  RBAC Manager                │ │
    │  │  (Trust Layer)   │  │  (Access Control)            │ │
    │  │                  │  │                              │ │
    │  │  - Data flow     │  │  - Role verification         │ │
    │  │  - Sensitive     │  │  - Permission checks         │ │
    │  │    patterns      │  │  - API key management        │ │
    │  │  - Enforcement   │  │                              │ │
    │  │    modes         │  │                              │ │
    │  └────────┬─────────┘  └──────────────┬───────────────┘ │
    │           │                           │                 │
    │           └───────────┬───────────────┘                 │
    │                       │                                 │
    │           ┌───────────▼───────────┐                     │
    │           │    Unified Audit      │                     │
    │           │    (Hash Chain)       │                     │
    │           └───────────────────────┘                     │
    └─────────────────────────────────────────────────────────┘

Usage:
    from boundary_rbac_integration import (
        get_security_gateway,
        require_boundary_permission,
        BoundaryMode,
    )

    # Decorator usage
    @require_boundary_permission(Permission.ENTRY_CREATE)
    def create_entry():
        ...

    # Manual authorization
    gateway = get_security_gateway()
    result = gateway.authorize(request, api_key, Permission.ENTRY_CREATE)

Environment Variables:
    NATLANGCHAIN_BOUNDARY_MODE=strict  # strict, permissive, audit_only
    NATLANGCHAIN_SECURITY_UNIFIED=true # Enable unified security layer
"""

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable

from flask import g, jsonify, request

# Import boundary daemon
from boundary_daemon import (
    AuditRecord,
    BoundaryDaemon,
    BoundaryPolicy,
    DataClassification,
    EnforcementMode,
    PolicyViolation,
    ViolationType,
)

# Import RBAC
from rbac import (
    APIKeyInfo,
    Permission,
    Role,
    RBACManager,
    ROLE_PERMISSIONS,
    get_rbac_manager,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Boundary Mode to RBAC Role Mapping
# =============================================================================

class BoundaryMode(Enum):
    """
    Boundary modes that control overall API access levels.

    These map to enforcement strictness and available operations.
    """
    OPEN = "open"              # Development mode, minimal restrictions
    STANDARD = "standard"      # Normal operation, standard policies
    ELEVATED = "elevated"      # Heightened security, additional checks
    RESTRICTED = "restricted"  # Limited operations, high-value protection
    LOCKDOWN = "lockdown"      # Emergency mode, minimal operations


# Map boundary modes to RBAC restrictions
MODE_PERMISSION_RESTRICTIONS: dict[BoundaryMode, set[Permission]] = {
    BoundaryMode.OPEN: set(),  # No restrictions
    BoundaryMode.STANDARD: set(),  # Normal operation
    BoundaryMode.ELEVATED: {
        Permission.ADMIN_CONFIG,
        Permission.TREASURY_MANAGE,
    },
    BoundaryMode.RESTRICTED: {
        Permission.ADMIN_CONFIG,
        Permission.ADMIN_USERS,
        Permission.TREASURY_MANAGE,
        Permission.CONTRACT_CREATE,
        Permission.DISPUTE_RESOLVE,
        Permission.P2P_MANAGE,
    },
    BoundaryMode.LOCKDOWN: {
        # In lockdown, only allow read operations
        permission for permission in Permission
        if not permission.name.endswith('_READ') and permission != Permission.CHAIN_VALIDATE
    },
}

# Map boundary modes to enforcement modes
MODE_TO_ENFORCEMENT: dict[BoundaryMode, EnforcementMode] = {
    BoundaryMode.OPEN: EnforcementMode.AUDIT_ONLY,
    BoundaryMode.STANDARD: EnforcementMode.PERMISSIVE,
    BoundaryMode.ELEVATED: EnforcementMode.STRICT,
    BoundaryMode.RESTRICTED: EnforcementMode.STRICT,
    BoundaryMode.LOCKDOWN: EnforcementMode.STRICT,
}

# Map roles to data classifications
ROLE_TO_CLASSIFICATION: dict[Role, DataClassification] = {
    Role.NONE: DataClassification.RESTRICTED,
    Role.READONLY: DataClassification.PUBLIC,
    Role.USER: DataClassification.INTERNAL,
    Role.OPERATOR: DataClassification.INTERNAL,
    Role.MEDIATOR: DataClassification.CONFIDENTIAL,
    Role.ADMIN: DataClassification.CONFIDENTIAL,
    Role.SERVICE: DataClassification.INTERNAL,
}


# =============================================================================
# Unified Security Event
# =============================================================================

@dataclass
class SecurityEvent:
    """Unified security event for audit trail."""

    event_id: str
    timestamp: str
    event_type: str  # rbac_check, boundary_check, combined_auth
    source: str      # IP, agent_id, api_key_name
    action: str      # The operation attempted
    permission: str | None
    role: str | None
    boundary_mode: str
    enforcement_mode: str
    decision: str    # allowed, denied, blocked
    reason: str
    data_classification: str | None = None
    violation_id: str | None = None
    request_hash: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_chain_entry(self) -> dict[str, Any]:
        """Convert to a NatLangChain entry for the audit trail."""
        decision_text = "ALLOWED" if self.decision == "allowed" else "DENIED"

        content = (
            f"Security Event [{self.event_id}]: {self.event_type} - {decision_text}. "
            f"Source: {self.source}. Action: {self.action}. "
            f"Mode: {self.boundary_mode}/{self.enforcement_mode}. "
            f"Reason: {self.reason}."
        )

        return {
            "content": content,
            "author": "security_gateway",
            "intent": "Record security decision",
            "metadata": {
                "is_security_event": True,
                "event_id": self.event_id,
                "event_type": self.event_type,
                "decision": self.decision,
                "permission": self.permission,
                "role": self.role,
                "boundary_mode": self.boundary_mode,
                "timestamp": self.timestamp,
            }
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "source": self.source,
            "action": self.action,
            "permission": self.permission,
            "role": self.role,
            "boundary_mode": self.boundary_mode,
            "enforcement_mode": self.enforcement_mode,
            "decision": self.decision,
            "reason": self.reason,
            "data_classification": self.data_classification,
            "violation_id": self.violation_id,
            "request_hash": self.request_hash,
            "metadata": self.metadata,
        }


# =============================================================================
# Boundary RBAC Gateway
# =============================================================================

class BoundaryRBACGateway:
    """
    Unified security gateway combining boundary-daemon and RBAC.

    This gateway:
    1. Checks RBAC permissions for the API key/role
    2. Applies boundary-daemon policies for data flow
    3. Enforces mode-based restrictions
    4. Maintains unified audit trail
    """

    def __init__(
        self,
        rbac_manager: RBACManager | None = None,
        boundary_daemon: BoundaryDaemon | None = None,
        boundary_mode: BoundaryMode = BoundaryMode.STANDARD,
    ):
        self._rbac = rbac_manager or get_rbac_manager()
        self._boundary_mode = boundary_mode
        self._enforcement_mode = MODE_TO_ENFORCEMENT[boundary_mode]

        self._daemon = boundary_daemon or BoundaryDaemon(
            enforcement_mode=self._enforcement_mode
        )

        self._event_counter = 0
        self._events: list[SecurityEvent] = []
        self._lock = threading.RLock()
        self._max_events = 10000

        # Chain entry callback (set by integration)
        self._chain_callback: Callable[[dict], None] | None = None

        logger.info(
            f"Security gateway initialized: mode={boundary_mode.value}, "
            f"enforcement={self._enforcement_mode.value}"
        )

    @property
    def boundary_mode(self) -> BoundaryMode:
        """Get current boundary mode."""
        return self._boundary_mode

    @boundary_mode.setter
    def boundary_mode(self, mode: BoundaryMode):
        """Set boundary mode and update enforcement."""
        with self._lock:
            old_mode = self._boundary_mode
            self._boundary_mode = mode
            self._enforcement_mode = MODE_TO_ENFORCEMENT[mode]

            # Update daemon enforcement mode
            self._daemon = BoundaryDaemon(
                enforcement_mode=self._enforcement_mode
            )

            self._log_event(
                event_type="mode_change",
                source="system",
                action=f"mode_change:{old_mode.value}->{mode.value}",
                decision="allowed",
                reason=f"Boundary mode changed from {old_mode.value} to {mode.value}",
            )

            logger.warning(
                f"Boundary mode changed: {old_mode.value} -> {mode.value}"
            )

    def set_chain_callback(self, callback: Callable[[dict], None]):
        """Set callback for recording events to blockchain."""
        self._chain_callback = callback

    def _generate_event_id(self) -> str:
        """Generate unique event ID."""
        with self._lock:
            self._event_counter += 1
            return f"SEC-{int(time.time())}-{self._event_counter:06d}"

    def _log_event(
        self,
        event_type: str,
        source: str,
        action: str,
        decision: str,
        reason: str,
        permission: Permission | None = None,
        role: Role | None = None,
        data_classification: DataClassification | None = None,
        violation_id: str | None = None,
        request_data: dict | None = None,
        record_to_chain: bool = False,
    ) -> SecurityEvent:
        """Log a security event."""
        request_hash = None
        if request_data:
            content = json.dumps(request_data, sort_keys=True)
            request_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        event = SecurityEvent(
            event_id=self._generate_event_id(),
            timestamp=datetime.utcnow().isoformat() + "Z",
            event_type=event_type,
            source=source,
            action=action,
            permission=permission.name if permission else None,
            role=role.value if role else None,
            boundary_mode=self._boundary_mode.value,
            enforcement_mode=self._enforcement_mode.value,
            decision=decision,
            reason=reason,
            data_classification=data_classification.value if data_classification else None,
            violation_id=violation_id,
            request_hash=request_hash,
        )

        with self._lock:
            self._events.append(event)
            if len(self._events) > self._max_events:
                self._events = self._events[-self._max_events:]

        # Record significant events to blockchain
        if record_to_chain and self._chain_callback:
            try:
                entry = event.to_chain_entry()
                self._chain_callback(entry)
            except Exception as e:
                logger.error(f"Failed to record event to chain: {e}")

        return event

    def authorize(
        self,
        api_key: str | None,
        permission: Permission,
        request_data: dict | None = None,
        destination: str = "natlangchain",
    ) -> tuple[bool, str, SecurityEvent]:
        """
        Perform unified authorization check.

        This combines:
        1. RBAC permission check
        2. Mode-based restrictions
        3. Boundary daemon data flow check

        Args:
            api_key: API key for authentication
            permission: Required permission
            request_data: Optional request payload for boundary check
            destination: Target destination for data flow

        Returns:
            Tuple of (allowed, reason, event)
        """
        source = "anonymous"
        role = None
        data_classification = None

        # Step 1: Check mode-based restrictions
        mode_restrictions = MODE_PERMISSION_RESTRICTIONS.get(self._boundary_mode, set())
        if permission in mode_restrictions:
            event = self._log_event(
                event_type="mode_restriction",
                source=source,
                action=permission.name,
                decision="denied",
                reason=f"Permission {permission.name} restricted in {self._boundary_mode.value} mode",
                permission=permission,
                record_to_chain=True,
            )
            return False, event.reason, event

        # Step 2: RBAC check
        rbac_allowed, rbac_reason = self._rbac.check_permission(api_key, permission)

        if api_key:
            key_info = self._rbac.get_key_info(api_key)
            if key_info:
                source = key_info.name
                role = key_info.role
                data_classification = ROLE_TO_CLASSIFICATION.get(role, DataClassification.INTERNAL)

        if not rbac_allowed:
            event = self._log_event(
                event_type="rbac_denied",
                source=source,
                action=permission.name,
                decision="denied",
                reason=rbac_reason,
                permission=permission,
                role=role,
                data_classification=data_classification,
                record_to_chain=True,
            )
            return False, rbac_reason, event

        # Step 3: Boundary daemon check (if request data provided)
        if request_data:
            boundary_result = self._daemon.authorize_request({
                "request_id": f"RBAC-{int(time.time())}",
                "source": source,
                "destination": destination,
                "payload": request_data,
                "data_classification": data_classification.value if data_classification else None,
            })

            if not boundary_result.get("authorized", False):
                violation = boundary_result.get("violation", {})
                event = self._log_event(
                    event_type="boundary_blocked",
                    source=source,
                    action=permission.name,
                    decision="blocked",
                    reason=violation.get("reason", "Boundary policy violation"),
                    permission=permission,
                    role=role,
                    data_classification=data_classification,
                    violation_id=violation.get("violation_id"),
                    request_data=request_data,
                    record_to_chain=True,
                )
                return False, event.reason, event

        # All checks passed
        event = self._log_event(
            event_type="authorized",
            source=source,
            action=permission.name,
            decision="allowed",
            reason=f"RBAC: {rbac_reason}",
            permission=permission,
            role=role,
            data_classification=data_classification,
            request_data=request_data,
        )

        return True, "Authorized", event

    def check_data_flow(
        self,
        data: Any,
        source: str,
        destination: str,
        classification: DataClassification | None = None,
    ) -> tuple[bool, str, SecurityEvent | None]:
        """
        Check if data flow is allowed by boundary daemon.

        Args:
            data: Data to check
            source: Source of the data
            destination: Intended destination
            classification: Optional explicit classification

        Returns:
            Tuple of (allowed, reason, event)
        """
        payload = {"content": data} if isinstance(data, str) else data

        result = self._daemon.authorize_request({
            "request_id": f"FLOW-{int(time.time())}",
            "source": source,
            "destination": destination,
            "payload": payload,
            "data_classification": classification.value if classification else None,
        })

        if result.get("authorized", False):
            return True, "Data flow authorized", None

        violation = result.get("violation", {})
        event = self._log_event(
            event_type="data_flow_blocked",
            source=source,
            action=f"data_flow:{source}->{destination}",
            decision="blocked",
            reason=violation.get("reason", "Data flow not authorized"),
            data_classification=classification,
            violation_id=violation.get("violation_id"),
            request_data=payload,
            record_to_chain=True,
        )

        return False, event.reason, event

    def get_events(
        self,
        event_type: str | None = None,
        decision: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Get security events."""
        with self._lock:
            events = self._events.copy()

        if event_type:
            events = [e for e in events if e.event_type == event_type]
        if decision:
            events = [e for e in events if e.decision == decision]

        return [e.to_dict() for e in events[-limit:]]

    def get_violations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get security violations (denied/blocked events)."""
        return self.get_events(decision="denied", limit=limit) + \
               self.get_events(decision="blocked", limit=limit)

    def get_stats(self) -> dict[str, Any]:
        """Get security statistics."""
        with self._lock:
            events = self._events.copy()

        total = len(events)
        allowed = sum(1 for e in events if e.decision == "allowed")
        denied = sum(1 for e in events if e.decision == "denied")
        blocked = sum(1 for e in events if e.decision == "blocked")

        by_type = {}
        for e in events:
            by_type[e.event_type] = by_type.get(e.event_type, 0) + 1

        return {
            "boundary_mode": self._boundary_mode.value,
            "enforcement_mode": self._enforcement_mode.value,
            "total_events": total,
            "allowed": allowed,
            "denied": denied,
            "blocked": blocked,
            "by_type": by_type,
        }


# =============================================================================
# Global Gateway Instance
# =============================================================================

_gateway: BoundaryRBACGateway | None = None
_gateway_lock = threading.Lock()


def get_security_gateway() -> BoundaryRBACGateway:
    """Get or create the global security gateway."""
    global _gateway

    with _gateway_lock:
        if _gateway is None:
            mode_str = os.getenv("NATLANGCHAIN_BOUNDARY_MODE", "standard")
            try:
                mode = BoundaryMode(mode_str)
            except ValueError:
                mode = BoundaryMode.STANDARD
                logger.warning(f"Invalid boundary mode '{mode_str}', using STANDARD")

            _gateway = BoundaryRBACGateway(boundary_mode=mode)

        return _gateway


def set_boundary_mode(mode: BoundaryMode):
    """Set the global boundary mode."""
    gateway = get_security_gateway()
    gateway.boundary_mode = mode


def get_boundary_mode() -> BoundaryMode:
    """Get the current boundary mode."""
    return get_security_gateway().boundary_mode


# =============================================================================
# Decorators
# =============================================================================

def require_boundary_permission(
    permission: Permission,
    check_payload: bool = False,
    destination: str = "natlangchain",
):
    """
    Decorator combining RBAC and boundary-daemon checks.

    Args:
        permission: Required permission
        check_payload: Whether to check request payload with boundary daemon
        destination: Destination for data flow check

    Example:
        @app.route('/entries', methods=['POST'])
        @require_boundary_permission(Permission.ENTRY_CREATE, check_payload=True)
        def create_entry():
            ...
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            gateway = get_security_gateway()

            # Get API key
            api_key = request.headers.get('X-API-Key')

            # Get request data if checking payload
            request_data = None
            if check_payload and request.is_json:
                request_data = request.get_json(silent=True)

            # Authorize
            allowed, reason, event = gateway.authorize(
                api_key=api_key,
                permission=permission,
                request_data=request_data,
                destination=destination,
            )

            # Store in request context
            g.security_event = event
            g.security_allowed = allowed

            if not allowed:
                return jsonify({
                    "error": "Access denied",
                    "reason": reason,
                    "event_id": event.event_id,
                    "boundary_mode": event.boundary_mode,
                }), 403

            return f(*args, **kwargs)

        return decorated_function
    return decorator


def require_boundary_mode(max_mode: BoundaryMode):
    """
    Decorator to restrict endpoint based on boundary mode.

    Args:
        max_mode: Maximum mode level that allows access
                  (modes more restrictive than this will block)

    Example:
        @require_boundary_mode(BoundaryMode.ELEVATED)
        def sensitive_operation():
            # Only available in OPEN, STANDARD, or ELEVATED modes
            ...
    """
    mode_hierarchy = [
        BoundaryMode.OPEN,
        BoundaryMode.STANDARD,
        BoundaryMode.ELEVATED,
        BoundaryMode.RESTRICTED,
        BoundaryMode.LOCKDOWN,
    ]

    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            current_mode = get_boundary_mode()

            try:
                current_level = mode_hierarchy.index(current_mode)
                max_level = mode_hierarchy.index(max_mode)

                if current_level > max_level:
                    return jsonify({
                        "error": "Operation not available",
                        "reason": f"Current mode ({current_mode.value}) restricts this operation",
                        "required_mode": f"{max_mode.value} or lower",
                    }), 503

            except ValueError:
                pass  # Unknown mode, allow

            return f(*args, **kwargs)

        return decorated_function
    return decorator


# =============================================================================
# Chain Integration Helpers
# =============================================================================

def record_security_event_to_chain(
    chain,
    event: SecurityEvent,
):
    """
    Record a security event to the NatLangChain blockchain.

    Args:
        chain: NatLangChain instance
        event: Security event to record
    """
    try:
        from blockchain import NaturalLanguageEntry

        entry_data = event.to_chain_entry()
        entry = NaturalLanguageEntry(
            content=entry_data["content"],
            author=entry_data["author"],
            intent=entry_data["intent"],
            metadata=entry_data["metadata"],
        )

        chain.add_entry(entry)
        logger.debug(f"Security event {event.event_id} recorded to chain")

    except Exception as e:
        logger.error(f"Failed to record security event to chain: {e}")


def setup_chain_integration(chain):
    """
    Set up automatic security event recording to blockchain.

    Args:
        chain: NatLangChain instance
    """
    gateway = get_security_gateway()

    def record_callback(entry_data: dict):
        try:
            from blockchain import NaturalLanguageEntry

            entry = NaturalLanguageEntry(
                content=entry_data["content"],
                author=entry_data.get("author", "security_gateway"),
                intent=entry_data.get("intent", "Security audit"),
                metadata=entry_data.get("metadata", {}),
            )
            chain.add_entry(entry)

        except Exception as e:
            logger.error(f"Chain callback failed: {e}")

    gateway.set_chain_callback(record_callback)
    logger.info("Security gateway chain integration enabled")


# =============================================================================
# API Endpoints for Security Management
# =============================================================================

def register_security_endpoints(app):
    """
    Register security management API endpoints.

    Args:
        app: Flask application
    """
    from rbac import require_role, Role

    @app.route('/security/mode', methods=['GET'])
    def get_mode():
        """Get current boundary mode."""
        gateway = get_security_gateway()
        return jsonify({
            "boundary_mode": gateway.boundary_mode.value,
            "enforcement_mode": gateway._enforcement_mode.value,
        })

    @app.route('/security/mode', methods=['PUT'])
    @require_role(Role.ADMIN)
    def set_mode():
        """Set boundary mode (admin only)."""
        data = request.get_json()
        mode_str = data.get("mode")

        try:
            mode = BoundaryMode(mode_str)
            set_boundary_mode(mode)
            return jsonify({
                "success": True,
                "boundary_mode": mode.value,
            })
        except ValueError:
            return jsonify({
                "error": f"Invalid mode: {mode_str}",
                "valid_modes": [m.value for m in BoundaryMode],
            }), 400

    @app.route('/security/events', methods=['GET'])
    @require_role(Role.OPERATOR)
    def get_events():
        """Get security events."""
        gateway = get_security_gateway()

        event_type = request.args.get("type")
        decision = request.args.get("decision")
        limit = int(request.args.get("limit", 100))

        events = gateway.get_events(
            event_type=event_type,
            decision=decision,
            limit=limit,
        )

        return jsonify({"events": events})

    @app.route('/security/violations', methods=['GET'])
    @require_role(Role.OPERATOR)
    def get_violations():
        """Get security violations."""
        gateway = get_security_gateway()
        limit = int(request.args.get("limit", 100))

        return jsonify({
            "violations": gateway.get_violations(limit=limit)
        })

    @app.route('/security/stats', methods=['GET'])
    def get_stats():
        """Get security statistics."""
        gateway = get_security_gateway()
        return jsonify(gateway.get_stats())

    logger.info("Security management endpoints registered")

"""
NatLangChain - Boundary Protection Exception Hierarchy

Provides a consistent set of exceptions for all boundary protection components.
All exceptions include structured error context for improved debugging and monitoring.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ErrorSeverity(Enum):
    """Severity levels for boundary protection errors."""
    LOW = "low"           # Informational, no action needed
    MEDIUM = "medium"     # Warning, should be monitored
    HIGH = "high"         # Error, requires attention
    CRITICAL = "critical" # Critical, may require immediate intervention


@dataclass
class ErrorContext:
    """Structured context for error tracking and debugging."""
    component: str
    action: str
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    details: dict[str, Any] = field(default_factory=dict)
    severity: ErrorSeverity = ErrorSeverity.MEDIUM

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging."""
        return {
            "component": self.component,
            "action": self.action,
            "timestamp": self.timestamp,
            "details": self.details,
            "severity": self.severity.value
        }


class BoundaryProtectionError(Exception):
    """
    Base exception for all boundary protection errors.

    Includes structured error context for improved debugging
    and integration with monitoring systems.
    """

    def __init__(
        self,
        message: str,
        component: str = "unknown",
        action: str = "unknown",
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(message)
        self.message = message
        self.context = ErrorContext(
            component=component,
            action=action,
            severity=severity,
            details=details or {}
        )
        self.cause = cause

        # Chain the cause if provided
        if cause:
            self.__cause__ = cause

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for logging/serialization."""
        result = {
            "error_type": type(self).__name__,
            "message": self.message,
            **self.context.to_dict()
        }
        if self.cause:
            result["cause"] = {
                "type": type(self.cause).__name__,
                "message": str(self.cause)
            }
        return result

    def __str__(self) -> str:
        base = f"[{self.context.component}:{self.context.action}] {self.message}"
        if self.cause:
            base += f" (caused by: {self.cause})"
        return base


# =============================================================================
# Enforcement Errors
# =============================================================================

class EnforcementError(BoundaryProtectionError):
    """
    Raised when a security enforcement action fails.

    Examples:
    - Network blocking failed
    - USB enforcement failed
    - Process sandboxing failed
    """

    def __init__(
        self,
        message: str,
        enforcement_type: str = "unknown",
        target: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="security_enforcement",
            action=enforcement_type,
            severity=ErrorSeverity.HIGH,
            details={
                "enforcement_type": enforcement_type,
                "target": target,
                **(details or {})
            },
            cause=cause
        )
        self.enforcement_type = enforcement_type
        self.target = target


class NetworkEnforcementError(EnforcementError):
    """Network-specific enforcement failures."""

    def __init__(
        self,
        message: str,
        target: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            enforcement_type="network",
            target=target,
            details=details,
            cause=cause
        )


class ProcessEnforcementError(EnforcementError):
    """Process sandboxing/control failures."""

    def __init__(
        self,
        message: str,
        pid: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            enforcement_type="process",
            target=str(pid) if pid else None,
            details={"pid": pid, **(details or {})},
            cause=cause
        )


# =============================================================================
# SIEM Errors
# =============================================================================

class SIEMError(BoundaryProtectionError):
    """Base class for SIEM-related errors."""

    def __init__(
        self,
        message: str,
        action: str = "siem_operation",
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="boundary_siem",
            action=action,
            severity=ErrorSeverity.MEDIUM,
            details=details,
            cause=cause
        )


class SIEMConnectionError(SIEMError):
    """SIEM connection or communication failures."""

    def __init__(
        self,
        message: str,
        endpoint: str | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            action="connect",
            details={
                "endpoint": endpoint,
                "status_code": status_code,
                **(details or {})
            },
            cause=cause
        )
        self.endpoint = endpoint
        self.status_code = status_code


class SIEMEventError(SIEMError):
    """Event sending/processing failures."""

    def __init__(
        self,
        message: str,
        event_id: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            action="send_event",
            details={"event_id": event_id, **(details or {})},
            cause=cause
        )


# =============================================================================
# Policy Errors
# =============================================================================

class PolicyError(BoundaryProtectionError):
    """Base class for policy-related errors."""

    def __init__(
        self,
        message: str,
        policy_name: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="boundary_daemon",
            action="policy_check",
            severity=ErrorSeverity.HIGH,
            details={"policy_name": policy_name, **(details or {})},
            cause=cause
        )
        self.policy_name = policy_name


class PolicyViolationError(PolicyError):
    """Raised when a policy is violated."""

    def __init__(
        self,
        message: str,
        violation_type: str,
        source: str | None = None,
        destination: str | None = None,
        details: dict[str, Any] | None = None
    ):
        super().__init__(
            message=message,
            policy_name=violation_type,
            details={
                "violation_type": violation_type,
                "source": source,
                "destination": destination,
                **(details or {})
            }
        )
        self.violation_type = violation_type


class PolicyConfigurationError(PolicyError):
    """Invalid policy configuration."""

    def __init__(
        self,
        message: str,
        policy_name: str | None = None,
        config_key: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            policy_name=policy_name,
            details={"config_key": config_key, **(details or {})},
            cause=cause
        )


# =============================================================================
# Mode Transition Errors
# =============================================================================

class ModeTransitionError(BoundaryProtectionError):
    """Errors during boundary mode transitions."""

    def __init__(
        self,
        message: str,
        from_mode: str | None = None,
        to_mode: str | None = None,
        reason: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="boundary_modes",
            action="mode_transition",
            severity=ErrorSeverity.HIGH,
            details={
                "from_mode": from_mode,
                "to_mode": to_mode,
                "reason": reason,
                **(details or {})
            },
            cause=cause
        )
        self.from_mode = from_mode
        self.to_mode = to_mode


class OverrideError(ModeTransitionError):
    """Override ceremony failures."""

    def __init__(
        self,
        message: str,
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            reason="override_failed",
            details={"request_id": request_id, **(details or {})},
            cause=cause
        )


# =============================================================================
# Security Check Errors
# =============================================================================

class SecurityCheckError(BoundaryProtectionError):
    """Errors during security checks (injection detection, etc.)."""

    def __init__(
        self,
        message: str,
        check_type: str = "unknown",
        input_context: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="agent_security",
            action=check_type,
            severity=ErrorSeverity.HIGH,
            details={
                "check_type": check_type,
                "input_context": input_context,
                **(details or {})
            },
            cause=cause
        )
        self.check_type = check_type


class PatternMatchError(SecurityCheckError):
    """Pattern matching failures during detection."""

    def __init__(
        self,
        message: str,
        pattern: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            check_type="pattern_match",
            details={"pattern": pattern, **(details or {})},
            cause=cause
        )


class AttestationError(SecurityCheckError):
    """Agent attestation failures."""

    def __init__(
        self,
        message: str,
        agent_id: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            check_type="attestation",
            details={"agent_id": agent_id, **(details or {})},
            cause=cause
        )


# =============================================================================
# Tripwire Errors
# =============================================================================

class TripwireError(BoundaryProtectionError):
    """Errors in tripwire handling."""

    def __init__(
        self,
        message: str,
        tripwire_type: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="boundary_modes",
            action="tripwire",
            severity=ErrorSeverity.CRITICAL,
            details={"tripwire_type": tripwire_type, **(details or {})},
            cause=cause
        )


# =============================================================================
# Configuration Errors
# =============================================================================

class ConfigurationError(BoundaryProtectionError):
    """Configuration-related errors."""

    def __init__(
        self,
        message: str,
        config_key: str | None = None,
        expected_type: str | None = None,
        details: dict[str, Any] | None = None,
        cause: Exception | None = None
    ):
        super().__init__(
            message=message,
            component="configuration",
            action="load_config",
            severity=ErrorSeverity.HIGH,
            details={
                "config_key": config_key,
                "expected_type": expected_type,
                **(details or {})
            },
            cause=cause
        )


# =============================================================================
# Utility Functions
# =============================================================================

def wrap_exception(
    e: Exception,
    component: str,
    action: str,
    message: str | None = None
) -> BoundaryProtectionError:
    """
    Wrap a generic exception in a BoundaryProtectionError.

    Useful for converting third-party or stdlib exceptions
    into our exception hierarchy.
    """
    return BoundaryProtectionError(
        message=message or str(e),
        component=component,
        action=action,
        cause=e
    )


def log_exception(
    logger,
    e: BoundaryProtectionError,
    level: str = "error"
) -> None:
    """
    Log a BoundaryProtectionError with full context.

    Args:
        logger: Logger instance
        e: The exception to log
        level: Log level (debug, info, warning, error, critical)
    """
    log_func = getattr(logger, level, logger.error)
    log_func(
        str(e),
        extra=e.to_dict(),
        exc_info=True if level in ("error", "critical") else False
    )

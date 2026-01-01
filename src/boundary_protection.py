"""
NatLangChain - Unified Boundary Protection Layer

This module integrates all boundary protection capabilities:
- Boundary Daemon (data classification, policy enforcement)
- Boundary Modes (six trust levels, tripwires)
- Security Enforcement (network, USB, sandboxing)
- Boundary SIEM (event logging, alert management)
- Agent Security (prompt injection, RAG poisoning)

Provides a single unified interface for protecting NatLangChain.

Based on:
- Boundary Daemon: https://github.com/kase1111-hash/boundary-daemon-
- Boundary SIEM: https://github.com/kase1111-hash/Boundary-SIEM
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable

try:
    from agent_security import (
        AgentSecurityManager,
        ThreatDetection,
        ThreatCategory,
        RiskLevel,
        init_agent_security,
    )
    from boundary_daemon import (
        BoundaryDaemon,
        BoundaryPolicy,
        DataClassification,
        EnforcementMode,
        PolicyViolation,
        ViolationType,
    )
    from boundary_modes import (
        BoundaryMode,
        BoundaryModeManager,
        MemoryClass,
        ModeTransition,
        TripwireType,
        init_mode_manager,
    )
    from boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        SIEMEvent,
        SIEMSeverity,
        init_siem_client,
        shutdown_siem_client,
    )
    from security_enforcement import (
        EnforcementResult,
        SecurityEnforcementManager,
    )
except ImportError:
    from .agent_security import (
        AgentSecurityManager,
        ThreatDetection,
        ThreatCategory,
        RiskLevel,
        init_agent_security,
    )
    from .boundary_daemon import (
        BoundaryDaemon,
        BoundaryPolicy,
        DataClassification,
        EnforcementMode,
        PolicyViolation,
        ViolationType,
    )
    from .boundary_modes import (
        BoundaryMode,
        BoundaryModeManager,
        MemoryClass,
        ModeTransition,
        TripwireType,
        init_mode_manager,
    )
    from .boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        SIEMEvent,
        SIEMSeverity,
        init_siem_client,
        shutdown_siem_client,
    )
    from .security_enforcement import (
        EnforcementResult,
        SecurityEnforcementManager,
    )

logger = logging.getLogger(__name__)


@dataclass
class ProtectionConfig:
    """Configuration for the boundary protection system."""
    # SIEM configuration
    siem_url: str | None = None
    siem_api_key: str | None = None
    siem_syslog_host: str | None = None
    siem_syslog_port: int = 514

    # Mode configuration
    initial_mode: BoundaryMode = BoundaryMode.RESTRICTED
    enable_tripwires: bool = True
    cooldown_period: int = 300

    # Enforcement configuration
    enable_network_enforcement: bool = True
    enable_usb_enforcement: bool = True
    enable_process_sandboxing: bool = True

    # Agent security configuration
    enable_injection_detection: bool = True
    enable_rag_poisoning_detection: bool = True
    enable_response_guardrails: bool = True
    enable_agent_attestation: bool = True

    # Boundary daemon configuration
    enforcement_mode: EnforcementMode = EnforcementMode.STRICT

    # Audit configuration
    audit_log_path: str = "/var/log/natlangchain/boundary.log"

    @classmethod
    def from_env(cls) -> "ProtectionConfig":
        """Create configuration from environment variables."""
        return cls(
            siem_url=os.getenv("BOUNDARY_SIEM_URL"),
            siem_api_key=os.getenv("BOUNDARY_SIEM_API_KEY"),
            siem_syslog_host=os.getenv("BOUNDARY_SIEM_SYSLOG_HOST"),
            siem_syslog_port=int(os.getenv("BOUNDARY_SIEM_SYSLOG_PORT", "514")),
            initial_mode=BoundaryMode(os.getenv("BOUNDARY_INITIAL_MODE", "restricted")),
            enable_tripwires=os.getenv("BOUNDARY_ENABLE_TRIPWIRES", "true").lower() == "true",
            cooldown_period=int(os.getenv("BOUNDARY_COOLDOWN_PERIOD", "300")),
            enable_network_enforcement=os.getenv("BOUNDARY_NETWORK_ENFORCEMENT", "true").lower() == "true",
            enable_usb_enforcement=os.getenv("BOUNDARY_USB_ENFORCEMENT", "true").lower() == "true",
            enable_process_sandboxing=os.getenv("BOUNDARY_SANDBOXING", "true").lower() == "true",
            enable_injection_detection=os.getenv("BOUNDARY_INJECTION_DETECTION", "true").lower() == "true",
            enable_rag_poisoning_detection=os.getenv("BOUNDARY_RAG_DETECTION", "true").lower() == "true",
            enable_response_guardrails=os.getenv("BOUNDARY_GUARDRAILS", "true").lower() == "true",
            enable_agent_attestation=os.getenv("BOUNDARY_ATTESTATION", "true").lower() == "true",
            enforcement_mode=EnforcementMode(os.getenv("BOUNDARY_ENFORCEMENT_MODE", "strict")),
            audit_log_path=os.getenv("BOUNDARY_AUDIT_LOG", "/var/log/natlangchain/boundary.log"),
        )


@dataclass
class ProtectionResult:
    """Result of a protection check."""
    allowed: bool
    action: str
    risk_level: RiskLevel
    details: dict[str, Any]
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "allowed": self.allowed,
            "action": self.action,
            "risk_level": self.risk_level.value,
            "details": self.details,
            "timestamp": self.timestamp
        }


class BoundaryProtection:
    """
    Unified boundary protection for NatLangChain.

    This class provides a single interface for all security features:
    - Data flow control (what data can go where)
    - Mode management (trust levels and restrictions)
    - Threat detection (injection, poisoning, etc.)
    - Security enforcement (network, USB, process)
    - Audit logging (SIEM integration)

    Fail-safe design principles:
    - Default to deny when uncertain
    - Escalate to LOCKDOWN on critical failures
    - Log all security events
    - Automatic tripwire responses
    """

    def __init__(self, config: ProtectionConfig | None = None):
        """
        Initialize the boundary protection system.

        Args:
            config: Configuration options. If None, loads from environment.
        """
        self.config = config or ProtectionConfig.from_env()
        self._lock = threading.RLock()
        self._running = False

        # Initialize components
        self._init_components()

        # Track statistics
        self._stats = {
            "requests_checked": 0,
            "requests_blocked": 0,
            "threats_detected": 0,
            "mode_changes": 0,
            "tripwires_triggered": 0,
            "startup_time": datetime.utcnow().isoformat() + "Z"
        }

    def _init_components(self) -> None:
        """Initialize all protection components."""
        # Initialize SIEM first (other components may use it)
        if self.config.siem_url or self.config.siem_syslog_host:
            self.siem = init_siem_client(
                siem_url=self.config.siem_url,
                api_key=self.config.siem_api_key,
                syslog_host=self.config.siem_syslog_host,
                syslog_port=self.config.siem_syslog_port
            )
        else:
            self.siem = None

        # Initialize security enforcement
        self.enforcement = SecurityEnforcementManager(
            log_path=self.config.audit_log_path
        )

        # Initialize mode manager
        self.modes = init_mode_manager(
            initial_mode=self.config.initial_mode,
            enforcement=self.enforcement,
            siem_client=self.siem,
            enable_tripwires=self.config.enable_tripwires,
            cooldown_period=self.config.cooldown_period
        )

        # Initialize boundary daemon
        self.daemon = BoundaryDaemon(
            enforcement_mode=self.config.enforcement_mode
        )

        # Initialize agent security
        self.agent_security = init_agent_security(
            siem_client=self.siem,
            enable_attestation=self.config.enable_agent_attestation
        )

    def start(self) -> None:
        """Start the boundary protection system."""
        with self._lock:
            if self._running:
                return

            self._running = True

            # Start SIEM client
            if self.siem:
                self.siem.start()

            # Start enforcement watchdog
            self.enforcement.start_watchdog()

            # Log startup
            if self.siem:
                event = NatLangChainSIEMEvents.system_startup(
                    version="1.0.0",
                    config={
                        "initial_mode": self.config.initial_mode.value,
                        "tripwires_enabled": self.config.enable_tripwires,
                        "enforcement_mode": self.config.enforcement_mode.value
                    }
                )
                self.siem.send_event_sync(event)

            logger.info("Boundary protection started")

    def stop(self) -> None:
        """Stop the boundary protection system."""
        with self._lock:
            if not self._running:
                return

            self._running = False

            # Shutdown SIEM
            if self.siem:
                shutdown_siem_client()

            logger.info("Boundary protection stopped")

    # =========================================================================
    # Data Flow Protection
    # =========================================================================

    def authorize_request(
        self,
        source: str,
        destination: str,
        payload: Any,
        classification: str | None = None
    ) -> ProtectionResult:
        """
        Authorize an outbound data request.

        This is the main entry point for data flow control. It checks:
        1. Current mode restrictions
        2. Data classification policies
        3. Sensitive pattern detection
        4. Destination allowlists

        Args:
            source: Where the request originates
            destination: Where the data is going
            payload: The data being sent
            classification: Optional explicit data classification

        Returns:
            ProtectionResult indicating if request is allowed
        """
        with self._lock:
            self._stats["requests_checked"] += 1

            # Check mode restrictions
            if not self.modes.is_network_allowed():
                self._stats["requests_blocked"] += 1
                return ProtectionResult(
                    allowed=False,
                    action="blocked_by_mode",
                    risk_level=RiskLevel.HIGH,
                    details={
                        "reason": f"Network blocked in {self.modes.current_mode.value} mode",
                        "source": source,
                        "destination": destination
                    }
                )

            # Check boundary daemon policies
            auth_result = self.daemon.authorize_request({
                "request_id": f"REQ-{int(time.time() * 1000)}",
                "source": source,
                "destination": destination,
                "payload": payload,
                "data_classification": classification
            })

            if not auth_result.get("authorized", False):
                self._stats["requests_blocked"] += 1

                # Trigger tripwire for exfiltration attempts
                if auth_result.get("violation", {}).get("type") == ViolationType.DATA_EXFILTRATION_ATTEMPT.value:
                    self.modes.trigger_tripwire(
                        TripwireType.DATA_EXFILTRATION_ATTEMPT,
                        f"Exfiltration attempt to {destination}"
                    )
                    self._stats["tripwires_triggered"] += 1

                # Send SIEM event
                if self.siem:
                    event = NatLangChainSIEMEvents.boundary_violation(
                        violation_type=auth_result.get("violation", {}).get("type", "unknown"),
                        source=source,
                        destination=destination,
                        pattern=auth_result.get("violation", {}).get("pattern"),
                        blocked=True
                    )
                    self.siem.send_event(event)

                return ProtectionResult(
                    allowed=False,
                    action="blocked_by_policy",
                    risk_level=RiskLevel.HIGH,
                    details={
                        "reason": auth_result.get("violation", {}).get("reason", "Policy violation"),
                        "violation_type": auth_result.get("violation", {}).get("type"),
                        "pattern": auth_result.get("violation", {}).get("pattern")
                    }
                )

            return ProtectionResult(
                allowed=True,
                action="allowed",
                risk_level=RiskLevel.NONE,
                details={
                    "authorization_id": auth_result.get("authorization_id"),
                    "classification": auth_result.get("data_classification")
                }
            )

    def inspect_data(self, data: str) -> ProtectionResult:
        """
        Inspect data for sensitive content without authorizing.

        Useful for pre-flight checks before attempting to send data.

        Args:
            data: The data to inspect

        Returns:
            ProtectionResult with risk assessment
        """
        result = self.daemon.inspect_data(data)

        risk_level = RiskLevel.NONE
        if result["risk_score"] >= 0.8:
            risk_level = RiskLevel.CRITICAL
        elif result["risk_score"] >= 0.6:
            risk_level = RiskLevel.HIGH
        elif result["risk_score"] >= 0.4:
            risk_level = RiskLevel.MEDIUM
        elif result["risk_score"] >= 0.2:
            risk_level = RiskLevel.LOW

        return ProtectionResult(
            allowed=result["policy_compliance"],
            action="inspection",
            risk_level=risk_level,
            details={
                "risk_score": result["risk_score"],
                "patterns_found": len(result["detected_patterns"]),
                "classification": result["classification_suggested"]
            }
        )

    # =========================================================================
    # Mode Management
    # =========================================================================

    @property
    def current_mode(self) -> BoundaryMode:
        """Get the current boundary mode."""
        return self.modes.current_mode

    def set_mode(
        self,
        mode: BoundaryMode,
        reason: str,
        triggered_by: str | None = None
    ) -> ModeTransition:
        """
        Change the boundary mode.

        Args:
            mode: Target mode
            reason: Why the mode is being changed
            triggered_by: Who or what triggered the change

        Returns:
            ModeTransition record
        """
        with self._lock:
            transition = self.modes.set_mode(mode, reason, triggered_by)
            if transition.success:
                self._stats["mode_changes"] += 1
            return transition

    def request_mode_override(
        self,
        to_mode: BoundaryMode,
        reason: str,
        requested_by: str
    ):
        """
        Request a human override ceremony for mode change.

        Required when relaxing security (moving to less restrictive mode).

        Args:
            to_mode: Target mode
            reason: Why the change is needed
            requested_by: Who is requesting

        Returns:
            HumanOverrideRequest with confirmation code
        """
        return self.modes.request_override(requested_by, to_mode, reason)

    def confirm_mode_override(
        self,
        request_id: str,
        confirmation_code: str,
        confirmed_by: str
    ) -> ModeTransition:
        """
        Confirm a human override ceremony.

        Args:
            request_id: ID of the override request
            confirmation_code: The confirmation code
            confirmed_by: Who is confirming

        Returns:
            ModeTransition result
        """
        return self.modes.confirm_override(request_id, confirmation_code, confirmed_by)

    def trigger_lockdown(self, reason: str) -> ModeTransition:
        """
        Immediately enter LOCKDOWN mode.

        Args:
            reason: Why lockdown is being triggered

        Returns:
            ModeTransition result
        """
        with self._lock:
            transition = self.modes.set_mode(
                BoundaryMode.LOCKDOWN,
                reason=f"Manual lockdown: {reason}",
                triggered_by="system",
                force=True
            )

            if transition.success and self.siem:
                event = NatLangChainSIEMEvents.lockdown_activated(
                    reason=reason,
                    triggered_by="manual",
                    actions_taken=transition.actions_taken
                )
                self.siem.send_event_sync(event)

            return transition

    # =========================================================================
    # AI/Agent Security
    # =========================================================================

    def check_input(
        self,
        text: str,
        context: str = "user_input"
    ) -> ProtectionResult:
        """
        Check user input for security threats.

        Detects prompt injection, jailbreak attempts, etc.

        Args:
            text: The input to check
            context: Context of the input

        Returns:
            ProtectionResult
        """
        if not self.config.enable_injection_detection:
            return ProtectionResult(
                allowed=True,
                action="skipped",
                risk_level=RiskLevel.NONE,
                details={"reason": "Injection detection disabled"}
            )

        detection = self.agent_security.check_input(text, context)

        if detection.detected:
            self._stats["threats_detected"] += 1

            # Trigger tripwire for repeated injection attempts
            if detection.risk_level in (RiskLevel.HIGH, RiskLevel.CRITICAL):
                self.modes.trigger_tripwire(
                    TripwireType.PROMPT_INJECTION_DETECTED,
                    f"Injection detected: {detection.category.value}"
                )

        return ProtectionResult(
            allowed=not detection.detected,
            action="input_check",
            risk_level=detection.risk_level,
            details={
                "category": detection.category.value,
                "patterns": detection.patterns_matched,
                "recommendation": detection.recommendation
            }
        )

    def check_document(
        self,
        content: str,
        document_id: str,
        source: str
    ) -> ProtectionResult:
        """
        Check a document for RAG poisoning.

        Should be called before adding documents to RAG index.

        Args:
            content: Document content
            document_id: Document identifier
            source: Document source

        Returns:
            ProtectionResult
        """
        if not self.config.enable_rag_poisoning_detection:
            return ProtectionResult(
                allowed=True,
                action="skipped",
                risk_level=RiskLevel.NONE,
                details={"reason": "RAG detection disabled"}
            )

        detection = self.agent_security.check_document(content, document_id, source)

        if detection.detected:
            self._stats["threats_detected"] += 1

        return ProtectionResult(
            allowed=not detection.detected or detection.risk_level == RiskLevel.LOW,
            action="document_check",
            risk_level=detection.risk_level,
            details={
                "document_id": document_id,
                "source": source,
                "indicators": detection.patterns_matched,
                "recommendation": detection.recommendation
            }
        )

    def check_response(self, response: str) -> ProtectionResult:
        """
        Check an AI response for safety issues.

        Should be called before returning responses to users.

        Args:
            response: The response to check

        Returns:
            ProtectionResult
        """
        if not self.config.enable_response_guardrails:
            return ProtectionResult(
                allowed=True,
                action="skipped",
                risk_level=RiskLevel.NONE,
                details={"reason": "Guardrails disabled"}
            )

        detection = self.agent_security.check_response(response)

        if detection.detected:
            self._stats["threats_detected"] += 1

        return ProtectionResult(
            allowed=not detection.detected or detection.risk_level in (RiskLevel.LOW, RiskLevel.MEDIUM),
            action="response_check",
            risk_level=detection.risk_level,
            details={
                "issues": detection.patterns_matched,
                "recommendation": detection.recommendation
            }
        )

    def sanitize_tool_output(
        self,
        output: str,
        tool_name: str = "unknown"
    ) -> str:
        """
        Sanitize tool output before including in context.

        Redacts sensitive data and neutralizes injection attempts.

        Args:
            output: Tool output to sanitize
            tool_name: Name of the tool

        Returns:
            Sanitized output string
        """
        result = self.agent_security.sanitize_tool_output(output, tool_name)
        return result.output

    # =========================================================================
    # Policy Checks
    # =========================================================================

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed in the current mode."""
        return self.modes.is_tool_allowed(tool_name)

    def is_memory_class_allowed(self, memory_class: MemoryClass) -> bool:
        """Check if a memory class is accessible."""
        return self.modes.is_memory_class_allowed(memory_class)

    def is_network_allowed(self) -> bool:
        """Check if network access is allowed."""
        return self.modes.is_network_allowed()

    # =========================================================================
    # Status and Statistics
    # =========================================================================

    def get_status(self) -> dict[str, Any]:
        """Get comprehensive status of the protection system."""
        return {
            "running": self._running,
            "mode": {
                "current": self.modes.current_mode.value,
                **self.modes.get_status()
            },
            "enforcement": self.enforcement.get_enforcement_status(),
            "siem": {
                "connected": self.siem._is_connected() if self.siem else False,
                "stats": self.siem.get_stats() if self.siem else None
            },
            "agent_security": self.agent_security.get_stats(),
            "statistics": self._stats
        }

    def get_stats(self) -> dict[str, Any]:
        """Get protection statistics."""
        return self._stats.copy()

    def get_violations(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent policy violations."""
        return self.daemon.get_violations(limit=limit)

    def get_audit_log(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent audit log entries."""
        return self.daemon.get_audit_log(limit=limit)

    def get_transition_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get mode transition history."""
        return self.modes.get_transition_history(limit=limit)

    # =========================================================================
    # SIEM Alerts
    # =========================================================================

    def get_siem_alerts(
        self,
        status: str | None = None,
        limit: int = 100
    ) -> list[Any]:
        """
        Get alerts from the SIEM.

        Args:
            status: Filter by status ("open", "acknowledged", "closed")
            limit: Maximum alerts to return

        Returns:
            List of SIEM alerts
        """
        if not self.siem:
            return []
        return self.siem.get_alerts(status=status, limit=limit)

    def acknowledge_siem_alert(self, alert_id: str, note: str | None = None) -> bool:
        """Acknowledge a SIEM alert."""
        if not self.siem:
            return False
        return self.siem.acknowledge_alert(alert_id, note)


# =============================================================================
# Global Protection Instance
# =============================================================================

_global_protection: BoundaryProtection | None = None


def get_protection() -> BoundaryProtection | None:
    """Get the global boundary protection instance."""
    return _global_protection


def init_protection(config: ProtectionConfig | None = None) -> BoundaryProtection:
    """
    Initialize the global boundary protection system.

    Args:
        config: Configuration options

    Returns:
        The initialized BoundaryProtection instance
    """
    global _global_protection
    _global_protection = BoundaryProtection(config)
    _global_protection.start()
    return _global_protection


def shutdown_protection() -> None:
    """Shutdown the global boundary protection system."""
    global _global_protection
    if _global_protection:
        _global_protection.stop()
        _global_protection = None


# =============================================================================
# Convenience Decorators
# =============================================================================

def protected_request(
    source: str = "api",
    destination: str = "external"
):
    """
    Decorator for protecting outbound requests.

    Usage:
        @protected_request(source="api", destination="external_service")
        def call_external_api(data):
            ...

    Args:
        source: Request source identifier
        destination: Request destination identifier
    """
    def decorator(func: Callable):
        def wrapper(*args, **kwargs):
            protection = get_protection()
            if not protection:
                return func(*args, **kwargs)

            # Get payload from args (assume first arg or 'data' kwarg)
            payload = args[0] if args else kwargs.get("data", {})

            result = protection.authorize_request(source, destination, payload)
            if not result.allowed:
                raise PermissionError(
                    f"Request blocked by boundary protection: {result.details.get('reason')}"
                )

            return func(*args, **kwargs)
        return wrapper
    return decorator


def protected_input(context: str = "user_input"):
    """
    Decorator for protecting input processing.

    Usage:
        @protected_input(context="user_input")
        def process_user_message(text):
            ...

    Args:
        context: Input context
    """
    def decorator(func: Callable):
        def wrapper(text: str, *args, **kwargs):
            protection = get_protection()
            if not protection:
                return func(text, *args, **kwargs)

            result = protection.check_input(text, context)
            if not result.allowed:
                raise ValueError(
                    f"Input blocked by boundary protection: {result.details.get('recommendation')}"
                )

            return func(text, *args, **kwargs)
        return wrapper
    return decorator

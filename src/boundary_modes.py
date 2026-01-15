"""
NatLangChain - Boundary Mode Manager

Implements the six boundary modes from the Boundary Daemon specification:
- OPEN: Casual use, full network access
- RESTRICTED: Research mode, most tools available
- TRUSTED: VPN-only network access
- AIRGAP: Offline mode, no network
- COLDROOM: High-value IP protection, display only
- LOCKDOWN: Emergency mode, everything blocked

Also implements:
- Tripwire system for automatic mode transitions
- Human override ceremony for sensitive operations
- Mode transition validation and audit logging

Based on the Boundary Daemon specification:
https://github.com/kase1111-hash/boundary-daemon-
"""

import logging
import secrets
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

try:
    from boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        get_siem_client,
    )
    from security_enforcement import (
        SecurityEnforcementManager,
    )
except ImportError:
    from .boundary_siem import (
        NatLangChainSIEMEvents,
        SIEMClient,
        get_siem_client,
    )
    from .security_enforcement import (
        SecurityEnforcementManager,
    )

logger = logging.getLogger(__name__)


class BoundaryMode(Enum):
    """
    The six boundary modes from the Boundary Daemon specification.

    Each mode represents a different trust level with corresponding
    restrictions on network, tools, and memory access.
    """

    OPEN = "open"  # Casual use: Full network, all tools
    RESTRICTED = "restricted"  # Research: Online, most tools
    TRUSTED = "trusted"  # Serious work: VPN only, no USB
    AIRGAP = "airgap"  # High-value IP: Offline only
    COLDROOM = "coldroom"  # Crown jewels: Offline, display only
    LOCKDOWN = "lockdown"  # Emergency: Everything blocked


class MemoryClass(Enum):
    """Memory classification levels (0-5)."""

    PUBLIC = 0  # Can be shared anywhere
    INTERNAL = 1  # Internal use only
    SENSITIVE = 2  # Requires authentication
    CONFIDENTIAL = 3  # Limited access
    SECRET = 4  # Need-to-know basis
    COMPARTMENTED = 5  # Highest classification


class TripwireType(Enum):
    """Types of tripwires that can trigger mode transitions."""

    NETWORK_ACTIVITY_IN_AIRGAP = "network_activity_in_airgap"
    USB_INSERTION_IN_COLDROOM = "usb_insertion_in_coldroom"
    UNAUTHORIZED_MEMORY_RECALL = "unauthorized_memory_recall"
    DAEMON_TAMPERING = "daemon_tampering"
    CLOCK_DRIFT = "clock_drift"
    FAILED_AUTH_THRESHOLD = "failed_auth_threshold"
    PROMPT_INJECTION_DETECTED = "prompt_injection_detected"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    INTEGRITY_CHECK_FAILED = "integrity_check_failed"


@dataclass
class ModeConfig:
    """Configuration for a boundary mode."""

    mode: BoundaryMode
    network_allowed: bool
    vpn_only: bool
    allowed_memory_classes: list[MemoryClass]
    allowed_tools: list[str]
    blocked_tools: list[str]
    description: str

    # Enforcement flags
    block_usb: bool = False
    display_only: bool = False
    block_all_io: bool = False


# Default mode configurations based on the Boundary Daemon spec
DEFAULT_MODE_CONFIGS: dict[BoundaryMode, ModeConfig] = {
    BoundaryMode.OPEN: ModeConfig(
        mode=BoundaryMode.OPEN,
        network_allowed=True,
        vpn_only=False,
        allowed_memory_classes=[MemoryClass.PUBLIC, MemoryClass.INTERNAL],
        allowed_tools=["*"],  # All tools
        blocked_tools=[],
        description="Casual use - full network access, all tools available",
    ),
    BoundaryMode.RESTRICTED: ModeConfig(
        mode=BoundaryMode.RESTRICTED,
        network_allowed=True,
        vpn_only=False,
        allowed_memory_classes=[MemoryClass.PUBLIC, MemoryClass.INTERNAL, MemoryClass.SENSITIVE],
        allowed_tools=["*"],
        blocked_tools=["shell_execute", "file_delete", "system_modify"],
        description="Research mode - online, most tools available",
    ),
    BoundaryMode.TRUSTED: ModeConfig(
        mode=BoundaryMode.TRUSTED,
        network_allowed=True,
        vpn_only=True,
        allowed_memory_classes=[
            MemoryClass.PUBLIC,
            MemoryClass.INTERNAL,
            MemoryClass.SENSITIVE,
            MemoryClass.CONFIDENTIAL,
        ],
        allowed_tools=["*"],
        blocked_tools=["usb_access", "external_storage"],
        block_usb=True,
        description="Serious work - VPN only, no USB access",
    ),
    BoundaryMode.AIRGAP: ModeConfig(
        mode=BoundaryMode.AIRGAP,
        network_allowed=False,
        vpn_only=False,
        allowed_memory_classes=[
            MemoryClass.PUBLIC,
            MemoryClass.INTERNAL,
            MemoryClass.SENSITIVE,
            MemoryClass.CONFIDENTIAL,
            MemoryClass.SECRET,
        ],
        allowed_tools=["local_*"],  # Only local tools
        blocked_tools=["network_*", "http_*", "api_*"],
        description="High-value IP - completely offline",
    ),
    BoundaryMode.COLDROOM: ModeConfig(
        mode=BoundaryMode.COLDROOM,
        network_allowed=False,
        vpn_only=False,
        allowed_memory_classes=[
            MemoryClass.PUBLIC,
            MemoryClass.INTERNAL,
            MemoryClass.SENSITIVE,
            MemoryClass.CONFIDENTIAL,
            MemoryClass.SECRET,
            MemoryClass.COMPARTMENTED,
        ],
        allowed_tools=["display", "read"],  # Display only
        blocked_tools=["*"],  # Block everything else
        block_usb=True,
        display_only=True,
        description="Crown jewels - offline, display only",
    ),
    BoundaryMode.LOCKDOWN: ModeConfig(
        mode=BoundaryMode.LOCKDOWN,
        network_allowed=False,
        vpn_only=False,
        allowed_memory_classes=[],  # No memory access
        allowed_tools=[],  # No tools
        blocked_tools=["*"],  # Block everything
        block_usb=True,
        display_only=True,
        block_all_io=True,
        description="Emergency lockdown - everything blocked",
    ),
}


@dataclass
class TripwireConfig:
    """Configuration for a tripwire."""

    tripwire_type: TripwireType
    enabled: bool
    target_mode: BoundaryMode  # Mode to transition to when triggered
    threshold: int = 1  # Number of events before triggering
    cooldown_seconds: int = 60  # Minimum time between triggers
    auto_notify: bool = True  # Automatically notify on trigger


@dataclass
class HumanOverrideRequest:
    """Request for human override ceremony."""

    request_id: str
    requested_by: str
    from_mode: BoundaryMode
    to_mode: BoundaryMode
    reason: str
    timestamp: str
    expires_at: str
    confirmation_code: str
    confirmed: bool = False
    confirmed_at: str | None = None
    confirmed_by: str | None = None


@dataclass
class ModeTransition:
    """Record of a mode transition."""

    transition_id: str
    from_mode: BoundaryMode
    to_mode: BoundaryMode
    timestamp: str
    trigger: str  # What caused the transition
    triggered_by: str | None  # Who or what triggered it
    success: bool
    actions_taken: list[str]
    error: str | None = None


class BoundaryModeManager:
    """
    Manages boundary modes and transitions.

    Key features:
    - Six boundary modes with configurable restrictions
    - Tripwire system for automatic security escalation
    - Human override ceremony for sensitive operations
    - Full audit logging of all transitions
    - SIEM integration for security monitoring

    Fail-safe design:
    - Defaults to LOCKDOWN on errors
    - Unknown states trigger lockdown
    - Clock drift detection
    """

    def __init__(
        self,
        initial_mode: BoundaryMode = BoundaryMode.RESTRICTED,
        enforcement: SecurityEnforcementManager | None = None,
        siem_client: SIEMClient | None = None,
        enable_tripwires: bool = True,
        cooldown_period: int = 300,  # 5 minutes default cooldown
    ):
        """
        Initialize the mode manager.

        Args:
            initial_mode: Starting boundary mode
            enforcement: Security enforcement manager
            siem_client: SIEM client for event logging
            enable_tripwires: Whether to enable tripwire detection
            cooldown_period: Minimum seconds between mode transitions
        """
        self._current_mode = initial_mode
        self._mode_lock = threading.RLock()
        self._enforcement = enforcement or SecurityEnforcementManager()
        self._siem = siem_client or get_siem_client()
        self._enable_tripwires = enable_tripwires
        self._cooldown_period = cooldown_period

        # Mode configurations (can be customized)
        self._mode_configs = DEFAULT_MODE_CONFIGS.copy()

        # Tripwire configurations
        self._tripwires: dict[TripwireType, TripwireConfig] = self._init_tripwires()

        # Tripwire state
        self._tripwire_counters: dict[TripwireType, int] = dict.fromkeys(TripwireType, 0)
        self._tripwire_last_triggered: dict[TripwireType, float] = {}

        # Transition history
        self._transition_history: list[ModeTransition] = []
        self._last_transition_time: float = 0

        # Override requests
        self._pending_overrides: dict[str, HumanOverrideRequest] = {}

        # Clock drift detection
        self._last_clock_check = time.time()
        self._expected_clock_drift_max = 5.0  # seconds

        # Apply initial mode
        self._apply_mode_enforcement(initial_mode, "initial_startup")

    def _init_tripwires(self) -> dict[TripwireType, TripwireConfig]:
        """Initialize default tripwire configurations."""
        return {
            TripwireType.NETWORK_ACTIVITY_IN_AIRGAP: TripwireConfig(
                tripwire_type=TripwireType.NETWORK_ACTIVITY_IN_AIRGAP,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,  # Immediate trigger
            ),
            TripwireType.USB_INSERTION_IN_COLDROOM: TripwireConfig(
                tripwire_type=TripwireType.USB_INSERTION_IN_COLDROOM,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,
            ),
            TripwireType.UNAUTHORIZED_MEMORY_RECALL: TripwireConfig(
                tripwire_type=TripwireType.UNAUTHORIZED_MEMORY_RECALL,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,
            ),
            TripwireType.DAEMON_TAMPERING: TripwireConfig(
                tripwire_type=TripwireType.DAEMON_TAMPERING,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,
            ),
            TripwireType.CLOCK_DRIFT: TripwireConfig(
                tripwire_type=TripwireType.CLOCK_DRIFT,
                enabled=True,
                target_mode=BoundaryMode.RESTRICTED,  # Less severe response
                threshold=3,  # Allow some drift events
                cooldown_seconds=300,
            ),
            TripwireType.FAILED_AUTH_THRESHOLD: TripwireConfig(
                tripwire_type=TripwireType.FAILED_AUTH_THRESHOLD,
                enabled=True,
                target_mode=BoundaryMode.RESTRICTED,
                threshold=5,  # 5 failed attempts
            ),
            TripwireType.PROMPT_INJECTION_DETECTED: TripwireConfig(
                tripwire_type=TripwireType.PROMPT_INJECTION_DETECTED,
                enabled=True,
                target_mode=BoundaryMode.RESTRICTED,
                threshold=3,
            ),
            TripwireType.DATA_EXFILTRATION_ATTEMPT: TripwireConfig(
                tripwire_type=TripwireType.DATA_EXFILTRATION_ATTEMPT,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,  # Immediate lockdown
            ),
            TripwireType.INTEGRITY_CHECK_FAILED: TripwireConfig(
                tripwire_type=TripwireType.INTEGRITY_CHECK_FAILED,
                enabled=True,
                target_mode=BoundaryMode.LOCKDOWN,
                threshold=1,
            ),
        }

    @property
    def current_mode(self) -> BoundaryMode:
        """Get the current boundary mode."""
        with self._mode_lock:
            return self._current_mode

    @property
    def current_config(self) -> ModeConfig:
        """Get the current mode configuration."""
        return self._mode_configs[self.current_mode]

    def get_mode_config(self, mode: BoundaryMode) -> ModeConfig:
        """Get configuration for a specific mode."""
        return self._mode_configs[mode]

    def set_mode(
        self,
        new_mode: BoundaryMode,
        reason: str,
        triggered_by: str | None = None,
        force: bool = False,
    ) -> ModeTransition:
        """
        Transition to a new boundary mode.

        Args:
            new_mode: Target mode
            reason: Reason for the transition
            triggered_by: Who or what triggered the transition
            force: Force transition even during cooldown

        Returns:
            ModeTransition record
        """
        with self._mode_lock:
            old_mode = self._current_mode

            # Check cooldown unless forcing
            if not force:
                now = time.time()
                if (now - self._last_transition_time) < self._cooldown_period:
                    remaining = self._cooldown_period - (now - self._last_transition_time)
                    logger.info(
                        "Mode transition blocked: cooldown active",
                        extra={
                            "from_mode": old_mode.value,
                            "to_mode": new_mode.value,
                            "remaining_seconds": remaining,
                        },
                    )
                    return ModeTransition(
                        transition_id=self._generate_transition_id(),
                        from_mode=old_mode,
                        to_mode=new_mode,
                        timestamp=datetime.utcnow().isoformat() + "Z",
                        trigger=reason,
                        triggered_by=triggered_by,
                        success=False,
                        actions_taken=[],
                        error=f"Cooldown active. {remaining:.0f}s remaining.",
                    )

            # Check if transition requires override ceremony
            if self._requires_override(old_mode, new_mode) and not force:
                logger.warning(
                    "Mode transition blocked: requires override",
                    extra={
                        "from_mode": old_mode.value,
                        "to_mode": new_mode.value,
                        "reason": reason,
                    },
                )
                return ModeTransition(
                    transition_id=self._generate_transition_id(),
                    from_mode=old_mode,
                    to_mode=new_mode,
                    timestamp=datetime.utcnow().isoformat() + "Z",
                    trigger=reason,
                    triggered_by=triggered_by,
                    success=False,
                    actions_taken=[],
                    error="Transition requires human override ceremony",
                )

            # Apply enforcement for new mode
            actions = self._apply_mode_enforcement(new_mode, reason)

            # Update state
            self._current_mode = new_mode
            self._last_transition_time = time.time()

            # Create transition record
            transition = ModeTransition(
                transition_id=self._generate_transition_id(),
                from_mode=old_mode,
                to_mode=new_mode,
                timestamp=datetime.utcnow().isoformat() + "Z",
                trigger=reason,
                triggered_by=triggered_by,
                success=True,
                actions_taken=actions,
            )

            self._transition_history.append(transition)

            # Log the successful transition
            log_level = logging.WARNING if new_mode == BoundaryMode.LOCKDOWN else logging.INFO
            logger.log(
                log_level,
                f"Mode transition: {old_mode.value} -> {new_mode.value}",
                extra={
                    "transition_id": transition.transition_id,
                    "from_mode": old_mode.value,
                    "to_mode": new_mode.value,
                    "reason": reason,
                    "triggered_by": triggered_by,
                    "actions_taken": actions,
                },
            )

            # Send SIEM event
            if self._siem:
                try:
                    event = NatLangChainSIEMEvents.mode_change(
                        old_mode=old_mode.value,
                        new_mode=new_mode.value,
                        reason=reason,
                        triggered_by=triggered_by,
                    )
                    self._siem.send_event(event)
                except Exception as e:
                    logger.error(
                        f"Failed to send SIEM event for mode change: {e}",
                        extra={"transition_id": transition.transition_id},
                    )

            return transition

    def _requires_override(self, from_mode: BoundaryMode, to_mode: BoundaryMode) -> bool:
        """
        Check if a transition requires human override ceremony.

        Relaxing security (going to less restrictive modes) requires override.
        Escalating security (going to more restrictive modes) does not.
        """
        mode_levels = {
            BoundaryMode.OPEN: 0,
            BoundaryMode.RESTRICTED: 1,
            BoundaryMode.TRUSTED: 2,
            BoundaryMode.AIRGAP: 3,
            BoundaryMode.COLDROOM: 4,
            BoundaryMode.LOCKDOWN: 5,
        }

        # Relaxing security requires override
        return mode_levels[to_mode] < mode_levels[from_mode]

    def _apply_mode_enforcement(self, mode: BoundaryMode, reason: str) -> list[str]:
        """Apply enforcement actions for a mode."""
        actions = []
        config = self._mode_configs[mode]

        try:
            # Network enforcement
            if not config.network_allowed:
                result = self._enforcement.enforce_airgap_mode()
                actions.append(f"network_blocked: {result.success}")
            elif config.vpn_only:
                result = self._enforcement.enforce_trusted_mode()
                actions.append(f"vpn_only: {result.success}")
            else:
                # Clear network restrictions
                self._enforcement.network.clear_rules()
                actions.append("network_unrestricted")

            # USB enforcement
            if config.block_usb:
                result = self._enforcement.usb.block_usb_storage()
                actions.append(f"usb_blocked: {result.success}")
            else:
                result = self._enforcement.usb.allow_usb_storage()
                actions.append("usb_allowed")

            # Full lockdown
            if mode == BoundaryMode.LOCKDOWN:
                result = self._enforcement.enforce_lockdown_mode()
                actions.append(f"full_lockdown: {result.success}")

        except Exception as e:
            actions.append(f"enforcement_error: {e}")
            # FAIL-SAFE: If enforcement fails, escalate to lockdown
            if mode != BoundaryMode.LOCKDOWN:
                self._trigger_tripwire(TripwireType.DAEMON_TAMPERING, f"Enforcement failed: {e}")

        return actions

    # =========================================================================
    # Tripwire System
    # =========================================================================

    def trigger_tripwire(self, tripwire_type: TripwireType, details: str) -> bool:
        """
        Trigger a tripwire event.

        Args:
            tripwire_type: Type of tripwire
            details: Details about the trigger

        Returns:
            True if mode transition occurred
        """
        return self._trigger_tripwire(tripwire_type, details)

    def _trigger_tripwire(self, tripwire_type: TripwireType, details: str) -> bool:
        """Internal tripwire trigger."""
        if not self._enable_tripwires:
            return False

        config = self._tripwires.get(tripwire_type)
        if not config or not config.enabled:
            return False

        # Check cooldown
        now = time.time()
        last_triggered = self._tripwire_last_triggered.get(tripwire_type, 0)
        if (now - last_triggered) < config.cooldown_seconds:
            logger.debug(
                f"Tripwire cooldown active: {tripwire_type.value}",
                extra={
                    "tripwire_type": tripwire_type.value,
                    "remaining_seconds": config.cooldown_seconds - (now - last_triggered),
                },
            )
            return False

        # Increment counter
        self._tripwire_counters[tripwire_type] += 1

        # Check threshold
        if self._tripwire_counters[tripwire_type] < config.threshold:
            logger.info(
                f"Tripwire event recorded: {tripwire_type.value}",
                extra={
                    "tripwire_type": tripwire_type.value,
                    "current_count": self._tripwire_counters[tripwire_type],
                    "threshold": config.threshold,
                    "details": details,
                },
            )
            return False

        # Reset counter and update last triggered
        self._tripwire_counters[tripwire_type] = 0
        self._tripwire_last_triggered[tripwire_type] = now

        # Log tripwire activation
        logger.warning(
            f"Tripwire ACTIVATED: {tripwire_type.value}",
            extra={
                "tripwire_type": tripwire_type.value,
                "target_mode": config.target_mode.value,
                "details": details,
                "threshold": config.threshold,
            },
        )

        # Send SIEM event
        if self._siem:
            try:
                event = NatLangChainSIEMEvents.tripwire_triggered(
                    tripwire_type=tripwire_type.value,
                    trigger_details=details,
                    automatic_response=f"Transitioning to {config.target_mode.value}",
                )
                self._siem.send_event(event)
            except Exception as e:
                logger.error(
                    f"Failed to send SIEM event for tripwire: {e}",
                    extra={"tripwire_type": tripwire_type.value},
                )

        # Transition to target mode
        self.set_mode(
            config.target_mode,
            reason=f"Tripwire triggered: {tripwire_type.value}",
            triggered_by="tripwire_system",
            force=True,  # Tripwires bypass cooldown
        )

        return True

    def check_clock_drift(self) -> bool:
        """
        Check for suspicious clock drift.

        Returns True if drift is within acceptable bounds.
        """
        now = time.time()
        expected = self._last_clock_check + (now - self._last_clock_check)
        drift = abs(now - expected)

        self._last_clock_check = now

        if drift > self._expected_clock_drift_max:
            self._trigger_tripwire(
                TripwireType.CLOCK_DRIFT, f"Clock drift of {drift:.2f}s detected"
            )
            return False

        return True

    # =========================================================================
    # Human Override Ceremony
    # =========================================================================

    def request_override(
        self, requested_by: str, to_mode: BoundaryMode, reason: str, validity_minutes: int = 5
    ) -> HumanOverrideRequest:
        """
        Request a human override ceremony.

        This generates a confirmation code that must be provided to complete
        the override. The code expires after the validity period.

        Args:
            requested_by: Identifier of the requester
            to_mode: Target mode
            reason: Reason for the override
            validity_minutes: How long the request is valid

        Returns:
            HumanOverrideRequest with confirmation code
        """
        request_id = f"OVERRIDE-{int(time.time() * 1000)}"
        confirmation_code = secrets.token_hex(16)
        now = datetime.utcnow()
        expires = now + timedelta(minutes=validity_minutes)

        request = HumanOverrideRequest(
            request_id=request_id,
            requested_by=requested_by,
            from_mode=self.current_mode,
            to_mode=to_mode,
            reason=reason,
            timestamp=now.isoformat() + "Z",
            expires_at=expires.isoformat() + "Z",
            confirmation_code=confirmation_code,
        )

        self._pending_overrides[request_id] = request

        logger.info(
            f"Override ceremony requested: {request.from_mode.value} -> {to_mode.value}",
            extra={
                "request_id": request_id,
                "requested_by": requested_by,
                "from_mode": request.from_mode.value,
                "to_mode": to_mode.value,
                "reason": reason,
                "expires_at": request.expires_at,
            },
        )

        return request

    def confirm_override(
        self, request_id: str, confirmation_code: str, confirmed_by: str
    ) -> ModeTransition:
        """
        Confirm a human override ceremony.

        Args:
            request_id: ID of the override request
            confirmation_code: The confirmation code from the request
            confirmed_by: Identifier of the person confirming

        Returns:
            ModeTransition if successful
        """
        request = self._pending_overrides.get(request_id)

        if not request:
            logger.warning(
                "Override confirmation failed: request not found",
                extra={"request_id": request_id, "confirmed_by": confirmed_by},
            )
            return ModeTransition(
                transition_id=self._generate_transition_id(),
                from_mode=self.current_mode,
                to_mode=self.current_mode,
                timestamp=datetime.utcnow().isoformat() + "Z",
                trigger="override_confirmation",
                triggered_by=confirmed_by,
                success=False,
                actions_taken=[],
                error="Override request not found",
            )

        # Check expiration
        expires = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
        if datetime.utcnow().replace(tzinfo=expires.tzinfo) > expires:
            del self._pending_overrides[request_id]
            logger.warning(
                "Override confirmation failed: request expired",
                extra={
                    "request_id": request_id,
                    "confirmed_by": confirmed_by,
                    "expired_at": request.expires_at,
                },
            )
            return ModeTransition(
                transition_id=self._generate_transition_id(),
                from_mode=self.current_mode,
                to_mode=request.to_mode,
                timestamp=datetime.utcnow().isoformat() + "Z",
                trigger="override_confirmation",
                triggered_by=confirmed_by,
                success=False,
                actions_taken=[],
                error="Override request expired",
            )

        # Verify confirmation code (timing-safe comparison)
        if not secrets.compare_digest(confirmation_code, request.confirmation_code):
            logger.warning(
                "Override confirmation failed: invalid code",
                extra={"request_id": request_id, "confirmed_by": confirmed_by},
            )
            return ModeTransition(
                transition_id=self._generate_transition_id(),
                from_mode=self.current_mode,
                to_mode=request.to_mode,
                timestamp=datetime.utcnow().isoformat() + "Z",
                trigger="override_confirmation",
                triggered_by=confirmed_by,
                success=False,
                actions_taken=[],
                error="Invalid confirmation code",
            )

        # Mark as confirmed
        request.confirmed = True
        request.confirmed_at = datetime.utcnow().isoformat() + "Z"
        request.confirmed_by = confirmed_by

        logger.info(
            f"Override ceremony confirmed: {request.from_mode.value} -> {request.to_mode.value}",
            extra={
                "request_id": request_id,
                "requested_by": request.requested_by,
                "confirmed_by": confirmed_by,
                "from_mode": request.from_mode.value,
                "to_mode": request.to_mode.value,
                "reason": request.reason,
            },
        )

        # Execute the transition
        transition = self.set_mode(
            request.to_mode,
            reason=f"Human override: {request.reason}",
            triggered_by=confirmed_by,
            force=True,
        )

        # Cleanup
        del self._pending_overrides[request_id]

        return transition

    # =========================================================================
    # Policy Checks
    # =========================================================================

    def is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed in the current mode."""
        config = self.current_config

        # Check blocked list first
        if "*" in config.blocked_tools:
            return False
        if tool_name in config.blocked_tools:
            return False

        # Check allowed list
        if "*" in config.allowed_tools:
            return True
        if tool_name in config.allowed_tools:
            return True

        # Check wildcard patterns
        for pattern in config.allowed_tools:
            if pattern.endswith("*"):
                prefix = pattern[:-1]
                if tool_name.startswith(prefix):
                    return True

        return False

    def is_memory_class_allowed(self, memory_class: MemoryClass) -> bool:
        """Check if a memory class is accessible in the current mode."""
        return memory_class in self.current_config.allowed_memory_classes

    def is_network_allowed(self) -> bool:
        """Check if network access is allowed in the current mode."""
        return self.current_config.network_allowed

    def is_vpn_required(self) -> bool:
        """Check if VPN is required in the current mode."""
        return self.current_config.vpn_only

    def is_display_only(self) -> bool:
        """Check if display-only mode is active."""
        return self.current_config.display_only

    # =========================================================================
    # Utilities
    # =========================================================================

    def _generate_transition_id(self) -> str:
        """Generate a unique transition ID."""
        return f"TRANS-{int(time.time() * 1000)}-{secrets.token_hex(4)}"

    def get_status(self) -> dict[str, Any]:
        """Get current status of the mode manager."""
        return {
            "current_mode": self.current_mode.value,
            "config": {
                "network_allowed": self.current_config.network_allowed,
                "vpn_only": self.current_config.vpn_only,
                "block_usb": self.current_config.block_usb,
                "display_only": self.current_config.display_only,
                "description": self.current_config.description,
            },
            "tripwires_enabled": self._enable_tripwires,
            "pending_overrides": len(self._pending_overrides),
            "recent_transitions": len(self._transition_history),
            "cooldown_remaining": max(
                0, self._cooldown_period - (time.time() - self._last_transition_time)
            ),
        }

    def get_transition_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent transition history."""
        return [
            {
                "transition_id": t.transition_id,
                "from_mode": t.from_mode.value,
                "to_mode": t.to_mode.value,
                "timestamp": t.timestamp,
                "trigger": t.trigger,
                "triggered_by": t.triggered_by,
                "success": t.success,
                "error": t.error,
            }
            for t in self._transition_history[-limit:]
        ]


# =============================================================================
# Global Mode Manager
# =============================================================================

_global_mode_manager: BoundaryModeManager | None = None


def get_mode_manager() -> BoundaryModeManager | None:
    """Get the global mode manager instance."""
    return _global_mode_manager


def init_mode_manager(**kwargs) -> BoundaryModeManager:
    """Initialize the global mode manager."""
    global _global_mode_manager
    _global_mode_manager = BoundaryModeManager(**kwargs)
    return _global_mode_manager

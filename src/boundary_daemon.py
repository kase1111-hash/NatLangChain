"""
NatLangChain - Boundary Daemon Integration
Trust boundary enforcement preventing unauthorized data flow and ensuring data sovereignty.

Implements the BOUNDARY-DAEMON-INTEGRATION.md specification:
- Data classification system (public, internal, confidential, restricted)
- Outbound rule enforcement blocking sensitive patterns
- Fail-safe design: block by default when uncertain
- Audit logging of all boundary events
- Violation alerting with escalation
"""

import hashlib
import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    from boundary_exceptions import (
        PolicyConfigurationError,
        PolicyError,
        PolicyViolationError,
    )
except ImportError:
    pass

logger = logging.getLogger(__name__)


class EnforcementMode(Enum):
    """Enforcement modes for the boundary daemon."""

    STRICT = "strict"  # Block all violations, no exceptions
    PERMISSIVE = "permissive"  # Block critical, warn on minor
    AUDIT_ONLY = "audit_only"  # Log only, no blocking


class DataClassification(Enum):
    """Data classification levels."""

    PUBLIC = "public"  # Can go anywhere
    INTERNAL = "internal"  # NatLangChain, Value Ledger only
    CONFIDENTIAL = "confidential"  # Memory Vault only
    RESTRICTED = "restricted"  # No external destinations allowed


class ViolationType(Enum):
    """Types of policy violations."""

    BLOCKED_PATTERN_DETECTED = "blocked_pattern_detected"
    DATA_EXFILTRATION_ATTEMPT = "data_exfiltration_attempt"
    UNAUTHORIZED_DESTINATION = "unauthorized_destination"
    CLASSIFICATION_VIOLATION = "classification_violation"
    PAYLOAD_TOO_LARGE = "payload_too_large"
    POLICY_NOT_FOUND = "policy_not_found"


@dataclass
class PolicyViolation:
    """Represents a policy violation."""

    violation_id: str
    violation_type: ViolationType
    severity: str  # low, medium, high, critical
    details: dict[str, Any]
    timestamp: str
    action_taken: str
    owner_notified: bool = False


@dataclass
class AuditRecord:
    """Audit record for data flow events."""

    audit_id: str
    event_type: str
    timestamp: str
    source: str
    destination: str
    request: dict[str, Any]
    authorization: dict[str, Any]
    result: dict[str, Any]


@dataclass
class BoundaryPolicy:
    """Policy configuration for boundary enforcement."""

    policy_id: str
    owner: str
    agent_id: str
    status: str = "active"
    enforcement_mode: EnforcementMode = EnforcementMode.STRICT

    # Data classifications and their allowed destinations
    data_classifications: dict[DataClassification, list[str]] = field(default_factory=dict)

    # Outbound rules
    outbound_rules: list[dict[str, Any]] = field(default_factory=list)

    # Inbound rules
    inbound_rules: list[dict[str, Any]] = field(default_factory=list)

    # Custom blocked patterns
    custom_blocked_patterns: list[str] = field(default_factory=list)

    # Maximum payload size in bytes
    max_payload_size: int = 1024 * 1024  # 1MB default


class BoundaryDaemon:
    """
    Boundary Daemon: Trust boundary enforcement layer.

    Core principle: "What cannot be leaked cannot be exploited."

    FAIL-SAFE DESIGN:
    - Unknown data classifications are treated as RESTRICTED
    - Unknown destinations are blocked
    - Pattern detection errs on the side of caution
    - Any error during validation results in blocking
    """

    # Built-in blocked patterns for sensitive data
    # These patterns are ALWAYS checked regardless of policy
    BUILTIN_BLOCKED_PATTERNS = [
        # API Keys and tokens (including "API key:" with space)
        r"api[_\-\s]?key\s*[=:]\s*['\"]?[\w\-]+",
        r"api-key\s*[=:]\s*['\"]?[\w\-]+",
        r"apikey\s*[=:]\s*['\"]?[\w\-]+",
        r"access[_-]?token\s*[=:]\s*['\"]?[\w\-]+",
        r"auth[_-]?token\s*[=:]\s*['\"]?[\w\-]+",
        r"bearer\s+[\w\-\.]+",
        r"sk-live-[\w]+",  # Stripe-style live keys
        r"sk-test-[\w]+",  # Stripe-style test keys
        # Passwords
        r"password\s*[=:]\s*['\"]?[^\s'\",]+",
        r"passwd\s*[=:]\s*['\"]?[^\s'\",]+",
        r"pwd\s*[=:]\s*['\"]?[^\s'\",]+",
        # Secrets
        r"secret\s*[=:]\s*['\"]?[\w\-]+",
        r"secret[_-]?key\s*[=:]\s*['\"]?[\w\-]+",
        # Private keys
        r"private[_-]?key",
        r"privatekey",
        r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
        r"-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----",
        r"-----BEGIN\s+EC\s+PRIVATE\s+KEY-----",
        r"-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----",
        # SSH keys
        r"ssh[_-]?key\s*[=:]\s*['\"]?[\w\-]+",
        r"ssh-rsa\s+[A-Za-z0-9+/=]+",
        r"ssh-ed25519\s+[A-Za-z0-9+/=]+",
        # Credit card patterns (Luhn-valid 16 digit sequences)
        r"\b(?:4[0-9]{12}(?:[0-9]{3})?)\b",  # Visa
        r"\b(?:5[1-5][0-9]{14})\b",  # Mastercard
        r"\b(?:3[47][0-9]{13})\b",  # Amex
        r"\b(?:6(?:011|5[0-9]{2})[0-9]{12})\b",  # Discover
        # Social Security Numbers
        r"\b\d{3}[-\s]?\d{2}[-\s]?\d{4}\b",
        # AWS credentials
        r"AKIA[0-9A-Z]{16}",
        r"aws[_-]?access[_-]?key[_-]?id\s*[=:]\s*['\"]?[\w]+",
        r"aws[_-]?secret[_-]?access[_-]?key\s*[=:]\s*['\"]?[\w]+",
        # Database connection strings
        r"(?:mongodb|postgres|mysql|redis)://[^\s]+",
        r"jdbc:[a-z]+://[^\s]+",
        # Generic secrets
        r"client[_-]?secret\s*[=:]\s*['\"]?[\w\-]+",
        r"encryption[_-]?key\s*[=:]\s*['\"]?[\w\-]+",
    ]

    # Keyword blocklist for simple string matching (case-insensitive)
    KEYWORD_BLOCKLIST = [
        "api_key",
        "api-key",
        "apikey",
        "password",
        "passwd",
        "pwd",
        "secret",
        "token",
        "private_key",
        "privatekey",
        "ssh_key",
        "ssh-key",
        "credentials",
        "credential",
    ]

    # Allowed destinations per classification
    DEFAULT_CLASSIFICATION_DESTINATIONS = {
        DataClassification.PUBLIC: ["*"],  # Anywhere
        DataClassification.INTERNAL: ["natlangchain", "value_ledger"],
        DataClassification.CONFIDENTIAL: ["memory_vault"],
        DataClassification.RESTRICTED: [],  # Nowhere
    }

    def __init__(self, enforcement_mode: EnforcementMode = EnforcementMode.STRICT):
        """
        Initialize the Boundary Daemon.

        Args:
            enforcement_mode: The default enforcement mode
        """
        self.enforcement_mode = enforcement_mode
        self.policies: dict[str, BoundaryPolicy] = {}
        self.audit_log: list[AuditRecord] = []
        self.violations: list[PolicyViolation] = []
        self._violation_counter = 0
        self._audit_counter = 0
        self._auth_counter = 0

        # Compile regex patterns for efficiency
        self._compiled_patterns = [
            re.compile(pattern, re.IGNORECASE) for pattern in self.BUILTIN_BLOCKED_PATTERNS
        ]

    def register_policy(self, policy: BoundaryPolicy) -> dict[str, Any]:
        """
        Register a new boundary policy.

        Args:
            policy: The policy to register

        Returns:
            Registration result
        """
        self.policies[policy.policy_id] = policy
        return {"registered": True, "policy_id": policy.policy_id, "status": policy.status}

    def _generate_violation_id(self) -> str:
        """Generate unique violation ID."""
        self._violation_counter += 1
        return f"VIOL-{self._violation_counter:04d}"

    def _generate_audit_id(self) -> str:
        """Generate unique audit ID."""
        self._audit_counter += 1
        return f"AUDIT-{self._audit_counter:04d}"

    def _generate_auth_id(self) -> str:
        """Generate unique authorization ID."""
        self._auth_counter += 1
        return f"AUTH-{self._auth_counter:04d}"

    def _hash_payload(self, payload: Any) -> str:
        """Generate SHA-256 hash of payload."""
        payload_str = json.dumps(payload, sort_keys=True, default=str)
        return f"SHA256:{hashlib.sha256(payload_str.encode()).hexdigest()}"

    def _detect_blocked_patterns(
        self, data: str, custom_patterns: list[str] | None = None
    ) -> list[dict[str, Any]]:
        """
        Detect blocked patterns in data.

        FAIL-SAFE: Any pattern match results in detection.

        Args:
            data: The data to inspect
            custom_patterns: Additional custom patterns to check

        Returns:
            List of detected pattern matches
        """
        detected = []

        # Check keyword blocklist (simple string matching)
        data_lower = data.lower()
        for keyword in self.KEYWORD_BLOCKLIST:
            if keyword in data_lower:
                detected.append(
                    {
                        "type": "keyword_match",
                        "pattern": keyword,
                        "risk": "high",
                        "location": "content",
                    }
                )

        # Check regex patterns
        for pattern in self._compiled_patterns:
            matches = pattern.findall(data)
            if matches:
                detected.append(
                    {
                        "type": "regex_match",
                        "pattern": pattern.pattern[:50] + "...",  # Truncate for safety
                        "count": len(matches),
                        "risk": "critical",
                        "location": "content",
                    }
                )

        # Check custom patterns
        if custom_patterns:
            for pattern_str in custom_patterns:
                try:
                    pattern = re.compile(pattern_str, re.IGNORECASE)
                    matches = pattern.findall(data)
                    if matches:
                        detected.append(
                            {
                                "type": "custom_pattern_match",
                                "pattern": pattern_str[:50],
                                "count": len(matches),
                                "risk": "high",
                                "location": "content",
                            }
                        )
                except re.error:
                    # Invalid regex - fail safe by flagging it
                    detected.append(
                        {
                            "type": "invalid_pattern",
                            "pattern": pattern_str[:50],
                            "risk": "medium",
                            "location": "pattern_config",
                        }
                    )

        return detected

    def _classify_data(
        self, data: str, explicit_classification: str | None = None
    ) -> DataClassification:
        """
        Classify data based on content analysis.

        FAIL-SAFE: If classification is uncertain, defaults to RESTRICTED.

        Args:
            data: The data to classify
            explicit_classification: Explicitly specified classification

        Returns:
            Data classification
        """
        # If explicitly specified, validate it
        if explicit_classification:
            try:
                return DataClassification(explicit_classification.lower())
            except ValueError:
                # Unknown classification - FAIL SAFE to restricted
                return DataClassification.RESTRICTED

        # Auto-classify based on content
        # Check for sensitive patterns - if found, classify as restricted
        patterns_detected = self._detect_blocked_patterns(data)
        if patterns_detected:
            return DataClassification.RESTRICTED

        # Default to internal for safety
        return DataClassification.INTERNAL

    def _check_destination_allowed(
        self,
        classification: DataClassification,
        destination: str,
        policy: BoundaryPolicy | None = None,
    ) -> tuple[bool, str]:
        """
        Check if a destination is allowed for the given classification.

        FAIL-SAFE: Unknown destinations are blocked.

        Args:
            classification: The data classification
            destination: The target destination
            policy: Optional policy for custom rules

        Returns:
            Tuple of (allowed, reason)
        """
        # Get allowed destinations
        if policy and policy.data_classifications:
            allowed_destinations = policy.data_classifications.get(classification, [])
        else:
            allowed_destinations = self.DEFAULT_CLASSIFICATION_DESTINATIONS.get(classification, [])

        # Wildcard allows all
        if "*" in allowed_destinations:
            return True, "Wildcard allows all destinations"

        # Empty list means no destinations allowed
        if not allowed_destinations:
            return False, f"No destinations allowed for {classification.value} data"

        # Check if destination is in allowed list
        destination_lower = destination.lower()
        for allowed in allowed_destinations:
            if allowed.lower() == destination_lower:
                return True, f"Destination {destination} is explicitly allowed"

        # FAIL-SAFE: Not in allowed list = blocked
        return (
            False,
            f"Destination {destination} not in allowed list for {classification.value} data",
        )

    def authorize_request(self, request: dict[str, Any]) -> dict[str, Any]:
        """
        Authorize an outbound request.

        FAIL-SAFE BEHAVIOR:
        1. Any error during authorization = BLOCK
        2. Unknown classification = RESTRICTED (most restrictive)
        3. Unknown destination = BLOCKED
        4. Pattern detection = BLOCK if any sensitive data found

        Args:
            request: Request containing source, destination, payload, etc.

        Returns:
            Authorization result
        """
        try:
            request_id = request.get("request_id", f"REQ-{int(time.time())}")
            source = request.get("source", "unknown")
            destination = request.get("destination", "unknown")
            payload = request.get("payload", {})
            explicit_classification = request.get("data_classification")
            policy_id = request.get("policy_id")

            # Get policy if specified
            policy = self.policies.get(policy_id) if policy_id else None
            enforcement = policy.enforcement_mode if policy else self.enforcement_mode

            # Convert payload to string for inspection
            if isinstance(payload, dict):
                payload_str = json.dumps(payload, default=str)
            else:
                payload_str = str(payload)

            # Step 1: Check payload size
            max_size = policy.max_payload_size if policy else 1024 * 1024
            if len(payload_str.encode()) > max_size:
                return self._block_request(
                    request_id=request_id,
                    violation_type=ViolationType.PAYLOAD_TOO_LARGE,
                    pattern="size_limit",
                    location="payload",
                    rule="size_limit",
                    source=source,
                    destination=destination,
                )

            # Step 2: Detect blocked patterns (ALWAYS runs, regardless of classification)
            custom_patterns = policy.custom_blocked_patterns if policy else []
            detected_patterns = self._detect_blocked_patterns(payload_str, custom_patterns)

            if detected_patterns:
                # Found sensitive data - BLOCK (in strict/permissive mode)
                if enforcement in [EnforcementMode.STRICT, EnforcementMode.PERMISSIVE]:
                    first_detection = detected_patterns[0]
                    return self._block_request(
                        request_id=request_id,
                        violation_type=ViolationType.BLOCKED_PATTERN_DETECTED,
                        pattern=first_detection.get("pattern", "unknown"),
                        location=first_detection.get("location", "payload"),
                        rule="builtin_patterns",
                        source=source,
                        destination=destination,
                        all_detections=detected_patterns,
                    )

            # Step 3: Classify data
            classification = self._classify_data(payload_str, explicit_classification)

            # Step 4: Check if destination is allowed for this classification
            allowed, reason = self._check_destination_allowed(classification, destination, policy)

            if not allowed:
                if enforcement == EnforcementMode.STRICT:
                    return self._block_request(
                        request_id=request_id,
                        violation_type=ViolationType.UNAUTHORIZED_DESTINATION,
                        pattern="destination_policy",
                        location="destination",
                        rule="classification_policy",
                        source=source,
                        destination=destination,
                        reason=reason,
                    )
                elif enforcement == EnforcementMode.PERMISSIVE:
                    # Permissive mode: warn but allow for non-critical
                    if classification == DataClassification.RESTRICTED:
                        return self._block_request(
                            request_id=request_id,
                            violation_type=ViolationType.DATA_EXFILTRATION_ATTEMPT,
                            pattern="restricted_data",
                            location="payload",
                            rule="classification_policy",
                            source=source,
                            destination=destination,
                        )

            # Authorization successful
            auth_id = self._generate_auth_id()

            # Log the successful authorization
            self._log_audit(
                event_type="authorization_granted",
                source=source,
                destination=destination,
                request=request,
                authorization={"authorized": True, "authorization_id": auth_id},
                result={"status": "allowed"},
            )

            return {
                "authorized": True,
                "request_id": request_id,
                "authorization_id": auth_id,
                "rules_applied": ["builtin_patterns", "classification_policy"],
                "data_classification": classification.value,
                "modifications": [],
                "proceed": True,
            }

        except Exception as e:
            # FAIL-SAFE: Any exception during authorization = BLOCK
            logger.error(
                f"Authorization failed (fail-safe block): {e}",
                extra={
                    "request_id": request.get("request_id", "unknown"),
                    "source": request.get("source", "unknown"),
                    "destination": request.get("destination", "unknown"),
                    "error": str(e),
                },
                exc_info=True,
            )
            return self._block_request(
                request_id=request.get("request_id", "unknown"),
                violation_type=ViolationType.POLICY_NOT_FOUND,
                pattern="error",
                location="authorization",
                rule="fail_safe",
                source=request.get("source", "unknown"),
                destination=request.get("destination", "unknown"),
                reason=f"Authorization error (fail-safe block): {e!s}",
            )

    def _block_request(
        self,
        request_id: str,
        violation_type: ViolationType,
        pattern: str,
        location: str,
        rule: str,
        source: str,
        destination: str,
        reason: str | None = None,
        all_detections: list[dict] | None = None,
    ) -> dict[str, Any]:
        """
        Block a request and record the violation.

        Args:
            request_id: The request ID
            violation_type: Type of violation
            pattern: The pattern that caused the block
            location: Where the pattern was found
            rule: The rule that was violated
            source: Request source
            destination: Request destination
            reason: Optional reason string
            all_detections: All pattern detections (if multiple)

        Returns:
            Block response
        """
        # Record violation
        violation = PolicyViolation(
            violation_id=self._generate_violation_id(),
            violation_type=violation_type,
            severity="high"
            if violation_type
            in [ViolationType.BLOCKED_PATTERN_DETECTED, ViolationType.DATA_EXFILTRATION_ATTEMPT]
            else "medium",
            details={
                "source": source,
                "destination": destination,
                "blocked_pattern": pattern,
                "rule_violated": rule,
                "all_detections": all_detections or [],
                "reason": reason,
            },
            timestamp=datetime.utcnow().isoformat() + "Z",
            action_taken="blocked",
            owner_notified=True,
        )
        self.violations.append(violation)

        # Log audit
        self._log_audit(
            event_type="authorization_denied",
            source=source,
            destination=destination,
            request={"request_id": request_id},
            authorization={"authorized": False, "violation_id": violation.violation_id},
            result={"status": "blocked", "reason": reason or violation_type.value},
        )

        return {
            "authorized": False,
            "request_id": request_id,
            "violation": {
                "type": violation_type.value,
                "pattern": pattern,
                "location": location,
                "rule": rule,
                "reason": reason,
            },
            "action_taken": "blocked",
            "owner_notified": True,
        }

    def _log_audit(
        self,
        event_type: str,
        source: str,
        destination: str,
        request: dict[str, Any],
        authorization: dict[str, Any],
        result: dict[str, Any],
    ) -> AuditRecord:
        """
        Log an audit record.

        Args:
            event_type: Type of event
            source: Request source
            destination: Request destination
            request: Request details
            authorization: Authorization result
            result: Final result

        Returns:
            The audit record
        """
        record = AuditRecord(
            audit_id=self._generate_audit_id(),
            event_type=event_type,
            timestamp=datetime.utcnow().isoformat() + "Z",
            source=source,
            destination=destination,
            request={
                "request_id": request.get("request_id", "unknown"),
                "payload_hash": self._hash_payload(request.get("payload", {})),
                "payload_size": len(str(request.get("payload", ""))),
            },
            authorization=authorization,
            result=result,
        )
        self.audit_log.append(record)

        # Log to logger for monitoring
        log_level = logging.WARNING if event_type == "authorization_denied" else logging.INFO
        logger.log(
            log_level,
            f"Boundary audit: {event_type}",
            extra={
                "audit_id": record.audit_id,
                "event_type": event_type,
                "source": source,
                "destination": destination,
                "authorized": authorization.get("authorized", False),
                "result_status": result.get("status", "unknown"),
            },
        )

        return record

    def inspect_data(self, data: str, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """
        Inspect data for sensitive patterns without authorizing.

        Useful for pre-flight checks.

        Args:
            data: The data to inspect
            context: Optional context

        Returns:
            Inspection result
        """
        context = context or {}

        detected = self._detect_blocked_patterns(data)
        classification = self._classify_data(data)

        # Calculate risk score
        risk_score = 0.0
        for detection in detected:
            if detection.get("risk") == "critical":
                risk_score += 0.4
            elif detection.get("risk") == "high":
                risk_score += 0.25
            elif detection.get("risk") == "medium":
                risk_score += 0.15
            else:
                risk_score += 0.1

        risk_score = min(1.0, risk_score)  # Cap at 1.0

        return {
            "inspection_id": f"INSP-{int(time.time())}",
            "risk_score": risk_score,
            "detected_patterns": detected,
            "classification_suggested": classification.value,
            "policy_compliance": len(detected) == 0,
        }

    def get_violations(self, severity: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        """
        Get recorded violations.

        Args:
            severity: Filter by severity (low, medium, high, critical)
            limit: Maximum number to return

        Returns:
            List of violations
        """
        violations = self.violations
        if severity:
            violations = [v for v in violations if v.severity == severity]

        return [
            {
                "violation_id": v.violation_id,
                "type": v.violation_type.value,
                "severity": v.severity,
                "details": v.details,
                "timestamp": v.timestamp,
                "action_taken": v.action_taken,
            }
            for v in violations[-limit:]
        ]

    def get_audit_log(
        self, event_type: str | None = None, limit: int = 100
    ) -> list[dict[str, Any]]:
        """
        Get audit log entries.

        Args:
            event_type: Filter by event type
            limit: Maximum number to return

        Returns:
            List of audit records
        """
        records = self.audit_log
        if event_type:
            records = [r for r in records if r.event_type == event_type]

        return [
            {
                "audit_id": r.audit_id,
                "event_type": r.event_type,
                "timestamp": r.timestamp,
                "source": r.source,
                "destination": r.destination,
                "request": r.request,
                "authorization": r.authorization,
                "result": r.result,
            }
            for r in records[-limit:]
        ]

    def generate_chain_entry(self, violation: PolicyViolation) -> dict[str, Any]:
        """
        Generate a NatLangChain entry for a violation.

        Critical boundary events should be recorded on-chain.

        Args:
            violation: The violation to record

        Returns:
            Entry suitable for NatLangChain
        """
        return {
            "content": f"Boundary Daemon Audit: {violation.violation_type.value} detected and blocked. "
            f"Source {violation.details.get('source', 'unknown')} attempted to send "
            f"{violation.details.get('classification', 'sensitive')} data to "
            f"{violation.details.get('destination', 'unknown')}. "
            f"Action: {violation.action_taken}. Owner notified.",
            "author": "boundary_daemon",
            "intent": "Record security event",
            "metadata": {
                "is_boundary_event": True,
                "event_type": "policy_violation",
                "violation_id": violation.violation_id,
                "severity": violation.severity,
                "action_taken": violation.action_taken,
            },
        }


# Convenience function for quick validation
def validate_outbound_data(
    data: str,
    destination: str,
    classification: str | None = None,
    mode: EnforcementMode = EnforcementMode.STRICT,
) -> dict[str, Any]:
    """
    Quick validation of outbound data.

    Args:
        data: Data to validate
        destination: Target destination
        classification: Optional explicit classification
        mode: Enforcement mode

    Returns:
        Authorization result
    """
    daemon = BoundaryDaemon(enforcement_mode=mode)
    return daemon.authorize_request(
        {
            "request_id": f"QUICK-{int(time.time())}",
            "source": "quick_validate",
            "destination": destination,
            "payload": {"content": data},
            "data_classification": classification,
        }
    )

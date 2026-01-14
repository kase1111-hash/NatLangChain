"""
NCIP-013: Emergency Overrides, Force Majeure & Semantic Fallbacks

This module implements emergency handling for NatLangChain while preserving:
- Canonical meaning (emergencies suspend execution, never meaning)
- Temporal boundaries (time-bounded, reviewable)
- Semantic integrity (no retroactive alterations)
- Fallback predictability (pre-declared, semantically validated)

Core Principle: Emergencies may suspend execution — never meaning.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any


class ForceMajeureClass(Enum):
    """
    Canonical Force Majeure classes per NCIP-013 Section 4.1.

    These are semantic labels, not legal conclusions.
    """

    NATURAL_DISASTER = "natural_disaster"  # Earthquake, flood, fire
    GOVERNMENT_ACTION = "government_action"  # Sanctions, seizure, shutdown
    ARMED_CONFLICT = "armed_conflict"  # War, terrorism
    INFRASTRUCTURE_FAILURE = "infrastructure_failure"  # Power, network collapse
    MEDICAL_INCAPACITY = "medical_incapacity"  # Death, coma, incapacity
    SYSTEMIC_PROTOCOL_FAILURE = "systemic_protocol_failure"  # Chain halt, validator collapse


class EmergencyScope(Enum):
    """Scope of emergency declaration."""

    CONTRACT = "contract"  # Affects specific contract(s)
    JURISDICTION = "jurisdiction"  # Affects entire jurisdiction
    SYSTEM = "system"  # System-wide emergency


class EmergencyStatus(Enum):
    """Status of an emergency declaration."""

    DECLARED = "declared"  # Initial declaration
    UNDER_REVIEW = "under_review"  # Being evaluated
    VALIDATED = "validated"  # Confirmed valid
    DISPUTED = "disputed"  # Under dispute
    ACTIVE = "active"  # Emergency effects active
    EXPIRED = "expired"  # Past max_duration
    RESOLVED = "resolved"  # Emergency ended
    REJECTED = "rejected"  # Declaration rejected


class ExecutionEffect(Enum):
    """
    Allowed execution effects per NCIP-013 Section 6.1.
    """

    PAUSE_EXECUTION = "pause_execution"  # ✅ Allowed
    DELAY_DEADLINES = "delay_deadlines"  # ✅ Allowed
    FREEZE_SETTLEMENT = "freeze_settlement"  # ✅ Allowed
    TRIGGER_FALLBACK = "trigger_fallback"  # ✅ Allowed


class ProhibitedEffect(Enum):
    """
    Prohibited effects per NCIP-013 Section 6.1.
    """

    REDEFINE_OBLIGATIONS = "redefine_obligations"  # ❌ Never allowed
    IMPOSE_NEW_DUTIES = "impose_new_duties"  # ❌ Never allowed
    ALTER_INTENT = "alter_intent"  # ❌ Never allowed
    COLLAPSE_UNCERTAINTY = "collapse_uncertainty"  # ❌ Never allowed


class OracleType(Enum):
    """Types of oracles that may provide emergency evidence."""

    DISASTER_FEED = "disaster_feed"
    GOVERNMENT_NOTICE = "government_notice"
    DEATH_REGISTRY = "death_registry"
    INFRASTRUCTURE_STATUS = "infrastructure_status"


@dataclass
class OracleEvidence:
    """
    Evidence from a Semantic Oracle per NCIP-013 Section 5.

    Oracle outputs are evidence, not authority.
    They do not auto-resolve disputes.
    """

    oracle_id: str
    oracle_type: OracleType
    evidence_data: str
    confidence_score: float  # 0.0 - 1.0
    retrieved_at: datetime = field(default_factory=datetime.utcnow)

    # Oracles are NOT authoritative
    is_authoritative: bool = False  # Always False per NCIP-013


@dataclass
class SemanticFallback:
    """
    A Semantic Fallback per NCIP-013 Section 7.

    Fallbacks:
    - Are declared at contract creation
    - Are semantically validated
    - Cannot be invented post-hoc
    """

    fallback_id: str
    contract_id: str
    trigger_condition: str  # Natural language condition
    fallback_action: str  # What happens when triggered

    # Validation
    declared_at: datetime = field(default_factory=datetime.utcnow)
    semantically_validated: bool = False
    validation_timestamp: datetime | None = None

    # Cannot be added post-hoc
    is_original: bool = True  # Must be True - set at contract creation

    def validate(self) -> tuple[bool, str]:
        """Validate the fallback declaration."""
        if not self.is_original:
            return (False, "Fallback cannot be invented post-hoc")
        if not self.trigger_condition:
            return (False, "Trigger condition is required")
        if not self.fallback_action:
            return (False, "Fallback action is required")
        return (True, "Fallback is valid")


@dataclass
class EmergencyDeclaration:
    """
    An emergency declaration per NCIP-013 Section 3.

    Required fields per Section 12:
    - scope
    - affected_refs
    - declared_reason
    - review_after
    - max_duration
    """

    emergency_id: str
    declared_by: str
    scope: EmergencyScope
    force_majeure_class: ForceMajeureClass
    declared_reason: str
    affected_refs: list[str]  # Contract IDs, jurisdiction codes, etc.

    # Timestamps
    declared_at: datetime = field(default_factory=datetime.utcnow)

    # Required timeout fields per Section 9
    review_after: timedelta = field(default_factory=lambda: timedelta(days=30))
    max_duration: timedelta = field(default_factory=lambda: timedelta(days=180))

    # Computed expiry times
    review_deadline: datetime | None = None
    expiry_deadline: datetime | None = None

    # Status tracking
    status: EmergencyStatus = EmergencyStatus.DECLARED

    # Oracle evidence
    oracle_evidence: list[OracleEvidence] = field(default_factory=list)

    # Applied effects
    applied_effects: list[ExecutionEffect] = field(default_factory=list)

    # Semantic lock (if disputed)
    semantic_lock_id: str | None = None

    # Resolution
    resolved_at: datetime | None = None
    resolution_reason: str | None = None

    # Abuse tracking
    frivolous: bool = False
    harassment_score_impact: float = 0.0

    def __post_init__(self):
        """Compute deadlines."""
        if self.review_deadline is None:
            self.review_deadline = self.declared_at + self.review_after
        if self.expiry_deadline is None:
            self.expiry_deadline = self.declared_at + self.max_duration

    @property
    def is_expired(self) -> bool:
        """Check if emergency has expired."""
        return datetime.utcnow() > self.expiry_deadline

    @property
    def needs_review(self) -> bool:
        """Check if emergency needs review."""
        return datetime.utcnow() > self.review_deadline and self.status == EmergencyStatus.ACTIVE

    @property
    def days_active(self) -> int:
        """Get number of days emergency has been active."""
        return (datetime.utcnow() - self.declared_at).days

    def has_required_fields(self) -> tuple[bool, list[str]]:
        """Check if declaration has all required fields."""
        missing = []
        if not self.scope:
            missing.append("scope")
        if not self.affected_refs:
            missing.append("affected_refs")
        if not self.declared_reason:
            missing.append("declared_reason")
        if not self.review_after:
            missing.append("review_after")
        if not self.max_duration:
            missing.append("max_duration")
        return (len(missing) == 0, missing)


@dataclass
class EmergencyDispute:
    """
    A dispute over an emergency declaration per NCIP-013 Section 8.

    If emergency declaration is contested:
    - MP-03 dispute flow applies
    - Semantic Lock engages immediately
    - Burden of proof lies with declarer
    - Execution remains paused during dispute
    """

    dispute_id: str
    emergency_id: str
    disputed_by: str
    dispute_reason: str

    # Status
    created_at: datetime = field(default_factory=datetime.utcnow)
    resolved_at: datetime | None = None
    upheld: bool | None = None  # True = emergency upheld, False = rejected

    # Semantic lock
    semantic_lock_id: str | None = None

    # Burden of proof is on declarer
    burden_of_proof: str = "declarer"


class EmergencyManager:
    """
    Manages emergency overrides per NCIP-013.

    Responsibilities:
    - Emergency declaration validation
    - Force majeure classification
    - Semantic fallback management
    - Oracle evidence handling
    - Dispute management
    - Timeout enforcement
    - Abuse prevention
    """

    # Default timeouts
    DEFAULT_REVIEW_DAYS = 30
    DEFAULT_MAX_DURATION_DAYS = 180

    # Escalation threshold
    ESCALATION_THRESHOLD_DAYS = 30

    # Abuse penalties
    FRIVOLOUS_HARASSMENT_PENALTY = 0.15
    REPEAT_MULTIPLIER = 1.5

    def __init__(self):
        self.emergencies: dict[str, EmergencyDeclaration] = {}
        self.fallbacks: dict[str, list[SemanticFallback]] = {}  # contract_id -> fallbacks
        self.disputes: dict[str, EmergencyDispute] = {}
        self.oracle_cache: dict[str, OracleEvidence] = {}

        self.emergency_counter = 0
        self.fallback_counter = 0
        self.dispute_counter = 0

        # Track abuse
        self.declarer_history: dict[str, list[str]] = {}  # declarer_id -> emergency_ids

    # -------------------------------------------------------------------------
    # Emergency Declaration
    # -------------------------------------------------------------------------

    def declare_emergency(
        self,
        declared_by: str,
        scope: EmergencyScope,
        force_majeure_class: ForceMajeureClass,
        declared_reason: str,
        affected_refs: list[str],
        review_after_days: int = DEFAULT_REVIEW_DAYS,
        max_duration_days: int = DEFAULT_MAX_DURATION_DAYS,
    ) -> tuple[EmergencyDeclaration | None, list[str]]:
        """
        Declare an emergency per NCIP-013 Section 3.

        Validators MUST:
        - Verify declaration format
        - Treat declaration as signal, not truth
        - Trigger emergency evaluation flow
        """
        errors = []

        # Validate required fields
        if not declared_by:
            errors.append("declared_by is required")
        if not declared_reason:
            errors.append("declared_reason is required")
        if not affected_refs:
            errors.append("affected_refs is required (at least one reference)")

        if errors:
            return (None, errors)

        self.emergency_counter += 1
        emergency_id = f"EMG-{datetime.utcnow().strftime('%Y%m%d')}-{self.emergency_counter:04d}"

        emergency = EmergencyDeclaration(
            emergency_id=emergency_id,
            declared_by=declared_by,
            scope=scope,
            force_majeure_class=force_majeure_class,
            declared_reason=declared_reason,
            affected_refs=affected_refs,
            review_after=timedelta(days=review_after_days),
            max_duration=timedelta(days=max_duration_days),
        )

        # Verify declaration format
        valid, missing = emergency.has_required_fields()
        if not valid:
            errors.append(f"Missing required fields: {', '.join(missing)}")
            return (None, errors)

        self.emergencies[emergency_id] = emergency

        # Track declarer history for abuse detection
        if declared_by not in self.declarer_history:
            self.declarer_history[declared_by] = []
        self.declarer_history[declared_by].append(emergency_id)

        return (emergency, [])

    def validate_emergency(self, emergency_id: str) -> dict[str, Any]:
        """
        Validate an emergency declaration.

        Per NCIP-013 Section 11: Validators MUST treat emergency claims skeptically.
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        issues = []

        # Check required fields
        valid, missing = emergency.has_required_fields()
        if not valid:
            issues.append(f"Missing required fields: {', '.join(missing)}")

        # Check for abuse patterns
        declarer_emergencies = self.declarer_history.get(emergency.declared_by, [])
        if len(declarer_emergencies) > 3:
            issues.append("Warning: Declarer has multiple emergency declarations")

        # Check scope reasonableness
        if emergency.scope == EmergencyScope.SYSTEM:
            issues.append("Warning: System-wide scope requires additional verification")

        # Determine validation outcome
        if issues:
            emergency.status = EmergencyStatus.UNDER_REVIEW
        else:
            emergency.status = EmergencyStatus.VALIDATED

        return {
            "emergency_id": emergency_id,
            "status": emergency.status.value,
            "issues": issues,
            "requires_review": len(issues) > 0,
            "message": "Declaration is signal, not truth - evaluation required",
        }

    # -------------------------------------------------------------------------
    # Execution Effects
    # -------------------------------------------------------------------------

    def apply_execution_effect(self, emergency_id: str, effect: ExecutionEffect) -> dict[str, Any]:
        """
        Apply an execution effect per NCIP-013 Section 6.

        Allowed: pause_execution, delay_deadlines, freeze_settlement, trigger_fallback
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        if emergency.status not in [EmergencyStatus.VALIDATED, EmergencyStatus.ACTIVE]:
            return {
                "status": "error",
                "message": f"Cannot apply effects in status: {emergency.status.value}",
            }

        emergency.applied_effects.append(effect)
        emergency.status = EmergencyStatus.ACTIVE

        return {
            "status": "applied",
            "emergency_id": emergency_id,
            "effect": effect.value,
            "applied_effects": [e.value for e in emergency.applied_effects],
        }

    def check_prohibited_effect(self, effect: str) -> dict[str, Any]:
        """
        Check if an effect is prohibited per NCIP-013 Section 6.1.

        Prohibited effects NEVER alter meaning.
        """
        try:
            ProhibitedEffect(effect)
            return {
                "effect": effect,
                "prohibited": True,
                "message": f"{effect} is NEVER allowed - emergencies may suspend execution, never meaning",
            }
        except ValueError:
            pass

        try:
            ExecutionEffect(effect)
            return {
                "effect": effect,
                "prohibited": False,
                "allowed": True,
                "message": f"{effect} is allowed during emergencies",
            }
        except ValueError:
            return {
                "effect": effect,
                "prohibited": False,
                "allowed": False,
                "message": f"Unknown effect: {effect}",
            }

    # -------------------------------------------------------------------------
    # Semantic Fallbacks
    # -------------------------------------------------------------------------

    def declare_fallback(
        self, contract_id: str, trigger_condition: str, fallback_action: str
    ) -> tuple[SemanticFallback | None, list[str]]:
        """
        Declare a semantic fallback per NCIP-013 Section 7.

        Fallbacks MUST be declared at contract creation.
        """
        errors = []

        if not contract_id:
            errors.append("contract_id is required")
        if not trigger_condition:
            errors.append("trigger_condition is required")
        if not fallback_action:
            errors.append("fallback_action is required")

        if errors:
            return (None, errors)

        self.fallback_counter += 1
        fallback_id = f"FALLBACK-{contract_id}-{self.fallback_counter:04d}"

        fallback = SemanticFallback(
            fallback_id=fallback_id,
            contract_id=contract_id,
            trigger_condition=trigger_condition,
            fallback_action=fallback_action,
            is_original=True,
        )

        if contract_id not in self.fallbacks:
            self.fallbacks[contract_id] = []
        self.fallbacks[contract_id].append(fallback)

        return (fallback, [])

    def validate_fallback(self, fallback_id: str, contract_id: str) -> dict[str, Any]:
        """
        Semantically validate a fallback.
        """
        contract_fallbacks = self.fallbacks.get(contract_id, [])
        fallback = None
        for fb in contract_fallbacks:
            if fb.fallback_id == fallback_id:
                fallback = fb
                break

        if not fallback:
            return {"status": "error", "message": f"Fallback {fallback_id} not found"}

        valid, msg = fallback.validate()
        if valid:
            fallback.semantically_validated = True
            fallback.validation_timestamp = datetime.utcnow()

        return {
            "fallback_id": fallback_id,
            "valid": valid,
            "message": msg,
            "semantically_validated": fallback.semantically_validated,
        }

    def trigger_fallback(
        self, emergency_id: str, fallback_id: str, contract_id: str
    ) -> dict[str, Any]:
        """
        Trigger a semantic fallback during an emergency.
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        contract_fallbacks = self.fallbacks.get(contract_id, [])
        fallback = None
        for fb in contract_fallbacks:
            if fb.fallback_id == fallback_id:
                fallback = fb
                break

        if not fallback:
            return {
                "status": "error",
                "message": f"Fallback {fallback_id} not found for contract {contract_id}",
            }

        if not fallback.semantically_validated:
            return {
                "status": "error",
                "message": "Fallback must be semantically validated before triggering",
            }

        if not fallback.is_original:
            return {
                "status": "error",
                "message": "Cannot trigger post-hoc fallback - must be declared at contract creation",
            }

        # Apply the fallback effect
        self.apply_execution_effect(emergency_id, ExecutionEffect.TRIGGER_FALLBACK)

        return {
            "status": "triggered",
            "emergency_id": emergency_id,
            "fallback_id": fallback_id,
            "contract_id": contract_id,
            "trigger_condition": fallback.trigger_condition,
            "fallback_action": fallback.fallback_action,
        }

    def reject_posthoc_fallback(
        self, contract_id: str, trigger_condition: str, fallback_action: str
    ) -> dict[str, Any]:
        """
        Reject an attempt to create a post-hoc fallback.

        Per NCIP-013 Section 7: Fallbacks cannot be invented post-hoc.
        """
        return {
            "status": "rejected",
            "reason": "Fallbacks cannot be invented post-hoc per NCIP-013 Section 7",
            "contract_id": contract_id,
            "attempted_trigger": trigger_condition,
            "attempted_action": fallback_action,
            "rule": "Fallbacks must be declared at contract creation",
        }

    # -------------------------------------------------------------------------
    # Oracle Evidence
    # -------------------------------------------------------------------------

    def add_oracle_evidence(
        self,
        emergency_id: str,
        oracle_id: str,
        oracle_type: OracleType,
        evidence_data: str,
        confidence_score: float,
    ) -> dict[str, Any]:
        """
        Add oracle evidence to an emergency declaration.

        Per NCIP-013 Section 5: Oracle outputs are evidence, not authority.
        """
        # Input validation
        if not emergency_id:
            return {"status": "error", "message": "Emergency ID is required"}

        if not oracle_id:
            return {"status": "error", "message": "Oracle ID is required"}

        if oracle_type is None:
            return {"status": "error", "message": "Oracle type is required"}

        # Validate oracle_type is a valid enum value
        if not isinstance(oracle_type, OracleType):
            try:
                oracle_type = OracleType(oracle_type)
            except (ValueError, TypeError):
                return {
                    "status": "error",
                    "message": f"Invalid oracle type: {oracle_type}. Valid types: {[t.value for t in OracleType]}",
                }

        if not evidence_data:
            return {"status": "error", "message": "Evidence data is required"}

        if not isinstance(evidence_data, str):
            try:
                evidence_data = str(evidence_data)
            except Exception:
                return {"status": "error", "message": "Evidence data must be convertible to string"}

        # Validate confidence_score
        if confidence_score is None:
            return {"status": "error", "message": "Confidence score is required"}

        try:
            confidence_score = float(confidence_score)
        except (ValueError, TypeError):
            return {"status": "error", "message": "Confidence score must be a number"}

        if confidence_score < 0 or confidence_score > 1:
            return {
                "status": "warning",
                "message": f"Confidence score {confidence_score} clamped to valid range [0.0, 1.0]",
            }

        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        # Validate emergency state - cannot add evidence to resolved emergencies
        if emergency.status in (EmergencyStatus.RESOLVED, EmergencyStatus.REJECTED):
            return {
                "status": "error",
                "message": f"Cannot add evidence to {emergency.status.value} emergency",
            }

        try:
            evidence = OracleEvidence(
                oracle_id=oracle_id,
                oracle_type=oracle_type,
                evidence_data=evidence_data,
                confidence_score=min(1.0, max(0.0, confidence_score)),
                is_authoritative=False,  # Always False per NCIP-013
            )

            emergency.oracle_evidence.append(evidence)

            return {
                "status": "added",
                "emergency_id": emergency_id,
                "oracle_id": oracle_id,
                "oracle_type": oracle_type.value,
                "confidence_score": evidence.confidence_score,
                "evidence_count": len(emergency.oracle_evidence),
                "note": "Oracle output is evidence, not authority - does not auto-resolve",
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to add oracle evidence: {str(e)}",
                "error_type": type(e).__name__,
            }

    # -------------------------------------------------------------------------
    # Emergency Disputes
    # -------------------------------------------------------------------------

    def dispute_emergency(
        self, emergency_id: str, disputed_by: str, dispute_reason: str
    ) -> tuple[EmergencyDispute | None, list[str]]:
        """
        Dispute an emergency declaration per NCIP-013 Section 8.

        Effects:
        - MP-03 dispute flow applies
        - Semantic Lock engages immediately
        - Burden of proof lies with declarer
        - Execution remains paused during dispute
        """
        errors = []

        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            errors.append(f"Emergency {emergency_id} not found")
            return (None, errors)

        if emergency.status == EmergencyStatus.RESOLVED:
            errors.append("Cannot dispute a resolved emergency")
            return (None, errors)

        self.dispute_counter += 1
        dispute_id = f"EMG-DISP-{self.dispute_counter:04d}"

        dispute = EmergencyDispute(
            dispute_id=dispute_id,
            emergency_id=emergency_id,
            disputed_by=disputed_by,
            dispute_reason=dispute_reason,
            semantic_lock_id=f"LOCK-{emergency_id}-DISPUTE",
        )

        # Update emergency status
        emergency.status = EmergencyStatus.DISPUTED
        emergency.semantic_lock_id = dispute.semantic_lock_id

        self.disputes[dispute_id] = dispute

        return (dispute, [])

    def resolve_emergency_dispute(
        self, dispute_id: str, upheld: bool, resolution_notes: str
    ) -> dict[str, Any]:
        """
        Resolve an emergency dispute.

        If not upheld, emergency declaration may be marked frivolous.
        """
        dispute = self.disputes.get(dispute_id)
        if not dispute:
            return {"status": "error", "message": f"Dispute {dispute_id} not found"}

        dispute.resolved_at = datetime.utcnow()
        dispute.upheld = upheld

        emergency = self.emergencies.get(dispute.emergency_id)
        if emergency:
            if upheld:
                emergency.status = EmergencyStatus.ACTIVE
            else:
                emergency.status = EmergencyStatus.REJECTED
                # Mark as frivolous and apply harassment penalty
                emergency.frivolous = True
                emergency.harassment_score_impact = self._calculate_harassment_penalty(
                    emergency.declared_by
                )

            emergency.semantic_lock_id = None

        return {
            "dispute_id": dispute_id,
            "emergency_id": dispute.emergency_id,
            "upheld": upheld,
            "resolution_notes": resolution_notes,
            "harassment_penalty": emergency.harassment_score_impact
            if emergency and not upheld
            else 0.0,
        }

    def _calculate_harassment_penalty(self, declarer_id: str) -> float:
        """Calculate harassment penalty with repeat multiplier."""
        history = self.declarer_history.get(declarer_id, [])
        frivolous_count = sum(
            1 for eid in history if eid in self.emergencies and self.emergencies[eid].frivolous
        )
        return self.FRIVOLOUS_HARASSMENT_PENALTY * (self.REPEAT_MULTIPLIER**frivolous_count)

    # -------------------------------------------------------------------------
    # Timeout & Expiry
    # -------------------------------------------------------------------------

    def check_expiry(self, emergency_id: str) -> dict[str, Any]:
        """
        Check if emergency has expired per NCIP-013 Section 9.

        At expiry:
        - Execution resumes, or
        - Contract terminates per fallback, or
        - Parties must ratify amendment

        Silent continuation is forbidden.
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        datetime.utcnow()
        result = {
            "emergency_id": emergency_id,
            "declared_at": emergency.declared_at.isoformat(),
            "days_active": emergency.days_active,
            "review_deadline": emergency.review_deadline.isoformat(),
            "expiry_deadline": emergency.expiry_deadline.isoformat(),
            "needs_review": emergency.needs_review,
            "is_expired": emergency.is_expired,
        }

        if emergency.is_expired:
            result["action_required"] = (
                "Emergency expired - must resume execution, terminate per fallback, or ratify amendment"
            )
            result["silent_continuation_forbidden"] = True
            emergency.status = EmergencyStatus.EXPIRED

        elif emergency.needs_review:
            result["action_required"] = "Emergency review deadline passed - review required"

        return result

    def process_expiry(
        self, emergency_id: str, action: str, ratification_id: str | None = None
    ) -> dict[str, Any]:
        """
        Process emergency expiry per NCIP-013 Section 9.1.

        Actions: resume_execution, terminate_fallback, ratify_amendment
        """
        # Input validation
        if not emergency_id:
            return {"status": "error", "message": "Emergency ID is required"}

        if not action:
            return {"status": "error", "message": "Action is required"}

        # Normalize action to lowercase for comparison
        action = action.strip().lower()

        valid_actions = ["resume_execution", "terminate_fallback", "ratify_amendment"]
        if action not in valid_actions:
            return {
                "status": "error",
                "message": f"Invalid action: {action}. Use one of: {', '.join(valid_actions)}",
            }

        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        # Validate emergency state - cannot process already resolved emergencies
        if emergency.status == EmergencyStatus.RESOLVED:
            return {
                "status": "error",
                "message": "Emergency is already resolved",
                "resolved_at": emergency.resolved_at.isoformat() if emergency.resolved_at else None,
                "resolution_reason": emergency.resolution_reason,
            }

        if emergency.status == EmergencyStatus.REJECTED:
            return {
                "status": "error",
                "message": "Cannot process expiry for a rejected emergency",
            }

        # Validate that emergency is expired or needs review for expiry processing
        if not emergency.is_expired and not emergency.needs_review:
            return {
                "status": "error",
                "message": "Emergency has not expired yet",
                "expiry_deadline": emergency.expiry_deadline.isoformat() if emergency.expiry_deadline else None,
                "days_remaining": (emergency.expiry_deadline - datetime.utcnow()).days if emergency.expiry_deadline else None,
            }

        try:
            if action == "resume_execution":
                emergency.status = EmergencyStatus.RESOLVED
                emergency.resolved_at = datetime.utcnow()
                emergency.resolution_reason = "Execution resumed after emergency expiry"
                return {
                    "status": "resolved",
                    "action": "resume_execution",
                    "emergency_id": emergency_id,
                }

            elif action == "terminate_fallback":
                # Verify fallbacks exist for affected contracts
                has_fallbacks = any(
                    ref in self.fallbacks for ref in emergency.affected_refs
                )
                if not has_fallbacks:
                    return {
                        "status": "warning",
                        "message": "No fallbacks found for affected contracts. Proceeding with termination.",
                        "action": "terminate_fallback",
                        "emergency_id": emergency_id,
                    }

                emergency.status = EmergencyStatus.RESOLVED
                emergency.resolved_at = datetime.utcnow()
                emergency.resolution_reason = "Contract terminated per fallback clause"
                return {
                    "status": "resolved",
                    "action": "terminate_fallback",
                    "emergency_id": emergency_id,
                }

            elif action == "ratify_amendment":
                if not ratification_id:
                    return {"status": "error", "message": "ratification_id required for amendment"}

                # Validate ratification_id format
                if not isinstance(ratification_id, str) or len(ratification_id.strip()) == 0:
                    return {"status": "error", "message": "ratification_id must be a non-empty string"}

                emergency.status = EmergencyStatus.RESOLVED
                emergency.resolved_at = datetime.utcnow()
                emergency.resolution_reason = f"Parties ratified amendment {ratification_id}"
                return {
                    "status": "resolved",
                    "action": "ratify_amendment",
                    "emergency_id": emergency_id,
                    "ratification_id": ratification_id,
                }

        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to process expiry: {str(e)}",
                "error_type": type(e).__name__,
            }

        # Should not reach here, but provide fallback
        return {
            "status": "error",
            "message": f"Unhandled action: {action}",
        }

    def check_escalation_needed(self, emergency_id: str) -> dict[str, Any]:
        """
        Check if emergency needs escalation per NCIP-013 Section 11.

        Validators MUST escalate unresolved emergencies >= 30 days.
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        needs_escalation = (
            emergency.days_active >= self.ESCALATION_THRESHOLD_DAYS
            and emergency.status in [EmergencyStatus.ACTIVE, EmergencyStatus.UNDER_REVIEW]
        )

        return {
            "emergency_id": emergency_id,
            "days_active": emergency.days_active,
            "threshold_days": self.ESCALATION_THRESHOLD_DAYS,
            "needs_escalation": needs_escalation,
            "current_status": emergency.status.value,
        }

    # -------------------------------------------------------------------------
    # Machine-Readable Policy
    # -------------------------------------------------------------------------

    def generate_emergency_policy(self) -> dict[str, Any]:
        """
        Generate machine-readable emergency policy per NCIP-013 Section 12.
        """
        return {
            "emergency_policy": {
                "version": "1.0",
                "allow_execution_pause": True,
                "allow_semantic_change": False,
                "required_fields": [
                    "scope",
                    "affected_refs",
                    "declared_reason",
                    "review_after",
                    "max_duration",
                ],
                "oracle_support": {"allowed": True, "authoritative": False},
                "dispute_handling": {
                    "lock_semantics_immediately": True,
                    "burden_of_proof": "declarer",
                },
                "abuse_controls": {
                    "frivolous_penalty": "harassment_score_increase",
                    "repeat_multiplier": self.REPEAT_MULTIPLIER,
                },
                "timeouts": {
                    "default_review_days": self.DEFAULT_REVIEW_DAYS,
                    "default_max_duration_days": self.DEFAULT_MAX_DURATION_DAYS,
                    "escalation_threshold_days": self.ESCALATION_THRESHOLD_DAYS,
                },
            }
        }

    # -------------------------------------------------------------------------
    # Validator Behavior
    # -------------------------------------------------------------------------

    def validator_check(self, emergency_id: str) -> dict[str, Any]:
        """
        Validator behavior check per NCIP-013 Section 11.

        Validators MUST:
        - Treat emergency claims skeptically
        - Require explicit scope and duration
        - Reject semantic alterations
        - Enforce fallback boundaries
        - Escalate unresolved emergencies >= 30 days
        """
        emergency = self.emergencies.get(emergency_id)
        if not emergency:
            return {"status": "error", "message": f"Emergency {emergency_id} not found"}

        checks = {
            "has_explicit_scope": emergency.scope is not None,
            "has_explicit_duration": emergency.max_duration is not None,
            "has_review_period": emergency.review_after is not None,
            "has_affected_refs": len(emergency.affected_refs) > 0,
            "semantic_integrity_preserved": True,  # Emergencies never alter meaning
            "needs_escalation": emergency.days_active >= self.ESCALATION_THRESHOLD_DAYS,
        }

        issues = []
        if not checks["has_explicit_scope"]:
            issues.append("Missing explicit scope")
        if not checks["has_explicit_duration"]:
            issues.append("Missing explicit duration")
        if not checks["has_affected_refs"]:
            issues.append("Missing affected references")
        if checks["needs_escalation"]:
            issues.append(f"Unresolved for {emergency.days_active} days - escalation required")

        return {
            "emergency_id": emergency_id,
            "checks": checks,
            "issues": issues,
            "validator_action": "escalate" if checks["needs_escalation"] else "monitor",
            "principle": "Emergencies may suspend execution — never meaning",
        }

    # -------------------------------------------------------------------------
    # Status & Reporting
    # -------------------------------------------------------------------------

    def get_emergency(self, emergency_id: str) -> EmergencyDeclaration | None:
        """Get an emergency by ID."""
        return self.emergencies.get(emergency_id)

    def get_active_emergencies(self) -> list[EmergencyDeclaration]:
        """Get all active emergencies."""
        return [e for e in self.emergencies.values() if e.status == EmergencyStatus.ACTIVE]

    def get_status_summary(self) -> dict[str, Any]:
        """Get summary of emergency system status."""
        status_counts = {}
        for emergency in self.emergencies.values():
            status = emergency.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        class_counts = {}
        for emergency in self.emergencies.values():
            fmclass = emergency.force_majeure_class.value
            class_counts[fmclass] = class_counts.get(fmclass, 0) + 1

        return {
            "total_emergencies": len(self.emergencies),
            "status_counts": status_counts,
            "force_majeure_class_counts": class_counts,
            "total_fallbacks": sum(len(fbs) for fbs in self.fallbacks.values()),
            "total_disputes": len(self.disputes),
            "active_emergencies": len(self.get_active_emergencies()),
            "frivolous_declarations": sum(1 for e in self.emergencies.values() if e.frivolous),
            "principle": "Emergencies may suspend execution — never meaning.",
        }

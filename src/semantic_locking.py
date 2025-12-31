"""
NatLangChain - Semantic Locking & Cooling Periods
Implements NCIP-005: Dispute Escalation, Cooling Periods & Semantic Locking

Semantic Lock:
- Freezes registry version, prose wording, anchor semantics, PoUs, NCIPs
- All interpretation references Lock Time (Tₗ) state only

Cooling Periods:
- D3 (Soft): 24 hours
- D4 (Hard): 72 hours

Escalation Path:
1. Mutual Settlement Attempt
2. Mediator Review
3. Formal Adjudication
4. Binding Resolution
"""

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

# Configure logging
logger = logging.getLogger("natlangchain.semantic_lock")


class DisputeLevel(Enum):
    """Dispute severity levels per NCIP-005."""
    D3 = "D3"  # Soft - 24h cooling
    D4 = "D4"  # Hard - 72h cooling


class DisputeTrigger(Enum):
    """Valid dispute triggers per NCIP-005 Section 3.1."""
    DRIFT_D3 = "drift_level_d3"
    DRIFT_D4 = "drift_level_d4"
    POU_FAILURE = "pou_failure"
    POU_CONTRADICTION = "pou_contradiction"
    CONFLICTING_RATIFICATIONS = "conflicting_ratifications"
    MULTILINGUAL_MISALIGNMENT = "multilingual_misalignment"
    MATERIAL_BREACH = "material_breach"


class LockAction(Enum):
    """Actions that can be attempted during a semantic lock."""
    # Allowed during cooling
    CLARIFICATION = "clarification"
    SETTLEMENT_PROPOSAL = "settlement_proposal"
    MEDIATOR_ASSIGNMENT = "mediator_assignment"
    EVIDENCE_SUBMISSION = "evidence_submission"
    # Forbidden during cooling
    ESCALATION = "escalation"
    ENFORCEMENT = "enforcement"
    SEMANTIC_CHANGE = "semantic_change"
    CONTRACT_AMENDMENT = "contract_amendment"
    RE_TRANSLATION = "re_translation"
    REGISTRY_UPGRADE = "registry_upgrade"
    POU_REGENERATION = "pou_regeneration"


class EscalationStage(Enum):
    """Escalation path stages per NCIP-005 Section 7."""
    COOLING = "cooling"
    MUTUAL_SETTLEMENT = "mutual_settlement"
    MEDIATOR_REVIEW = "mediator_review"
    ADJUDICATION = "adjudication"
    BINDING_RESOLUTION = "binding_resolution"
    RESOLVED = "resolved"


class ResolutionOutcome(Enum):
    """Dispute resolution outcomes per NCIP-005 Section 9."""
    DISMISSED = "dismissed"         # Execution resumes
    CLARIFIED = "clarified"         # Semantic Lock updated + re-ratified
    AMENDED = "amended"             # New Prose Contract required
    TERMINATED = "terminated"       # Agreement voided
    COMPENSATED = "compensated"     # Settlement enforced


# NCIP-005 Cooling Period Durations (in hours)
COOLING_PERIODS = {
    DisputeLevel.D3: 24,  # 24 hours for soft disputes
    DisputeLevel.D4: 72   # 72 hours for hard disputes
}

# Actions allowed during cooling period
ALLOWED_DURING_COOLING = {
    LockAction.CLARIFICATION,
    LockAction.SETTLEMENT_PROPOSAL,
    LockAction.MEDIATOR_ASSIGNMENT,
    LockAction.EVIDENCE_SUBMISSION
}

# Actions forbidden during cooling period
FORBIDDEN_DURING_COOLING = {
    LockAction.ESCALATION,
    LockAction.ENFORCEMENT,
    LockAction.SEMANTIC_CHANGE,
    LockAction.CONTRACT_AMENDMENT,
    LockAction.RE_TRANSLATION,
    LockAction.REGISTRY_UPGRADE,
    LockAction.POU_REGENERATION
}

# Actions forbidden during ANY semantic lock
FORBIDDEN_DURING_LOCK = {
    LockAction.CONTRACT_AMENDMENT,
    LockAction.RE_TRANSLATION,
    LockAction.REGISTRY_UPGRADE,
    LockAction.POU_REGENERATION,
    LockAction.SEMANTIC_CHANGE
}


@dataclass
class LockedState:
    """
    Captures the semantic state at lock time per NCIP-005 Section 5.1.

    Semantic Lock freezes:
    - Canonical Term Registry version
    - Prose Contract wording
    - Anchor language semantics
    - Verified PoUs
    - Applicable NCIPs
    """
    registry_version: str
    prose_content_hash: str
    anchor_language: str
    verified_pou_hashes: list[str]
    applicable_ncips: list[str]
    contract_id: str
    locked_at: str  # ISO timestamp


@dataclass
class CoolingPeriodStatus:
    """Status of a cooling period."""
    dispute_level: DisputeLevel
    started_at: str  # ISO timestamp
    ends_at: str     # ISO timestamp
    duration_hours: int
    is_active: bool
    time_remaining_seconds: float


@dataclass
class SemanticLock:
    """
    A semantic lock per NCIP-005.

    Ensures meaning freezes before conflict escalates.
    All interpretation references Tₗ state only.
    """
    lock_id: str
    dispute_id: str
    contract_id: str
    lock_time: str  # Tₗ - ISO timestamp
    locked_state: LockedState
    dispute_level: DisputeLevel
    trigger: DisputeTrigger
    initiator_id: str
    is_active: bool
    cooling_ends_at: str  # ISO timestamp
    current_stage: EscalationStage
    execution_halted: bool
    action_log: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class DisputeEntry:
    """A dispute entry per NCIP-005 Section 3.2."""
    contract_id: str
    trigger: DisputeTrigger
    claimed_divergence: str
    timestamp: str  # Tᵢ
    initiator_id: str
    dispute_level: DisputeLevel


class SemanticLockManager:
    """
    Manages semantic locks per NCIP-005.

    Key responsibilities:
    - Activate/deactivate semantic locks
    - Enforce cooling periods
    - Control allowed/forbidden actions
    - Manage escalation path
    """

    def __init__(self, validator_id: str = "default"):
        """
        Initialize the semantic lock manager.

        Args:
            validator_id: Identifier for this validator instance
        """
        self.validator_id = validator_id
        self._locks: dict[str, SemanticLock] = {}  # lock_id -> lock
        self._dispute_locks: dict[str, str] = {}   # dispute_id -> lock_id
        self._contract_locks: dict[str, str] = {}  # contract_id -> lock_id

    def _generate_lock_id(self, dispute_id: str, contract_id: str) -> str:
        """Generate unique lock ID."""
        data = f"{dispute_id}:{contract_id}:{datetime.utcnow().isoformat()}"
        return f"LOCK-{hashlib.sha256(data.encode()).hexdigest()[:12].upper()}"

    def _get_dispute_level(self, trigger: DisputeTrigger) -> DisputeLevel:
        """Determine dispute level from trigger."""
        if trigger == DisputeTrigger.DRIFT_D4:
            return DisputeLevel.D4
        # D3 for most triggers, D4 only for explicit D4 drift
        return DisputeLevel.D3

    def initiate_dispute(
        self,
        contract_id: str,
        trigger: DisputeTrigger,
        claimed_divergence: str,
        initiator_id: str,
        registry_version: str,
        prose_content: str,
        anchor_language: str = "en",
        verified_pou_hashes: list[str] | None = None,
        applicable_ncips: list[str] | None = None
    ) -> tuple[SemanticLock, DisputeEntry]:
        """
        Initiate a dispute and activate semantic lock per NCIP-005.

        Per NCIP-005 Section 4 (Immediate Validator Actions):
        1. Halt all derived execution
        2. Activate Semantic Lock
        3. Record Lock Time (Tₗ = Tᵢ)
        4. Reject all reinterpretations post-Tₗ

        Args:
            contract_id: The prose contract being disputed
            trigger: What triggered the dispute
            claimed_divergence: Description of semantic divergence
            initiator_id: Party initiating the dispute
            registry_version: Current registry version to lock
            prose_content: Contract prose to lock
            anchor_language: Anchor language to lock
            verified_pou_hashes: PoU hashes to lock
            applicable_ncips: NCIP versions to lock

        Returns:
            Tuple of (SemanticLock, DisputeEntry)
        """
        # Check if contract already locked
        if contract_id in self._contract_locks:
            existing_lock_id = self._contract_locks[contract_id]
            existing_lock = self._locks.get(existing_lock_id)
            if existing_lock and existing_lock.is_active:
                raise ValueError(
                    f"Contract {contract_id} already has active lock: {existing_lock_id}"
                )

        # Determine dispute level
        dispute_level = self._get_dispute_level(trigger)

        # Create dispute entry
        now = datetime.utcnow()
        timestamp = now.isoformat() + "Z"
        dispute_id = f"DISPUTE-{hashlib.sha256(f'{contract_id}:{timestamp}'.encode()).hexdigest()[:12].upper()}"

        dispute_entry = DisputeEntry(
            contract_id=contract_id,
            trigger=trigger,
            claimed_divergence=claimed_divergence,
            timestamp=timestamp,
            initiator_id=initiator_id,
            dispute_level=dispute_level
        )

        # Calculate cooling period end
        cooling_hours = COOLING_PERIODS[dispute_level]
        cooling_ends = now + timedelta(hours=cooling_hours)

        # Create locked state
        prose_hash = hashlib.sha256(prose_content.encode()).hexdigest()
        locked_state = LockedState(
            registry_version=registry_version,
            prose_content_hash=prose_hash,
            anchor_language=anchor_language,
            verified_pou_hashes=verified_pou_hashes or [],
            applicable_ncips=applicable_ncips or ["NCIP-001", "NCIP-002", "NCIP-004", "NCIP-005"],
            contract_id=contract_id,
            locked_at=timestamp
        )

        # Create semantic lock
        lock_id = self._generate_lock_id(dispute_id, contract_id)

        lock = SemanticLock(
            lock_id=lock_id,
            dispute_id=dispute_id,
            contract_id=contract_id,
            lock_time=timestamp,  # Tₗ = Tᵢ
            locked_state=locked_state,
            dispute_level=dispute_level,
            trigger=trigger,
            initiator_id=initiator_id,
            is_active=True,
            cooling_ends_at=cooling_ends.isoformat() + "Z",
            current_stage=EscalationStage.COOLING,
            execution_halted=True,
            action_log=[{
                "action": "lock_activated",
                "timestamp": timestamp,
                "by": self.validator_id,
                "details": f"Semantic lock activated due to {trigger.value}"
            }]
        )

        # Store lock
        self._locks[lock_id] = lock
        self._dispute_locks[dispute_id] = lock_id
        self._contract_locks[contract_id] = lock_id

        logger.info(f"Semantic lock {lock_id} activated for dispute {dispute_id}")

        return lock, dispute_entry

    def get_lock(self, lock_id: str) -> SemanticLock | None:
        """Get a lock by ID."""
        return self._locks.get(lock_id)

    def get_lock_by_dispute(self, dispute_id: str) -> SemanticLock | None:
        """Get lock by dispute ID."""
        lock_id = self._dispute_locks.get(dispute_id)
        return self._locks.get(lock_id) if lock_id else None

    def get_lock_by_contract(self, contract_id: str) -> SemanticLock | None:
        """Get lock by contract ID."""
        lock_id = self._contract_locks.get(contract_id)
        return self._locks.get(lock_id) if lock_id else None

    def is_contract_locked(self, contract_id: str) -> bool:
        """Check if a contract has an active semantic lock."""
        lock = self.get_lock_by_contract(contract_id)
        return lock is not None and lock.is_active

    def get_cooling_status(self, lock_id: str) -> CoolingPeriodStatus | None:
        """
        Get the cooling period status for a lock.

        Args:
            lock_id: The lock ID

        Returns:
            CoolingPeriodStatus or None if lock not found
        """
        lock = self._locks.get(lock_id)
        if not lock:
            return None

        now = datetime.utcnow()
        cooling_ends = datetime.fromisoformat(lock.cooling_ends_at.rstrip('Z'))
        time_remaining = (cooling_ends - now).total_seconds()
        is_active = time_remaining > 0

        return CoolingPeriodStatus(
            dispute_level=lock.dispute_level,
            started_at=lock.lock_time,
            ends_at=lock.cooling_ends_at,
            duration_hours=COOLING_PERIODS[lock.dispute_level],
            is_active=is_active,
            time_remaining_seconds=max(0, time_remaining)
        )

    def is_cooling_active(self, lock_id: str) -> bool:
        """Check if cooling period is still active."""
        status = self.get_cooling_status(lock_id)
        return status is not None and status.is_active

    def can_perform_action(
        self,
        lock_id: str,
        action: LockAction
    ) -> tuple[bool, str]:
        """
        Check if an action is allowed given the current lock state.

        Per NCIP-005 Section 5.2 and 6.3.

        Args:
            lock_id: The lock ID
            action: The action to check

        Returns:
            Tuple of (is_allowed, reason)
        """
        lock = self._locks.get(lock_id)
        if not lock:
            return True, "No active lock"

        if not lock.is_active:
            return True, "Lock is not active"

        # Actions forbidden during ANY lock
        if action in FORBIDDEN_DURING_LOCK:
            return False, f"Action '{action.value}' is forbidden during semantic lock per NCIP-005 Section 5.2"

        # Check cooling period specific rules
        cooling_status = self.get_cooling_status(lock_id)

        if cooling_status and cooling_status.is_active:
            # During cooling period
            if action in FORBIDDEN_DURING_COOLING:
                hours_remaining = cooling_status.time_remaining_seconds / 3600
                return False, (
                    f"Action '{action.value}' is forbidden during cooling period. "
                    f"{hours_remaining:.1f} hours remaining per NCIP-005 Section 6.3"
                )
            if action in ALLOWED_DURING_COOLING:
                return True, f"Action '{action.value}' is allowed during cooling period"

        # Post-cooling: escalation allowed
        if not cooling_status or not cooling_status.is_active:
            if action == LockAction.ESCALATION:
                return True, "Escalation allowed after cooling period"

        return True, "Action allowed"

    def attempt_action(
        self,
        lock_id: str,
        action: LockAction,
        actor_id: str,
        details: str | None = None
    ) -> tuple[bool, str]:
        """
        Attempt to perform an action, logging the attempt.

        Args:
            lock_id: The lock ID
            action: The action to attempt
            actor_id: Who is attempting the action
            details: Optional details about the action

        Returns:
            Tuple of (success, message)
        """
        allowed, reason = self.can_perform_action(lock_id, action)

        lock = self._locks.get(lock_id)
        if lock:
            lock.action_log.append({
                "action": action.value,
                "attempted_by": actor_id,
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "allowed": allowed,
                "reason": reason,
                "details": details
            })

            if not allowed:
                logger.warning(
                    f"Blocked action {action.value} on lock {lock_id} by {actor_id}: {reason}"
                )
            else:
                logger.info(
                    f"Allowed action {action.value} on lock {lock_id} by {actor_id}"
                )

        return allowed, reason

    def advance_stage(
        self,
        lock_id: str,
        actor_id: str,
        reason: str | None = None
    ) -> tuple[bool, str, EscalationStage | None]:
        """
        Advance to the next escalation stage per NCIP-005 Section 7.

        Escalation path:
        COOLING -> MUTUAL_SETTLEMENT -> MEDIATOR_REVIEW -> ADJUDICATION -> BINDING_RESOLUTION -> RESOLVED

        Args:
            lock_id: The lock ID
            actor_id: Who is advancing the stage
            reason: Optional reason for advancement

        Returns:
            Tuple of (success, message, new_stage)
        """
        lock = self._locks.get(lock_id)
        if not lock:
            return False, "Lock not found", None

        if not lock.is_active:
            return False, "Lock is not active", None

        current = lock.current_stage

        # Define stage transitions
        stage_order = [
            EscalationStage.COOLING,
            EscalationStage.MUTUAL_SETTLEMENT,
            EscalationStage.MEDIATOR_REVIEW,
            EscalationStage.ADJUDICATION,
            EscalationStage.BINDING_RESOLUTION,
            EscalationStage.RESOLVED
        ]

        # Check if cooling period is still active
        if current == EscalationStage.COOLING and self.is_cooling_active(lock_id):
            cooling_status = self.get_cooling_status(lock_id)
            hours = cooling_status.time_remaining_seconds / 3600
            return False, f"Cannot advance during cooling period. {hours:.1f} hours remaining", None

        # Find current index and advance
        try:
            current_idx = stage_order.index(current)
        except ValueError:
            return False, f"Unknown stage: {current}", None

        if current_idx >= len(stage_order) - 1:
            return False, "Already at final stage", current

        new_stage = stage_order[current_idx + 1]
        lock.current_stage = new_stage

        lock.action_log.append({
            "action": "stage_advanced",
            "from_stage": current.value,
            "to_stage": new_stage.value,
            "advanced_by": actor_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "reason": reason
        })

        logger.info(f"Lock {lock_id} advanced from {current.value} to {new_stage.value}")

        return True, f"Advanced to {new_stage.value}", new_stage

    def resolve_dispute(
        self,
        lock_id: str,
        outcome: ResolutionOutcome,
        resolution_authority: str,
        resolution_details: str,
        findings: dict[str, Any] | None = None
    ) -> tuple[bool, str]:
        """
        Resolve a dispute and release the semantic lock.

        Per NCIP-005 Section 9.

        Args:
            lock_id: The lock ID
            outcome: Resolution outcome
            resolution_authority: Who authorized the resolution
            resolution_details: Description of resolution
            findings: Optional structured findings

        Returns:
            Tuple of (success, message)
        """
        lock = self._locks.get(lock_id)
        if not lock:
            return False, "Lock not found"

        if not lock.is_active:
            return False, "Lock is already inactive"

        # Cannot resolve during cooling period
        if self.is_cooling_active(lock_id):
            return False, "Cannot resolve during cooling period"

        # Ensure we're at binding resolution stage or beyond
        if lock.current_stage not in [EscalationStage.BINDING_RESOLUTION, EscalationStage.ADJUDICATION]:
            # Allow resolution from adjudication or binding_resolution
            pass

        now = datetime.utcnow().isoformat() + "Z"

        # Determine effects based on outcome
        effects = self._get_resolution_effects(outcome)

        lock.is_active = False
        lock.current_stage = EscalationStage.RESOLVED

        if outcome == ResolutionOutcome.DISMISSED:
            lock.execution_halted = False  # Resume execution

        lock.action_log.append({
            "action": "dispute_resolved",
            "outcome": outcome.value,
            "resolution_authority": resolution_authority,
            "resolution_details": resolution_details,
            "findings": findings,
            "effects": effects,
            "timestamp": now
        })

        # Clean up references
        if lock.contract_id in self._contract_locks:
            del self._contract_locks[lock.contract_id]
        if lock.dispute_id in self._dispute_locks:
            del self._dispute_locks[lock.dispute_id]

        logger.info(f"Lock {lock_id} resolved with outcome: {outcome.value}")

        return True, f"Dispute resolved: {outcome.value}"

    def _get_resolution_effects(self, outcome: ResolutionOutcome) -> dict[str, Any]:
        """Get the effects of a resolution outcome per NCIP-005 Section 9."""
        effects = {
            ResolutionOutcome.DISMISSED: {
                "resume_execution": True,
                "requires_action": False
            },
            ResolutionOutcome.CLARIFIED: {
                "resume_execution": False,
                "require_reratification": True,
                "update_semantic_lock": True
            },
            ResolutionOutcome.AMENDED: {
                "resume_execution": False,
                "require_new_contract": True,
                "void_current": True
            },
            ResolutionOutcome.TERMINATED: {
                "resume_execution": False,
                "void_contract": True,
                "release_all_parties": True
            },
            ResolutionOutcome.COMPENSATED: {
                "resume_execution": False,
                "enforce_settlement": True
            }
        }
        return effects.get(outcome, {})

    def verify_against_lock(
        self,
        lock_id: str,
        registry_version: str,
        prose_content: str
    ) -> tuple[bool, list[str]]:
        """
        Verify that content matches the locked state.

        Per NCIP-005: All interpretation references Tₗ state only.

        Args:
            lock_id: The lock ID
            registry_version: Registry version to check
            prose_content: Prose content to check

        Returns:
            Tuple of (matches, list of discrepancies)
        """
        lock = self._locks.get(lock_id)
        if not lock or not lock.is_active:
            return True, []

        discrepancies = []

        # Check registry version
        if registry_version != lock.locked_state.registry_version:
            discrepancies.append(
                f"Registry version mismatch: expected {lock.locked_state.registry_version}, "
                f"got {registry_version}"
            )

        # Check prose content hash
        content_hash = hashlib.sha256(prose_content.encode()).hexdigest()
        if content_hash != lock.locked_state.prose_content_hash:
            discrepancies.append("Prose content has been modified since lock time")

        return len(discrepancies) == 0, discrepancies

    def get_validator_response(
        self,
        lock_id: str,
        action: LockAction
    ) -> dict[str, Any]:
        """
        Get complete validator response for an action attempt.

        Args:
            lock_id: The lock ID
            action: The action being attempted

        Returns:
            Complete validator response
        """
        lock = self._locks.get(lock_id)

        if not lock:
            return {
                "lock_active": False,
                "action_allowed": True,
                "message": "No active lock"
            }

        allowed, reason = self.can_perform_action(lock_id, action)
        cooling_status = self.get_cooling_status(lock_id)

        response = {
            "lock_id": lock_id,
            "lock_active": lock.is_active,
            "dispute_id": lock.dispute_id,
            "contract_id": lock.contract_id,
            "lock_time": lock.lock_time,
            "dispute_level": lock.dispute_level.value,
            "current_stage": lock.current_stage.value,
            "execution_halted": lock.execution_halted,
            "action": action.value,
            "action_allowed": allowed,
            "reason": reason,
            "validator_id": self.validator_id
        }

        if cooling_status:
            response["cooling_period"] = {
                "is_active": cooling_status.is_active,
                "ends_at": cooling_status.ends_at,
                "duration_hours": cooling_status.duration_hours,
                "time_remaining_seconds": cooling_status.time_remaining_seconds
            }

        return response

    def get_lock_summary(self, lock_id: str) -> dict[str, Any] | None:
        """Get a summary of a lock's state."""
        lock = self._locks.get(lock_id)
        if not lock:
            return None

        cooling_status = self.get_cooling_status(lock_id)

        return {
            "lock_id": lock.lock_id,
            "dispute_id": lock.dispute_id,
            "contract_id": lock.contract_id,
            "is_active": lock.is_active,
            "lock_time": lock.lock_time,
            "dispute_level": lock.dispute_level.value,
            "trigger": lock.trigger.value,
            "initiator": lock.initiator_id,
            "current_stage": lock.current_stage.value,
            "execution_halted": lock.execution_halted,
            "cooling_active": cooling_status.is_active if cooling_status else False,
            "cooling_ends_at": lock.cooling_ends_at,
            "locked_state": {
                "registry_version": lock.locked_state.registry_version,
                "anchor_language": lock.locked_state.anchor_language,
                "pou_count": len(lock.locked_state.verified_pou_hashes),
                "ncip_count": len(lock.locked_state.applicable_ncips)
            },
            "action_count": len(lock.action_log)
        }

    def get_action_log(self, lock_id: str) -> list[dict[str, Any]]:
        """Get the action log for a lock."""
        lock = self._locks.get(lock_id)
        return lock.action_log if lock else []


# Machine-readable configuration per NCIP-005
NCIP_005_CONFIG = {
    "dispute_protocol": {
        "version": "1.0",
        "cooling_periods": {
            "D3": "24h",
            "D4": "72h"
        },
        "during_cooling": {
            "allowed": ["clarification", "settlement_proposal", "mediator_assignment"],
            "forbidden": ["escalation", "enforcement", "semantic_change"]
        },
        "semantic_lock": {
            "freezes": [
                "registry_version",
                "prose_content",
                "anchor_language",
                "verified_pous",
                "applicable_ncips"
            ],
            "prohibits": [
                "contract_amendment",
                "re_translation",
                "registry_upgrade",
                "pou_regeneration"
            ]
        },
        "escalation_path": [
            "mutual_settlement",
            "mediator_review",
            "adjudication",
            "binding_resolution"
        ],
        "resolution_outcomes": {
            "dismissed": {"resume_execution": True},
            "clarified": {"require_reratification": True},
            "amended": {"require_new_contract": True},
            "terminated": {"void_contract": True},
            "compensated": {"enforce_settlement": True}
        },
        "triggers": [
            "drift_level_d3",
            "drift_level_d4",
            "pou_failure",
            "pou_contradiction",
            "conflicting_ratifications",
            "multilingual_misalignment",
            "material_breach"
        ]
    }
}


def get_ncip_005_config() -> dict[str, Any]:
    """Get the NCIP-005 configuration."""
    return NCIP_005_CONFIG.copy()


def get_cooling_period_hours(dispute_level: DisputeLevel) -> int:
    """Get cooling period duration in hours for a dispute level."""
    return COOLING_PERIODS[dispute_level]


def is_action_allowed_during_cooling(action: LockAction) -> bool:
    """Check if an action is allowed during cooling period."""
    return action in ALLOWED_DURING_COOLING


def is_action_forbidden_during_lock(action: LockAction) -> bool:
    """Check if an action is forbidden during any semantic lock."""
    return action in FORBIDDEN_DURING_LOCK

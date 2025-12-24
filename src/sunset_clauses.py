"""
NCIP-015: Sunset Clauses, Archival Finality & Historical Semantics

This module implements temporal governance and semantic preservation:
- Sunset clauses with 6 trigger types
- Entry state machine (DRAFT → RATIFIED → ACTIVE → SUNSET_PENDING → SUNSET → ARCHIVED)
- Archival finality (irreversible, semantics frozen forever)
- Historical semantics preservation (meaning at T₀)
- Temporal context binding

Core Principle: Meaning may expire. History must not.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib


class SunsetTriggerType(Enum):
    """
    Sunset trigger types per NCIP-015 Section 3.2.
    """
    TIME_BASED = "time_based"              # Fixed datetime or duration
    EVENT_BASED = "event_based"            # External or oracle-verified event
    CONDITION_FULFILLED = "condition_fulfilled"  # Explicit semantic completion
    EXHAUSTION = "exhaustion"              # Finite-use depletion
    REVOCATION = "revocation"              # Explicit revocation under allowed terms
    CONSTITUTIONAL = "constitutional"       # Triggered by NCIP-014 amendment


class EntryState(Enum):
    """
    Entry lifecycle states per NCIP-015 Section 4.

    State machine: DRAFT → RATIFIED → ACTIVE → SUNSET_PENDING → SUNSET → ARCHIVED
    No backward transitions permitted.
    """
    DRAFT = "draft"
    RATIFIED = "ratified"
    ACTIVE = "active"
    SUNSET_PENDING = "sunset_pending"  # Allows notice & cooling
    SUNSET = "sunset"                   # Ends enforceability
    ARCHIVED = "archived"               # Locks semantics permanently


class EntryType(Enum):
    """Types of entries with default sunset policies."""
    CONTRACT = "contract"           # Default: 20 years
    LICENSE = "license"             # Default: 10 years
    DELEGATION = "delegation"       # Default: 2 years
    STANDING_INTENT = "standing_intent"  # Default: 1 year
    DISPUTE = "dispute"             # Default: On resolution
    SETTLEMENT = "settlement"       # Default: Immediate archive


# Default sunset durations per NCIP-015 Section 14
DEFAULT_SUNSET_YEARS = {
    EntryType.CONTRACT: 20,
    EntryType.LICENSE: 10,
    EntryType.DELEGATION: 2,
    EntryType.STANDING_INTENT: 1,
    EntryType.DISPUTE: None,        # On resolution
    EntryType.SETTLEMENT: 0,        # Immediate archive
}

# Valid state transitions (forward only)
VALID_TRANSITIONS = {
    EntryState.DRAFT: [EntryState.RATIFIED],
    EntryState.RATIFIED: [EntryState.ACTIVE],
    EntryState.ACTIVE: [EntryState.SUNSET_PENDING],
    EntryState.SUNSET_PENDING: [EntryState.SUNSET],
    EntryState.SUNSET: [EntryState.ARCHIVED],
    EntryState.ARCHIVED: [],  # Terminal state
}


@dataclass
class TemporalContext:
    """
    Temporal context binding per NCIP-015 Section 7.

    This bundle is immutable once archived.
    """
    registry_version: str
    language_variant: str
    jurisdiction_context: str
    proof_of_understanding_ids: List[str] = field(default_factory=list)
    validator_consensus_snapshot: Dict[str, Any] = field(default_factory=dict)

    # Binding timestamp
    bound_at: datetime = field(default_factory=datetime.utcnow)

    def to_hash(self) -> str:
        """Generate immutable hash of temporal context."""
        content = (
            f"{self.registry_version}|{self.language_variant}|"
            f"{self.jurisdiction_context}|{','.join(sorted(self.proof_of_understanding_ids))}|"
            f"{self.bound_at.isoformat()}"
        )
        return hashlib.sha256(content.encode()).hexdigest()[:16]


@dataclass
class SunsetClause:
    """
    A sunset clause per NCIP-015 Section 3.

    Sunsets MUST NOT:
    - Alter historical semantics
    - Delete or redact records
    - Enable reinterpretation
    """
    clause_id: str
    entry_id: str
    trigger_type: SunsetTriggerType

    # Trigger conditions
    trigger_datetime: Optional[datetime] = None  # For time_based
    trigger_event: Optional[str] = None          # For event_based
    trigger_condition: Optional[str] = None      # For condition_fulfilled
    max_uses: Optional[int] = None               # For exhaustion
    revocation_terms: Optional[str] = None       # For revocation
    amendment_id: Optional[str] = None           # For constitutional

    # Configuration
    notice_period_days: int = 30
    declared_at: datetime = field(default_factory=datetime.utcnow)

    # Status
    triggered: bool = False
    triggered_at: Optional[datetime] = None
    trigger_reason: Optional[str] = None

    # Usage tracking (for exhaustion type)
    current_uses: int = 0

    def is_explicit(self) -> bool:
        """Check if sunset clause is explicit (required per Section 3.3)."""
        if self.trigger_type == SunsetTriggerType.TIME_BASED:
            return self.trigger_datetime is not None
        elif self.trigger_type == SunsetTriggerType.EVENT_BASED:
            return self.trigger_event is not None
        elif self.trigger_type == SunsetTriggerType.CONDITION_FULFILLED:
            return self.trigger_condition is not None
        elif self.trigger_type == SunsetTriggerType.EXHAUSTION:
            return self.max_uses is not None
        elif self.trigger_type == SunsetTriggerType.REVOCATION:
            return self.revocation_terms is not None
        elif self.trigger_type == SunsetTriggerType.CONSTITUTIONAL:
            return self.amendment_id is not None
        return False

    def check_trigger(self, current_time: Optional[datetime] = None) -> Tuple[bool, str]:
        """Check if sunset should trigger."""
        now = current_time or datetime.utcnow()

        if self.trigger_type == SunsetTriggerType.TIME_BASED:
            if self.trigger_datetime and now >= self.trigger_datetime:
                return (True, f"Time-based sunset reached: {self.trigger_datetime.isoformat()}")

        elif self.trigger_type == SunsetTriggerType.EXHAUSTION:
            if self.max_uses and self.current_uses >= self.max_uses:
                return (True, f"Exhaustion limit reached: {self.current_uses}/{self.max_uses}")

        return (False, "Sunset conditions not met")

    def record_use(self) -> bool:
        """Record a use for exhaustion-type clauses."""
        if self.trigger_type == SunsetTriggerType.EXHAUSTION:
            self.current_uses += 1
            return True
        return False


@dataclass
class ArchivedEntry:
    """
    An archived entry per NCIP-015 Section 5.

    Archival Finality means:
    - Semantics are frozen forever
    - Drift detection is disabled
    - No reinterpretation is permitted
    - Entry is admissible as historical fact only
    """
    archive_id: str
    entry_id: str
    entry_type: EntryType

    # Original content (preserved exactly)
    prose_content: str
    original_meaning: str  # Meaning as understood at T₀

    # Temporal context (immutable bundle)
    temporal_context: TemporalContext

    # State history
    ratified_at: datetime
    activated_at: datetime
    sunset_at: datetime
    archived_at: datetime = field(default_factory=datetime.utcnow)

    # Sunset details
    sunset_clause: Optional[SunsetClause] = None

    # Archive properties
    enforceable: bool = False      # Always False for archived
    negotiable: bool = False       # Always False for archived
    referential_only: bool = True  # Always True for archived
    drift_detection_disabled: bool = True  # Always True for archived

    # Hash for integrity verification
    archive_hash: Optional[str] = None

    def __post_init__(self):
        """Compute archive hash."""
        if self.archive_hash is None:
            self.archive_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute immutable hash of archived content."""
        content = (
            f"{self.entry_id}|{self.prose_content}|{self.original_meaning}|"
            f"{self.temporal_context.to_hash()}|{self.ratified_at.isoformat()}|"
            f"{self.archived_at.isoformat()}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify archive has not been tampered with."""
        return self.archive_hash == self._compute_hash()


@dataclass
class ManagedEntry:
    """
    An entry managed through the sunset lifecycle.
    """
    entry_id: str
    entry_type: EntryType
    prose_content: str

    # State
    state: EntryState = EntryState.DRAFT

    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    ratified_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None
    sunset_pending_at: Optional[datetime] = None
    sunset_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    # Sunset clause
    sunset_clause: Optional[SunsetClause] = None

    # Temporal context
    temporal_context: Optional[TemporalContext] = None

    # Original meaning (captured at ratification)
    original_meaning: Optional[str] = None

    # Emergency pause (per NCIP-013)
    emergency_paused: bool = False
    emergency_id: Optional[str] = None

    # State history for audit
    state_history: List[Tuple[EntryState, datetime]] = field(default_factory=list)

    def __post_init__(self):
        """Initialize state history."""
        if not self.state_history:
            self.state_history.append((self.state, self.created_at))


class SunsetManager:
    """
    Manages sunset clauses, state transitions, and archival per NCIP-015.

    Responsibilities:
    - Sunset clause declaration and validation
    - State machine enforcement
    - Archival finality
    - Historical semantics preservation
    - Validator behavior enforcement
    - Mediator constraint checking
    """

    # Archive delay after sunset (days)
    DEFAULT_ARCHIVE_DELAY_DAYS = 90

    # Default horizon if unspecified (years)
    DEFAULT_HORIZON_YEARS = 20

    def __init__(self):
        self.entries: Dict[str, ManagedEntry] = {}
        self.sunset_clauses: Dict[str, SunsetClause] = {}
        self.archives: Dict[str, ArchivedEntry] = {}

        self.entry_counter = 0
        self.clause_counter = 0
        self.archive_counter = 0

    # -------------------------------------------------------------------------
    # Entry Management
    # -------------------------------------------------------------------------

    def create_entry(
        self,
        entry_type: EntryType,
        prose_content: str,
        entry_id: Optional[str] = None
    ) -> ManagedEntry:
        """Create a new entry in DRAFT state."""
        self.entry_counter += 1
        if entry_id is None:
            entry_id = f"ENTRY-{datetime.utcnow().strftime('%Y%m%d')}-{self.entry_counter:04d}"

        entry = ManagedEntry(
            entry_id=entry_id,
            entry_type=entry_type,
            prose_content=prose_content,
            state=EntryState.DRAFT
        )

        self.entries[entry_id] = entry
        return entry

    def get_entry(self, entry_id: str) -> Optional[ManagedEntry]:
        """Get an entry by ID."""
        return self.entries.get(entry_id)

    # -------------------------------------------------------------------------
    # State Machine
    # -------------------------------------------------------------------------

    def transition_state(
        self,
        entry_id: str,
        new_state: EntryState,
        temporal_context: Optional[TemporalContext] = None,
        original_meaning: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Transition entry to a new state per NCIP-015 Section 4.

        No backward transitions are permitted.
        """
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        # Check for emergency pause
        if entry.emergency_paused and new_state in [EntryState.SUNSET_PENDING, EntryState.SUNSET]:
            return (False, "Cannot transition during emergency pause - sunset timers paused per NCIP-013")

        # Validate transition
        valid_next_states = VALID_TRANSITIONS.get(entry.state, [])
        if new_state not in valid_next_states:
            return (False, f"Invalid transition: {entry.state.value} → {new_state.value}. "
                         f"Valid transitions: {[s.value for s in valid_next_states]}")

        now = datetime.utcnow()
        old_state = entry.state
        entry.state = new_state
        entry.state_history.append((new_state, now))

        # Handle state-specific logic
        if new_state == EntryState.RATIFIED:
            entry.ratified_at = now
            if temporal_context:
                entry.temporal_context = temporal_context
            if original_meaning:
                entry.original_meaning = original_meaning
            # Apply default sunset if not specified
            if not entry.sunset_clause:
                self._apply_default_sunset(entry)

        elif new_state == EntryState.ACTIVE:
            entry.activated_at = now

        elif new_state == EntryState.SUNSET_PENDING:
            entry.sunset_pending_at = now

        elif new_state == EntryState.SUNSET:
            entry.sunset_at = now

        elif new_state == EntryState.ARCHIVED:
            entry.archived_at = now
            self._create_archive(entry)

        return (True, f"Transitioned from {old_state.value} to {new_state.value}")

    def _apply_default_sunset(self, entry: ManagedEntry) -> None:
        """Apply default sunset policy per NCIP-015 Section 14."""
        default_years = DEFAULT_SUNSET_YEARS.get(entry.entry_type)

        if default_years is None:
            # Dispute type - sunset on resolution (handled separately)
            return

        if default_years == 0:
            # Settlement type - immediate archive (handled separately)
            return

        # Create time-based sunset clause
        self.clause_counter += 1
        clause_id = f"SUNSET-{entry.entry_id}-{self.clause_counter:04d}"

        trigger_datetime = datetime.utcnow() + timedelta(days=default_years * 365)

        clause = SunsetClause(
            clause_id=clause_id,
            entry_id=entry.entry_id,
            trigger_type=SunsetTriggerType.TIME_BASED,
            trigger_datetime=trigger_datetime,
            notice_period_days=30
        )

        entry.sunset_clause = clause
        self.sunset_clauses[clause_id] = clause

    def can_transition(self, entry_id: str, new_state: EntryState) -> Tuple[bool, str]:
        """Check if transition is valid without performing it."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if entry.emergency_paused and new_state in [EntryState.SUNSET_PENDING, EntryState.SUNSET]:
            return (False, "Emergency pause active")

        valid_next_states = VALID_TRANSITIONS.get(entry.state, [])
        if new_state not in valid_next_states:
            return (False, f"Invalid transition from {entry.state.value}")

        return (True, "Transition allowed")

    # -------------------------------------------------------------------------
    # Sunset Clauses
    # -------------------------------------------------------------------------

    def declare_sunset(
        self,
        entry_id: str,
        trigger_type: SunsetTriggerType,
        trigger_datetime: Optional[datetime] = None,
        trigger_event: Optional[str] = None,
        trigger_condition: Optional[str] = None,
        max_uses: Optional[int] = None,
        revocation_terms: Optional[str] = None,
        amendment_id: Optional[str] = None,
        notice_period_days: int = 30
    ) -> Tuple[Optional[SunsetClause], List[str]]:
        """
        Declare a sunset clause per NCIP-015 Section 3.

        All sunset clauses MUST be explicit.
        Implicit sunsets are invalid.
        """
        errors = []

        entry = self.entries.get(entry_id)
        if not entry:
            errors.append(f"Entry {entry_id} not found")
            return (None, errors)

        if entry.state not in [EntryState.DRAFT, EntryState.RATIFIED]:
            errors.append("Sunset clauses must be declared before entry becomes ACTIVE")
            return (None, errors)

        self.clause_counter += 1
        clause_id = f"SUNSET-{entry_id}-{self.clause_counter:04d}"

        clause = SunsetClause(
            clause_id=clause_id,
            entry_id=entry_id,
            trigger_type=trigger_type,
            trigger_datetime=trigger_datetime,
            trigger_event=trigger_event,
            trigger_condition=trigger_condition,
            max_uses=max_uses,
            revocation_terms=revocation_terms,
            amendment_id=amendment_id,
            notice_period_days=notice_period_days
        )

        # Validate explicitness
        if not clause.is_explicit():
            errors.append(f"Sunset clause must be explicit for trigger type: {trigger_type.value}")
            return (None, errors)

        entry.sunset_clause = clause
        self.sunset_clauses[clause_id] = clause

        return (clause, [])

    def check_sunset_triggers(self) -> List[Dict[str, Any]]:
        """Check all active entries for sunset triggers."""
        triggered = []
        now = datetime.utcnow()

        for entry_id, entry in self.entries.items():
            if entry.state != EntryState.ACTIVE:
                continue

            if entry.emergency_paused:
                continue

            if entry.sunset_clause:
                should_trigger, reason = entry.sunset_clause.check_trigger(now)
                if should_trigger:
                    triggered.append({
                        "entry_id": entry_id,
                        "clause_id": entry.sunset_clause.clause_id,
                        "trigger_type": entry.sunset_clause.trigger_type.value,
                        "reason": reason
                    })

        return triggered

    def trigger_sunset(
        self,
        entry_id: str,
        trigger_reason: str
    ) -> Tuple[bool, str]:
        """
        Trigger sunset for an entry.

        Initiates SUNSET_PENDING state with notice period.
        """
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if entry.state != EntryState.ACTIVE:
            return (False, f"Cannot trigger sunset from state: {entry.state.value}")

        if entry.sunset_clause:
            entry.sunset_clause.triggered = True
            entry.sunset_clause.triggered_at = datetime.utcnow()
            entry.sunset_clause.trigger_reason = trigger_reason

        # Transition to SUNSET_PENDING
        success, msg = self.transition_state(entry_id, EntryState.SUNSET_PENDING)
        if not success:
            return (False, msg)

        return (True, f"Sunset triggered for {entry_id}: {trigger_reason}")

    def complete_sunset(self, entry_id: str) -> Tuple[bool, str]:
        """Complete sunset after notice period, transition to SUNSET state."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if entry.state != EntryState.SUNSET_PENDING:
            return (False, f"Cannot complete sunset from state: {entry.state.value}")

        # Check notice period
        if entry.sunset_pending_at and entry.sunset_clause:
            notice_end = entry.sunset_pending_at + timedelta(days=entry.sunset_clause.notice_period_days)
            if datetime.utcnow() < notice_end:
                days_remaining = (notice_end - datetime.utcnow()).days
                return (False, f"Notice period not complete. {days_remaining} days remaining.")

        return self.transition_state(entry_id, EntryState.SUNSET)

    def record_event_trigger(
        self,
        entry_id: str,
        event_description: str,
        oracle_evidence: Optional[str] = None
    ) -> Tuple[bool, str]:
        """Record an event trigger for event-based sunset."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if not entry.sunset_clause:
            return (False, "No sunset clause defined")

        if entry.sunset_clause.trigger_type != SunsetTriggerType.EVENT_BASED:
            return (False, "Sunset clause is not event-based")

        return self.trigger_sunset(entry_id, f"Event occurred: {event_description}")

    def record_condition_fulfilled(
        self,
        entry_id: str,
        fulfillment_description: str
    ) -> Tuple[bool, str]:
        """Record condition fulfillment for condition-based sunset."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if not entry.sunset_clause:
            return (False, "No sunset clause defined")

        if entry.sunset_clause.trigger_type != SunsetTriggerType.CONDITION_FULFILLED:
            return (False, "Sunset clause is not condition-based")

        return self.trigger_sunset(entry_id, f"Condition fulfilled: {fulfillment_description}")

    def record_use(self, entry_id: str) -> Dict[str, Any]:
        """Record a use for exhaustion-type sunset clauses."""
        entry = self.entries.get(entry_id)
        if not entry:
            return {"status": "error", "message": f"Entry {entry_id} not found"}

        if not entry.sunset_clause:
            return {"status": "error", "message": "No sunset clause defined"}

        if entry.sunset_clause.trigger_type != SunsetTriggerType.EXHAUSTION:
            return {"status": "error", "message": "Sunset clause is not exhaustion-based"}

        entry.sunset_clause.record_use()

        result = {
            "status": "recorded",
            "entry_id": entry_id,
            "current_uses": entry.sunset_clause.current_uses,
            "max_uses": entry.sunset_clause.max_uses
        }

        # Check if exhausted
        if entry.sunset_clause.current_uses >= entry.sunset_clause.max_uses:
            self.trigger_sunset(entry_id, f"Exhaustion limit reached: {entry.sunset_clause.current_uses}/{entry.sunset_clause.max_uses}")
            result["sunset_triggered"] = True

        return result

    def process_revocation(
        self,
        entry_id: str,
        revoker_id: str,
        revocation_reason: str
    ) -> Tuple[bool, str]:
        """Process explicit revocation under allowed terms."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if not entry.sunset_clause:
            return (False, "No sunset clause defined")

        if entry.sunset_clause.trigger_type != SunsetTriggerType.REVOCATION:
            return (False, "Sunset clause does not allow revocation")

        return self.trigger_sunset(entry_id, f"Revoked by {revoker_id}: {revocation_reason}")

    # -------------------------------------------------------------------------
    # Archival
    # -------------------------------------------------------------------------

    def archive_entry(
        self,
        entry_id: str
    ) -> Tuple[Optional[ArchivedEntry], str]:
        """
        Archive an entry per NCIP-015 Section 5.

        Archival Finality means:
        - Semantics are frozen forever
        - Drift detection is disabled
        - No reinterpretation is permitted
        """
        entry = self.entries.get(entry_id)
        if not entry:
            return (None, f"Entry {entry_id} not found")

        if entry.state != EntryState.SUNSET:
            return (None, f"Cannot archive from state: {entry.state.value}. Must be SUNSET.")

        # Transition to ARCHIVED
        success, msg = self.transition_state(entry_id, EntryState.ARCHIVED)
        if not success:
            return (None, msg)

        # Return the created archive
        archive = self.archives.get(f"ARCHIVE-{entry_id}")
        return (archive, "Entry archived successfully")

    def _create_archive(self, entry: ManagedEntry) -> ArchivedEntry:
        """Create an archived entry."""
        self.archive_counter += 1
        archive_id = f"ARCHIVE-{entry.entry_id}"

        # Ensure temporal context exists
        if not entry.temporal_context:
            entry.temporal_context = TemporalContext(
                registry_version="unknown",
                language_variant="en",
                jurisdiction_context="unspecified"
            )

        archive = ArchivedEntry(
            archive_id=archive_id,
            entry_id=entry.entry_id,
            entry_type=entry.entry_type,
            prose_content=entry.prose_content,
            original_meaning=entry.original_meaning or "Meaning not captured",
            temporal_context=entry.temporal_context,
            ratified_at=entry.ratified_at or entry.created_at,
            activated_at=entry.activated_at or entry.created_at,
            sunset_at=entry.sunset_at or datetime.utcnow(),
            archived_at=datetime.utcnow(),
            sunset_clause=entry.sunset_clause
        )

        self.archives[archive_id] = archive
        return archive

    def get_archive(self, entry_id: str) -> Optional[ArchivedEntry]:
        """Get an archived entry."""
        return self.archives.get(f"ARCHIVE-{entry_id}")

    def check_archive_eligibility(self, entry_id: str) -> Dict[str, Any]:
        """Check if entry is eligible for archival."""
        entry = self.entries.get(entry_id)
        if not entry:
            return {"eligible": False, "reason": f"Entry {entry_id} not found"}

        if entry.state == EntryState.ARCHIVED:
            return {"eligible": False, "reason": "Already archived"}

        if entry.state != EntryState.SUNSET:
            return {"eligible": False, "reason": f"Must be in SUNSET state, currently: {entry.state.value}"}

        # Check archive delay
        if entry.sunset_at:
            archive_eligible_at = entry.sunset_at + timedelta(days=self.DEFAULT_ARCHIVE_DELAY_DAYS)
            if datetime.utcnow() < archive_eligible_at:
                days_remaining = (archive_eligible_at - datetime.utcnow()).days
                return {
                    "eligible": False,
                    "reason": f"Archive delay not complete. {days_remaining} days remaining."
                }

        return {"eligible": True, "reason": "Entry is eligible for archival"}

    # -------------------------------------------------------------------------
    # Historical Semantics
    # -------------------------------------------------------------------------

    def validate_historical_reference(
        self,
        archived_entry_id: str,
        proposed_interpretation: str
    ) -> Dict[str, Any]:
        """
        Validate a reference to historical/archived entry.

        Per NCIP-015 Section 6: Validators MUST reject reinterpretation attempts.
        """
        archive = self.archives.get(f"ARCHIVE-{archived_entry_id}")
        if not archive:
            return {
                "valid": False,
                "reason": f"Archived entry {archived_entry_id} not found"
            }

        return {
            "valid": True,
            "archived_entry_id": archived_entry_id,
            "original_meaning": archive.original_meaning,
            "ratified_at": archive.ratified_at.isoformat(),
            "registry_version": archive.temporal_context.registry_version,
            "warning": "Historical entry - referential only, not enforceable",
            "reinterpretation_rejected": True,
            "rule": "Historical entries retain original meaning at T₀"
        }

    def reject_retroactive_application(
        self,
        archived_entry_id: str,
        attempted_action: str
    ) -> Dict[str, Any]:
        """
        Reject attempt to apply new definitions retroactively.

        Per NCIP-015 Section 6.2.
        """
        return {
            "rejected": True,
            "archived_entry_id": archived_entry_id,
            "attempted_action": attempted_action,
            "reason": "Cannot apply new definitions retroactively to archived entries",
            "rule": "NCIP-015 Section 6.2: Validators MUST reject retroactive application"
        }

    # -------------------------------------------------------------------------
    # Validator Behavior
    # -------------------------------------------------------------------------

    def validator_check(self, entry_id: str) -> Dict[str, Any]:
        """
        Validator behavior check per NCIP-015 Section 8.

        Validators MUST:
        - Enforce sunset triggers exactly as declared
        - Transition state deterministically
        - Disable semantic drift checks post-archive
        - Reject new obligations referencing archived semantics unless restated
        """
        entry = self.entries.get(entry_id)
        archive = self.archives.get(f"ARCHIVE-{entry_id}")

        if archive:
            return {
                "entry_id": entry_id,
                "state": "archived",
                "drift_detection_enabled": False,
                "enforceable": False,
                "referential_only": True,
                "integrity_verified": archive.verify_integrity(),
                "validator_action": "reject_new_obligations_unless_restated",
                "principle": "Meaning may expire. History must not."
            }

        if not entry:
            return {
                "entry_id": entry_id,
                "status": "not_found"
            }

        checks = {
            "has_explicit_sunset": entry.sunset_clause is not None and entry.sunset_clause.is_explicit(),
            "state_valid": entry.state in EntryState,
            "temporal_context_bound": entry.temporal_context is not None if entry.state != EntryState.DRAFT else True
        }

        # Check if sunset should trigger
        sunset_status = None
        if entry.sunset_clause and entry.state == EntryState.ACTIVE:
            should_trigger, reason = entry.sunset_clause.check_trigger()
            sunset_status = {
                "should_trigger": should_trigger,
                "reason": reason
            }

        return {
            "entry_id": entry_id,
            "state": entry.state.value,
            "checks": checks,
            "sunset_status": sunset_status,
            "drift_detection_enabled": entry.state not in [EntryState.SUNSET, EntryState.ARCHIVED],
            "enforceable": entry.state == EntryState.ACTIVE,
            "principle": "Meaning may expire. History must not."
        }

    # -------------------------------------------------------------------------
    # Mediator Constraints
    # -------------------------------------------------------------------------

    def mediator_can_cite(self, entry_id: str) -> Dict[str, Any]:
        """
        Check if mediator can cite an entry.

        Per NCIP-015 Section 9: Mediators MAY cite archived entries as context.
        """
        archive = self.archives.get(f"ARCHIVE-{entry_id}")
        if archive:
            return {
                "can_cite": True,
                "as_context_only": True,
                "can_propose_action": False,
                "reason": "Archived entries can be cited as context but cannot compel action"
            }

        entry = self.entries.get(entry_id)
        if not entry:
            return {"can_cite": False, "reason": f"Entry {entry_id} not found"}

        return {
            "can_cite": True,
            "as_context_only": entry.state in [EntryState.SUNSET, EntryState.ARCHIVED],
            "can_propose_action": entry.state == EntryState.ACTIVE,
            "current_state": entry.state.value
        }

    def mediator_restatement_required(
        self,
        archived_entry_id: str,
        proposed_reactivation: str
    ) -> Dict[str, Any]:
        """
        Check if mediator properly restates historical semantics.

        Per NCIP-015 Section 9: Mediators MUST restate any historical semantics
        they wish to reactivate.
        """
        archive = self.archives.get(f"ARCHIVE-{archived_entry_id}")
        if not archive:
            return {
                "restatement_required": False,
                "reason": f"Entry {archived_entry_id} is not archived"
            }

        return {
            "restatement_required": True,
            "original_meaning": archive.original_meaning,
            "proposed_reactivation": proposed_reactivation,
            "rule": "Mediators MUST restate historical semantics to reactivate",
            "guidance": "History can inform. It cannot compel."
        }

    # -------------------------------------------------------------------------
    # Emergency Integration (NCIP-013)
    # -------------------------------------------------------------------------

    def pause_sunset_timer(
        self,
        entry_id: str,
        emergency_id: str
    ) -> Tuple[bool, str]:
        """
        Pause sunset timer during emergency per NCIP-015 Section 11.

        Sunset timers MAY pause during emergency.
        Semantics MUST remain unchanged.
        """
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        entry.emergency_paused = True
        entry.emergency_id = emergency_id

        return (True, f"Sunset timer paused for {entry_id} during emergency {emergency_id}")

    def resume_sunset_timer(
        self,
        entry_id: str
    ) -> Tuple[bool, str]:
        """Resume sunset timer after emergency resolution."""
        entry = self.entries.get(entry_id)
        if not entry:
            return (False, f"Entry {entry_id} not found")

        if not entry.emergency_paused:
            return (False, "Sunset timer is not paused")

        entry.emergency_paused = False
        entry.emergency_id = None

        return (True, f"Sunset timer resumed for {entry_id}")

    # -------------------------------------------------------------------------
    # Machine-Readable Schema
    # -------------------------------------------------------------------------

    def generate_sunset_schema(self, entry_id: str) -> Dict[str, Any]:
        """
        Generate machine-readable sunset & archive schema per NCIP-015 Section 10.
        """
        entry = self.entries.get(entry_id)
        archive = self.archives.get(f"ARCHIVE-{entry_id}")

        if archive:
            return {
                "sunset_and_archive": {
                    "version": "1.0",
                    "entry_id": entry_id,
                    "state": "archived",
                    "sunset": {
                        "type": archive.sunset_clause.trigger_type.value if archive.sunset_clause else "default",
                        "triggered_at": archive.sunset_at.isoformat()
                    },
                    "post_sunset_state": {
                        "enforceable": False,
                        "negotiable": False,
                        "referential_only": True
                    },
                    "archival": {
                        "archived_at": archive.archived_at.isoformat(),
                        "preserve": [
                            "prose_content",
                            "registry_version",
                            "language",
                            "jurisdiction",
                            "proof_of_understanding",
                            "validator_snapshot"
                        ],
                        "archive_hash": archive.archive_hash
                    },
                    "validator_rules": {
                        "reject_reactivation_without_restatement": True,
                        "disable_drift_detection": True
                    }
                }
            }

        if not entry:
            return {"error": f"Entry {entry_id} not found"}

        sunset_config = None
        if entry.sunset_clause:
            sunset_config = {
                "type": entry.sunset_clause.trigger_type.value,
                "notice_period_days": entry.sunset_clause.notice_period_days
            }
            if entry.sunset_clause.trigger_datetime:
                sunset_config["trigger"] = {
                    "datetime": entry.sunset_clause.trigger_datetime.isoformat()
                }
            if entry.sunset_clause.max_uses:
                sunset_config["trigger"] = {
                    "max_uses": entry.sunset_clause.max_uses,
                    "current_uses": entry.sunset_clause.current_uses
                }

        return {
            "sunset_and_archive": {
                "version": "1.0",
                "entry_id": entry_id,
                "state": entry.state.value,
                "sunset": sunset_config,
                "post_sunset_state": {
                    "enforceable": False,
                    "negotiable": False,
                    "referential_only": True
                },
                "archival": {
                    "auto_archive": True,
                    "archive_after_days": self.DEFAULT_ARCHIVE_DELAY_DAYS,
                    "preserve": [
                        "prose_content",
                        "registry_version",
                        "language",
                        "jurisdiction",
                        "proof_of_understanding",
                        "validator_snapshot"
                    ]
                },
                "validator_rules": {
                    "reject_reactivation_without_restatement": True,
                    "disable_drift_detection": entry.state in [EntryState.SUNSET, EntryState.ARCHIVED]
                }
            }
        }

    # -------------------------------------------------------------------------
    # Status & Reporting
    # -------------------------------------------------------------------------

    def get_entries_by_state(self, state: EntryState) -> List[ManagedEntry]:
        """Get all entries in a given state."""
        return [e for e in self.entries.values() if e.state == state]

    def get_expiring_entries(self, days_ahead: int = 30) -> List[Dict[str, Any]]:
        """Get entries expiring within specified days."""
        expiring = []
        now = datetime.utcnow()
        cutoff = now + timedelta(days=days_ahead)

        for entry in self.entries.values():
            if entry.state != EntryState.ACTIVE:
                continue
            if not entry.sunset_clause:
                continue
            if entry.sunset_clause.trigger_type == SunsetTriggerType.TIME_BASED:
                if entry.sunset_clause.trigger_datetime and entry.sunset_clause.trigger_datetime <= cutoff:
                    expiring.append({
                        "entry_id": entry.entry_id,
                        "entry_type": entry.entry_type.value,
                        "sunset_date": entry.sunset_clause.trigger_datetime.isoformat(),
                        "days_until_sunset": (entry.sunset_clause.trigger_datetime - now).days
                    })

        return sorted(expiring, key=lambda x: x["days_until_sunset"])

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of sunset system status."""
        state_counts = {}
        for entry in self.entries.values():
            state = entry.state.value
            state_counts[state] = state_counts.get(state, 0) + 1

        type_counts = {}
        for entry in self.entries.values():
            etype = entry.entry_type.value
            type_counts[etype] = type_counts.get(etype, 0) + 1

        return {
            "total_entries": len(self.entries),
            "total_archives": len(self.archives),
            "state_counts": state_counts,
            "type_counts": type_counts,
            "sunset_clauses_defined": len(self.sunset_clauses),
            "emergency_paused_entries": sum(1 for e in self.entries.values() if e.emergency_paused),
            "principle": "Meaning may expire. History must not."
        }

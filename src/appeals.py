"""
NCIP-008: Semantic Appeals, Precedent & Case Law Encoding

This module implements semantic appeals, Semantic Case Records (SCRs),
and precedent encoding while preserving:
- Non-binding precedent (advisory signal, not law)
- Explicit intent priority over precedent
- Append-only case record integrity
- Human-centered jurisprudence

Core Principle: Past meaning may inform future interpretation —
but never replace explicit present intent.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import re


class AppealableItem(Enum):
    """Items that may be appealed per NCIP-008 Section 3.1."""
    VALIDATOR_REJECTION = "validator_rejection"      # D2-D4 rejections
    DRIFT_CLASSIFICATION = "drift_classification"    # Drift level disputes
    POU_MISMATCH = "pou_mismatch"                   # Proof of Understanding mismatch
    MEDIATOR_INTERPRETATION = "mediator_interpretation"  # Mediator semantic interpretation


class NonAppealableItem(Enum):
    """Items that cannot be appealed per NCIP-008 Section 3.1."""
    TERM_REGISTRY_MAPPING = "term_registry_mapping"  # Requires NCIP-001 update
    SETTLEMENT_OUTCOME = "settlement_outcome"        # Final settlements


class AppealStatus(Enum):
    """Appeal lifecycle states per NCIP-008 Section 3.3."""
    DECLARED = "declared"              # Appeal submitted
    SEMANTIC_LOCK_APPLIED = "locked"   # Scoped lock on disputed terms
    UNDER_REVIEW = "under_review"      # Review panel evaluating
    AWAITING_RATIFICATION = "awaiting_ratification"  # Pending human ratification
    RESOLVED = "resolved"              # Resolution recorded
    REJECTED = "rejected"              # Appeal rejected (invalid/frivolous)
    EXPIRED = "expired"                # Review window expired


class AppealOutcome(Enum):
    """Possible appeal outcomes."""
    UPHELD = "upheld"                  # Original decision upheld
    OVERTURNED = "overturned"          # Original decision overturned
    PARTIALLY_REVISED = "partially_revised"  # Classification revised
    DISMISSED = "dismissed"            # Appeal dismissed (procedural)


class PrecedentWeight(Enum):
    """Precedent weight decay per NCIP-008 Section 6.2."""
    HIGH = "high"        # < 3 months
    MEDIUM = "medium"    # 3-12 months
    LOW = "low"          # > 12 months
    ZERO = "zero"        # Superseded term registry


class DriftLevel(Enum):
    """Drift levels per NCIP-002."""
    D0 = "D0"
    D1 = "D1"
    D2 = "D2"
    D3 = "D3"
    D4 = "D4"


@dataclass
class AppealReference:
    """Required references for an appeal per NCIP-008 Section 3.2."""
    original_entry_id: str
    validator_decision_id: str
    drift_classification: DriftLevel

    # Optional additional context
    original_prose: Optional[str] = None
    pou_ids: List[str] = field(default_factory=list)  # Pre-dispute PoUs only


@dataclass
class ReviewPanelMember:
    """A member of the appeal review panel per NCIP-008 Section 4.1."""
    validator_id: str
    implementation_type: str  # e.g., "llm", "hybrid", "symbolic", "human"
    trust_score: float = 0.5

    def __hash__(self):
        return hash(self.validator_id)

    def __eq__(self, other):
        if isinstance(other, ReviewPanelMember):
            return self.validator_id == other.validator_id
        return False


@dataclass
class ReviewPanel:
    """
    Appeal review panel per NCIP-008 Section 4.1.

    Requirements:
    - N >= 3 validators
    - Distinct implementations (model diversity)
    - No overlap with original validators
    """
    members: List[ReviewPanelMember] = field(default_factory=list)
    original_validator_ids: Set[str] = field(default_factory=set)

    @property
    def is_valid(self) -> bool:
        """Check if panel meets requirements."""
        if len(self.members) < 3:
            return False

        # Check for distinct implementations
        implementations = set(m.implementation_type for m in self.members)
        if len(implementations) < 2:  # Need at least 2 different types
            return False

        # Check no overlap with original validators
        member_ids = set(m.validator_id for m in self.members)
        if member_ids & self.original_validator_ids:
            return False

        return True

    def add_member(self, member: ReviewPanelMember) -> Tuple[bool, str]:
        """Add a member to the panel."""
        if member.validator_id in self.original_validator_ids:
            return (False, "Member was an original validator - overlap not allowed")

        if any(m.validator_id == member.validator_id for m in self.members):
            return (False, "Member already on panel")

        self.members.append(member)
        return (True, f"Added {member.validator_id} to panel")


@dataclass
class AppealVote:
    """A vote from a review panel member."""
    validator_id: str
    vote: AppealOutcome
    revised_classification: Optional[DriftLevel] = None
    rationale: str = ""
    voted_at: datetime = field(default_factory=datetime.utcnow)


@dataclass
class SemanticCaseRecord:
    """
    Semantic Case Record (SCR) per NCIP-008 Section 5.

    SCRs are:
    - Append-only
    - Publicly queryable
    - Non-binding
    """
    case_id: str
    originating_entry: str
    appeal_reason: AppealableItem
    disputed_terms: List[str]

    # Outcome
    outcome: AppealOutcome
    upheld: bool
    revised_classification: Optional[DriftLevel] = None

    # Rationale
    rationale_summary: str = ""

    # References
    canonical_terms_version: str = ""
    prior_cases: List[str] = field(default_factory=list)

    # Metadata
    resolution_timestamp: datetime = field(default_factory=datetime.utcnow)
    human_ratification: bool = False
    human_ratifier_id: Optional[str] = None

    # Panel votes
    panel_votes: List[AppealVote] = field(default_factory=list)

    # Immutability
    _hash: Optional[str] = field(default=None, repr=False)

    def __post_init__(self):
        """Compute hash for integrity verification."""
        if self._hash is None:
            self._hash = self._compute_hash()

    def _compute_hash(self) -> str:
        """Compute hash of the SCR for integrity verification."""
        content = (
            f"{self.case_id}|{self.originating_entry}|{self.appeal_reason.value}|"
            f"{','.join(self.disputed_terms)}|{self.outcome.value}|{self.upheld}|"
            f"{self.rationale_summary}|{self.resolution_timestamp.isoformat()}"
        )
        return hashlib.sha256(content.encode()).hexdigest()

    def verify_integrity(self) -> bool:
        """Verify the SCR has not been modified."""
        return self._hash == self._compute_hash()

    def to_yaml_dict(self) -> Dict[str, Any]:
        """Generate YAML-compatible dictionary per NCIP-008 Section 5.2."""
        return {
            "semantic_case_record": {
                "case_id": self.case_id,
                "originating_entry": self.originating_entry,
                "appeal_reason": self.appeal_reason.value,
                "disputed_terms": self.disputed_terms,
                "outcome": {
                    "upheld": self.upheld,
                    "revised_classification": self.revised_classification.value if self.revised_classification else None
                },
                "rationale_summary": self.rationale_summary,
                "references": {
                    "canonical_terms_version": self.canonical_terms_version,
                    "prior_cases": self.prior_cases
                },
                "resolution_timestamp": self.resolution_timestamp.isoformat(),
                "human_ratification": self.human_ratification
            }
        }


@dataclass
class Appeal:
    """
    A semantic appeal per NCIP-008 Section 3.

    Appeals MUST:
    - Reference original entry, validator decision, drift classification
    - NOT introduce new intent
    - Pay non-refundable burn fee
    """
    appeal_id: str
    appellant_id: str
    appeal_type: AppealableItem
    reference: AppealReference

    # Appeal details
    disputed_terms: List[str] = field(default_factory=list)
    appeal_rationale: str = ""

    # Status tracking
    status: AppealStatus = AppealStatus.DECLARED
    declared_at: datetime = field(default_factory=datetime.utcnow)

    # Review window (default 7 days per Section 3.3)
    review_window_days: int = 7
    review_deadline: Optional[datetime] = None

    # Burn fee
    burn_fee_paid: float = 0.0

    # Review panel
    review_panel: Optional[ReviewPanel] = None

    # Resolution
    outcome: Optional[AppealOutcome] = None
    scr: Optional[SemanticCaseRecord] = None
    resolved_at: Optional[datetime] = None

    # Semantic lock
    semantic_lock_id: Optional[str] = None
    locked_terms: List[str] = field(default_factory=list)

    def __post_init__(self):
        if self.review_deadline is None:
            self.review_deadline = self.declared_at + timedelta(days=self.review_window_days)

    @property
    def is_expired(self) -> bool:
        """Check if review window has expired."""
        return datetime.utcnow() > self.review_deadline and self.status != AppealStatus.RESOLVED

    def apply_semantic_lock(self, lock_id: str) -> None:
        """Apply scoped semantic lock to disputed terms."""
        self.semantic_lock_id = lock_id
        self.locked_terms = self.disputed_terms.copy()
        self.status = AppealStatus.SEMANTIC_LOCK_APPLIED


@dataclass
class PrecedentEntry:
    """An entry in the precedent index."""
    scr: SemanticCaseRecord
    weight: PrecedentWeight
    canonical_term_ids: List[str] = field(default_factory=list)
    jurisdiction_context: Optional[str] = None

    @property
    def age_months(self) -> float:
        """Get age of precedent in months."""
        delta = datetime.utcnow() - self.scr.resolution_timestamp
        return delta.days / 30.0

    def compute_weight(self, current_registry_version: str) -> PrecedentWeight:
        """
        Compute precedent weight based on age and registry version.

        Per NCIP-008 Section 6.2:
        - < 3 months: High
        - 3-12 months: Medium
        - > 12 months: Low
        - Superseded term registry: Zero
        """
        # Check if registry version is superseded
        if self.scr.canonical_terms_version != current_registry_version:
            # Simple version comparison (major.minor format)
            try:
                scr_parts = [int(x) for x in self.scr.canonical_terms_version.split('.')]
                curr_parts = [int(x) for x in current_registry_version.split('.')]
                if curr_parts > scr_parts:
                    return PrecedentWeight.ZERO
            except (ValueError, AttributeError):
                pass

        age = self.age_months
        if age < 3:
            return PrecedentWeight.HIGH
        elif age < 12:
            return PrecedentWeight.MEDIUM
        else:
            return PrecedentWeight.LOW


@dataclass
class AppealCooldown:
    """Cooldown tracking for appeal abuse prevention."""
    appellant_id: str
    entry_id: str
    failed_appeals: int = 0
    last_failed_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None

    # Default cooldown after failed appeal: 30 days
    DEFAULT_COOLDOWN_DAYS = 30

    def record_failed_appeal(self) -> None:
        """Record a failed appeal and set cooldown."""
        self.failed_appeals += 1
        self.last_failed_at = datetime.utcnow()
        # Escalating cooldown
        cooldown_days = self.DEFAULT_COOLDOWN_DAYS * self.failed_appeals
        self.cooldown_until = datetime.utcnow() + timedelta(days=cooldown_days)

    @property
    def is_in_cooldown(self) -> bool:
        """Check if appellant is in cooldown period."""
        if self.cooldown_until is None:
            return False
        return datetime.utcnow() < self.cooldown_until


class AppealsManager:
    """
    Manages semantic appeals per NCIP-008.

    Responsibilities:
    - Appeal creation and lifecycle management
    - Review panel composition
    - Semantic Case Record generation
    - Precedent indexing and querying
    - Abuse prevention
    """

    # Base burn fee
    BASE_BURN_FEE = 1.0

    # Escalating fee multiplier for repeated appeals
    ESCALATING_FEE_MULTIPLIER = 2.0

    def __init__(self):
        self.appeals: Dict[str, Appeal] = {}
        self.scrs: Dict[str, SemanticCaseRecord] = {}
        self.precedent_index: Dict[str, List[PrecedentEntry]] = {}  # term_id -> precedents
        self.cooldowns: Dict[str, AppealCooldown] = {}  # (appellant_id, entry_id) -> cooldown

        self.appeal_counter: int = 0
        self.scr_counter: int = 0

        # Current canonical term registry version
        self.current_registry_version: str = "1.0"

    # -------------------------------------------------------------------------
    # Appeal Creation
    # -------------------------------------------------------------------------

    def create_appeal(
        self,
        appellant_id: str,
        appeal_type: AppealableItem,
        original_entry_id: str,
        validator_decision_id: str,
        drift_classification: DriftLevel,
        disputed_terms: List[str],
        appeal_rationale: str,
        original_prose: Optional[str] = None,
        pou_ids: Optional[List[str]] = None
    ) -> Tuple[Optional[Appeal], List[str]]:
        """
        Create a new appeal per NCIP-008 Section 3.

        Returns:
            Tuple of (Appeal or None, list of errors/warnings)
        """
        errors = []

        # Check if item is appealable
        if appeal_type not in AppealableItem:
            errors.append(f"Invalid appeal type: {appeal_type}")
            return (None, errors)

        # Check cooldown
        cooldown_key = f"{appellant_id}:{original_entry_id}"
        if cooldown_key in self.cooldowns:
            cooldown = self.cooldowns[cooldown_key]
            if cooldown.is_in_cooldown:
                errors.append(
                    f"Appellant in cooldown until {cooldown.cooldown_until.isoformat()}. "
                    f"Failed appeals on this entry: {cooldown.failed_appeals}"
                )
                return (None, errors)

        # Validate references
        if not original_entry_id:
            errors.append("Original entry ID is required")
        if not validator_decision_id:
            errors.append("Validator decision ID is required")
        if not disputed_terms:
            errors.append("At least one disputed term is required")

        if errors:
            return (None, errors)

        # Calculate burn fee
        burn_fee = self._calculate_burn_fee(appellant_id, original_entry_id)

        # Create appeal
        self.appeal_counter += 1
        appeal_id = f"APPEAL-{datetime.utcnow().strftime('%Y')}-{self.appeal_counter:04d}"

        reference = AppealReference(
            original_entry_id=original_entry_id,
            validator_decision_id=validator_decision_id,
            drift_classification=drift_classification,
            original_prose=original_prose,
            pou_ids=pou_ids or []
        )

        appeal = Appeal(
            appeal_id=appeal_id,
            appellant_id=appellant_id,
            appeal_type=appeal_type,
            reference=reference,
            disputed_terms=disputed_terms,
            appeal_rationale=appeal_rationale,
            burn_fee_paid=burn_fee
        )

        self.appeals[appeal_id] = appeal

        return (appeal, [f"Burn fee charged: {burn_fee}"])

    def _calculate_burn_fee(self, appellant_id: str, entry_id: str) -> float:
        """Calculate burn fee with escalation for repeated appeals."""
        cooldown_key = f"{appellant_id}:{entry_id}"

        if cooldown_key in self.cooldowns:
            cooldown = self.cooldowns[cooldown_key]
            # Escalating fee
            return self.BASE_BURN_FEE * (self.ESCALATING_FEE_MULTIPLIER ** cooldown.failed_appeals)

        return self.BASE_BURN_FEE

    def is_appealable(self, item_type: str) -> Tuple[bool, str]:
        """Check if an item type is appealable."""
        try:
            AppealableItem(item_type)
            return (True, f"{item_type} is appealable")
        except ValueError:
            pass

        try:
            NonAppealableItem(item_type)
            return (False, f"{item_type} is not appealable per NCIP-008 Section 3.1")
        except ValueError:
            return (False, f"Unknown item type: {item_type}")

    # -------------------------------------------------------------------------
    # Semantic Lock
    # -------------------------------------------------------------------------

    def apply_scoped_lock(
        self,
        appeal: Appeal,
        lock_id: str
    ) -> Dict[str, Any]:
        """
        Apply scoped semantic lock to disputed terms.

        Per NCIP-008 Section 9:
        - Lock applies only to disputed terms
        - Lock does not block unrelated amendments
        """
        appeal.apply_semantic_lock(lock_id)
        appeal.status = AppealStatus.SEMANTIC_LOCK_APPLIED

        return {
            "lock_id": lock_id,
            "locked_terms": appeal.locked_terms,
            "appeal_id": appeal.appeal_id,
            "status": "scoped_lock_applied"
        }

    def release_lock(self, appeal: Appeal) -> Dict[str, Any]:
        """Release semantic lock upon resolution."""
        old_lock_id = appeal.semantic_lock_id
        appeal.semantic_lock_id = None
        appeal.locked_terms = []

        return {
            "lock_id": old_lock_id,
            "appeal_id": appeal.appeal_id,
            "status": "lock_released"
        }

    # -------------------------------------------------------------------------
    # Review Panel
    # -------------------------------------------------------------------------

    def create_review_panel(
        self,
        appeal: Appeal,
        original_validator_ids: List[str]
    ) -> ReviewPanel:
        """Create a review panel for an appeal."""
        panel = ReviewPanel(original_validator_ids=set(original_validator_ids))
        appeal.review_panel = panel
        return panel

    def validate_panel(self, panel: ReviewPanel) -> Tuple[bool, List[str]]:
        """
        Validate review panel meets requirements.

        Per NCIP-008 Section 4.1:
        - N >= 3 validators
        - Distinct implementations
        - No overlap with original validators
        """
        issues = []

        if len(panel.members) < 3:
            issues.append(f"Panel has {len(panel.members)} members, needs >= 3")

        implementations = set(m.implementation_type for m in panel.members)
        if len(implementations) < 2:
            issues.append("Panel needs at least 2 distinct implementation types")

        member_ids = set(m.validator_id for m in panel.members)
        overlap = member_ids & panel.original_validator_ids
        if overlap:
            issues.append(f"Panel has overlap with original validators: {overlap}")

        return (len(issues) == 0, issues)

    def begin_review(self, appeal: Appeal) -> Tuple[bool, str]:
        """Begin the review process for an appeal."""
        if appeal.review_panel is None:
            return (False, "No review panel assigned")

        valid, issues = self.validate_panel(appeal.review_panel)
        if not valid:
            return (False, f"Invalid panel: {'; '.join(issues)}")

        appeal.status = AppealStatus.UNDER_REVIEW
        return (True, "Review process started")

    def record_vote(
        self,
        appeal: Appeal,
        validator_id: str,
        vote: AppealOutcome,
        revised_classification: Optional[DriftLevel] = None,
        rationale: str = ""
    ) -> Tuple[bool, str]:
        """Record a vote from a panel member."""
        if appeal.review_panel is None:
            return (False, "No review panel")

        # Check validator is on panel
        panel_ids = {m.validator_id for m in appeal.review_panel.members}
        if validator_id not in panel_ids:
            return (False, "Validator not on review panel")

        # Check for duplicate votes
        existing_votes = {v.validator_id for v in getattr(appeal, '_votes', [])}
        if validator_id in existing_votes:
            return (False, "Validator has already voted")

        vote_obj = AppealVote(
            validator_id=validator_id,
            vote=vote,
            revised_classification=revised_classification,
            rationale=rationale
        )

        if not hasattr(appeal, '_votes'):
            appeal._votes = []
        appeal._votes.append(vote_obj)

        # Check if all votes are in
        if len(appeal._votes) >= len(appeal.review_panel.members):
            appeal.status = AppealStatus.AWAITING_RATIFICATION

        return (True, f"Vote recorded from {validator_id}")

    # -------------------------------------------------------------------------
    # Resolution & SCR Generation
    # -------------------------------------------------------------------------

    def resolve_appeal(
        self,
        appeal: Appeal,
        outcome: AppealOutcome,
        revised_classification: Optional[DriftLevel],
        rationale_summary: str,
        human_ratifier_id: str,
        prior_cases: Optional[List[str]] = None
    ) -> Tuple[Optional[SemanticCaseRecord], List[str]]:
        """
        Resolve an appeal and generate Semantic Case Record.

        Per NCIP-008 Section 4.1: Human ratification required for outcome finalization.
        """
        errors = []

        if appeal.status not in [AppealStatus.UNDER_REVIEW, AppealStatus.AWAITING_RATIFICATION]:
            errors.append(f"Appeal cannot be resolved in status: {appeal.status.value}")
            return (None, errors)

        # Generate SCR
        self.scr_counter += 1
        case_id = f"SCR-{datetime.utcnow().strftime('%Y')}-{self.scr_counter:04d}"

        scr = SemanticCaseRecord(
            case_id=case_id,
            originating_entry=appeal.reference.original_entry_id,
            appeal_reason=appeal.appeal_type,
            disputed_terms=appeal.disputed_terms,
            outcome=outcome,
            upheld=(outcome == AppealOutcome.UPHELD),
            revised_classification=revised_classification,
            rationale_summary=rationale_summary,
            canonical_terms_version=self.current_registry_version,
            prior_cases=prior_cases or [],
            human_ratification=True,
            human_ratifier_id=human_ratifier_id,
            panel_votes=getattr(appeal, '_votes', [])
        )

        # Store SCR
        self.scrs[case_id] = scr

        # Update appeal
        appeal.status = AppealStatus.RESOLVED
        appeal.outcome = outcome
        appeal.scr = scr
        appeal.resolved_at = datetime.utcnow()

        # Release semantic lock
        self.release_lock(appeal)

        # Index for precedent
        self._index_precedent(scr)

        # Update cooldown on failure
        if outcome == AppealOutcome.UPHELD or outcome == AppealOutcome.DISMISSED:
            self._record_failed_appeal(appeal.appellant_id, appeal.reference.original_entry_id)

        return (scr, [])

    def _record_failed_appeal(self, appellant_id: str, entry_id: str) -> None:
        """Record a failed appeal for cooldown tracking."""
        cooldown_key = f"{appellant_id}:{entry_id}"

        if cooldown_key not in self.cooldowns:
            self.cooldowns[cooldown_key] = AppealCooldown(
                appellant_id=appellant_id,
                entry_id=entry_id
            )

        self.cooldowns[cooldown_key].record_failed_appeal()

    def reject_appeal(
        self,
        appeal: Appeal,
        rejection_reason: str
    ) -> Dict[str, Any]:
        """Reject an appeal (invalid/frivolous)."""
        appeal.status = AppealStatus.REJECTED
        appeal.resolved_at = datetime.utcnow()

        # Record as failed for cooldown
        self._record_failed_appeal(appeal.appellant_id, appeal.reference.original_entry_id)

        # Release any lock
        self.release_lock(appeal)

        return {
            "appeal_id": appeal.appeal_id,
            "status": "rejected",
            "reason": rejection_reason
        }

    # -------------------------------------------------------------------------
    # Precedent Indexing & Querying
    # -------------------------------------------------------------------------

    def _index_precedent(self, scr: SemanticCaseRecord) -> None:
        """Index an SCR for precedent lookup."""
        entry = PrecedentEntry(
            scr=scr,
            weight=PrecedentWeight.HIGH,  # New case is high weight
            canonical_term_ids=scr.disputed_terms.copy()
        )

        # Index by each disputed term
        for term in scr.disputed_terms:
            if term not in self.precedent_index:
                self.precedent_index[term] = []
            self.precedent_index[term].append(entry)

    def query_precedents(
        self,
        canonical_term_id: Optional[str] = None,
        drift_class: Optional[DriftLevel] = None,
        jurisdiction_context: Optional[str] = None,
        date_range: Optional[Tuple[datetime, datetime]] = None,
        include_zero_weight: bool = False
    ) -> List[PrecedentEntry]:
        """
        Query precedents per NCIP-008 Section 11.

        Lookup fields:
        - canonical_term_id
        - drift_class
        - jurisdiction_context
        - date_range
        """
        results = []

        # Get candidates
        if canonical_term_id:
            candidates = self.precedent_index.get(canonical_term_id, [])
        else:
            # All precedents
            seen = set()
            candidates = []
            for entries in self.precedent_index.values():
                for entry in entries:
                    if entry.scr.case_id not in seen:
                        seen.add(entry.scr.case_id)
                        candidates.append(entry)

        for entry in candidates:
            # Compute current weight
            weight = entry.compute_weight(self.current_registry_version)
            entry.weight = weight

            # Filter by weight
            if weight == PrecedentWeight.ZERO and not include_zero_weight:
                continue

            # Filter by drift class
            if drift_class and entry.scr.revised_classification != drift_class:
                if entry.scr.outcome != AppealOutcome.OVERTURNED:
                    continue

            # Filter by jurisdiction
            if jurisdiction_context and entry.jurisdiction_context != jurisdiction_context:
                continue

            # Filter by date range
            if date_range:
                start, end = date_range
                if not (start <= entry.scr.resolution_timestamp <= end):
                    continue

            results.append(entry)

        # Sort by weight (high first) then by date (recent first)
        weight_order = {PrecedentWeight.HIGH: 0, PrecedentWeight.MEDIUM: 1, PrecedentWeight.LOW: 2, PrecedentWeight.ZERO: 3}
        results.sort(key=lambda e: (weight_order[e.weight], -e.scr.resolution_timestamp.timestamp()))

        return results

    def get_precedent_signal(
        self,
        term_id: str,
        drift_class: DriftLevel
    ) -> Dict[str, Any]:
        """
        Get advisory precedent signal for a term and drift class.

        Per NCIP-008 Section 6.1:
        - Precedent is advisory, not binding
        - Validators may increase confidence, reduce uncertainty, flag likely interpretations
        - Validators must NOT auto-accept or reject based on precedent
        """
        precedents = self.query_precedents(canonical_term_id=term_id)

        if not precedents:
            return {
                "term_id": term_id,
                "drift_class": drift_class.value,
                "precedent_available": False,
                "advisory_only": True,
                "binding": False
            }

        # Analyze precedent patterns
        similar_outcomes = []
        for p in precedents:
            if p.scr.appeal_reason == AppealableItem.DRIFT_CLASSIFICATION:
                similar_outcomes.append({
                    "case_id": p.scr.case_id,
                    "original_drift": p.scr.disputed_terms,
                    "outcome": p.scr.outcome.value,
                    "revised": p.scr.revised_classification.value if p.scr.revised_classification else None,
                    "weight": p.weight.value,
                    "age_months": round(p.age_months, 1)
                })

        # Calculate confidence adjustment
        high_weight_count = sum(1 for p in precedents if p.weight == PrecedentWeight.HIGH)
        confidence_boost = min(0.1 * high_weight_count, 0.3)  # Max 30% boost

        return {
            "term_id": term_id,
            "drift_class": drift_class.value,
            "precedent_available": True,
            "precedent_count": len(precedents),
            "similar_outcomes": similar_outcomes[:5],  # Top 5
            "confidence_adjustment": confidence_boost,
            "advisory_only": True,
            "binding": False,
            "warning": "Precedent is advisory signal only. Explicit prose takes priority."
        }

    # -------------------------------------------------------------------------
    # SCR Index Generation
    # -------------------------------------------------------------------------

    def generate_scr_index(self) -> Dict[str, Any]:
        """
        Generate machine-readable SCR index per NCIP-008 Section 11.
        """
        return {
            "semantic_precedent_index": {
                "version": "1.0",
                "lookup_fields": [
                    "canonical_term_id",
                    "drift_class",
                    "jurisdiction_context",
                    "date_range"
                ],
                "advisory_only": True,
                "binding": False,
                "total_records": len(self.scrs),
                "registry_version": self.current_registry_version,
                "weight_decay": {
                    "high": "< 3 months",
                    "medium": "3-12 months",
                    "low": "> 12 months",
                    "zero": "superseded registry"
                }
            }
        }

    # -------------------------------------------------------------------------
    # Validator Behavior Checks
    # -------------------------------------------------------------------------

    def check_precedent_divergence(
        self,
        term_id: str,
        proposed_classification: DriftLevel
    ) -> Optional[str]:
        """
        Check if proposed classification diverges from strong precedent.

        Per NCIP-008 Section 7: Validators MUST emit warnings when
        diverging from strong precedent.
        """
        precedents = self.query_precedents(canonical_term_id=term_id)

        high_weight = [p for p in precedents if p.weight == PrecedentWeight.HIGH]
        if not high_weight:
            return None

        # Check if any high-weight precedent has different classification
        for p in high_weight:
            if p.scr.revised_classification and p.scr.revised_classification != proposed_classification:
                return (
                    f"Warning: Proposed classification {proposed_classification.value} diverges from "
                    f"strong precedent {p.scr.case_id} (revised to {p.scr.revised_classification.value}, "
                    f"weight: {p.weight.value}). Per NCIP-008, explicit prose takes priority."
                )

        return None

    # -------------------------------------------------------------------------
    # Status & Reporting
    # -------------------------------------------------------------------------

    def get_appeal(self, appeal_id: str) -> Optional[Appeal]:
        """Get an appeal by ID."""
        return self.appeals.get(appeal_id)

    def get_scr(self, case_id: str) -> Optional[SemanticCaseRecord]:
        """Get an SCR by ID."""
        return self.scrs.get(case_id)

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of appeals system status."""
        status_counts = {}
        for appeal in self.appeals.values():
            status = appeal.status.value
            status_counts[status] = status_counts.get(status, 0) + 1

        weight_counts = {}
        for entries in self.precedent_index.values():
            for entry in entries:
                weight = entry.compute_weight(self.current_registry_version)
                weight_counts[weight.value] = weight_counts.get(weight.value, 0) + 1

        return {
            "total_appeals": len(self.appeals),
            "appeal_status_counts": status_counts,
            "total_scrs": len(self.scrs),
            "precedent_index_size": len(self.precedent_index),
            "precedent_weight_distribution": weight_counts,
            "current_registry_version": self.current_registry_version,
            "active_cooldowns": sum(1 for c in self.cooldowns.values() if c.is_in_cooldown),
            "principle": "Past meaning may inform future interpretation — but never replace explicit present intent."
        }

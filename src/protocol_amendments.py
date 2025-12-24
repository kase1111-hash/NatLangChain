"""
NCIP-014: Protocol Amendments & Constitutional Change

This module implements the constitutional amendment process for NatLangChain,
ensuring changes are explicit, slow, human-ratified, non-coercive, and forward-only.

Core Principle: Past meaning is inviolable. Future meaning is negotiable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib
import json


class AmendmentClass(Enum):
    """
    Amendment classes with increasing severity and threshold requirements.

    Per NCIP-014 Section 4:
    - A: Editorial/Clarificatory - Simple majority
    - B: Procedural - Supermajority
    - C: Semantic - Constitutional quorum
    - D: Structural - Near-unanimous
    - E: Existential - Fork-only
    """
    A = "editorial"        # Wording clarity, examples
    B = "procedural"       # Validator behavior, thresholds
    C = "semantic"         # Term definitions, protocol meaning
    D = "structural"       # Governance model, authority boundaries
    E = "existential"      # Core principles, refusal doctrine


class AmendmentStatus(Enum):
    """Status of an amendment through the ratification process."""
    DRAFT = "draft"
    PROPOSED = "proposed"
    COOLING = "cooling"
    DELIBERATION = "deliberation"
    VOTING = "voting"
    RATIFIED = "ratified"
    ACTIVATED = "activated"
    REJECTED = "rejected"
    EXPIRED = "expired"
    VOID = "void"  # Constitutional violation


class RatificationStage(Enum):
    """
    Stages of the ratification process per NCIP-014 Section 7.1.
    No stage may be skipped.
    """
    PROPOSAL_POSTING = 1
    COOLING_PERIOD = 2
    DELIBERATION_WINDOW = 3
    HUMAN_RATIFICATION = 4
    SEMANTIC_LOCK = 5
    FUTURE_ACTIVATION = 6


class ConstitutionalArtifact(Enum):
    """Constitutional artifacts subject to NCIP-014 governance."""
    GENESIS_BLOCK = "genesis_block"
    CORE_DOCTRINES = "core_doctrines"
    MP_01 = "mp_01"
    MP_02 = "mp_02"
    MP_03 = "mp_03"
    MP_04 = "mp_04"
    MP_05 = "mp_05"
    NCIP_001 = "ncip_001"
    NCIP_002 = "ncip_002"
    NCIP_003 = "ncip_003"
    NCIP_004 = "ncip_004"
    NCIP_005 = "ncip_005"
    NCIP_006 = "ncip_006"
    NCIP_007 = "ncip_007"
    NCIP_008 = "ncip_008"
    NCIP_009 = "ncip_009"
    NCIP_010 = "ncip_010"
    NCIP_011 = "ncip_011"
    NCIP_012 = "ncip_012"
    NCIP_013 = "ncip_013"
    NCIP_014 = "ncip_014"
    NCIP_015 = "ncip_015"
    CANONICAL_TERM_REGISTRY = "canonical_term_registry"


class ProhibitedAction(Enum):
    """Actions that are constitutionally prohibited per NCIP-014 Section 13."""
    RETROACTIVE_REINTERPRETATION = "retroactive_reinterpretation"
    POU_INVALIDATION = "pou_invalidation"
    SEMANTIC_LOCK_OVERRIDE = "semantic_lock_override"
    NON_HUMAN_SEMANTIC_AUTHORITY = "non_human_semantic_authority"
    REFUSAL_DOCTRINE_COLLAPSE = "refusal_doctrine_collapse"


@dataclass
class VoteRecord:
    """Record of a single vote on an amendment."""
    voter_id: str
    vote: str  # "approve", "reject", "abstain"
    pou_statement: str  # Required PoU per NCIP-014 Section 6
    pou_hash: str
    weight: float = 1.0
    validator_trust_score: Optional[float] = None
    mediator_reputation: Optional[float] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)

    @property
    def has_valid_pou(self) -> bool:
        """Check if vote has required PoU."""
        return bool(self.pou_statement and len(self.pou_statement) >= 50)


@dataclass
class PoUStatement:
    """
    Proof of Understanding statement required for amendment voting.
    Per NCIP-014 Section 6.1, must state:
    - What changes
    - What does not change
    - Who is affected
    - Why they agree or disagree
    """
    voter_id: str
    what_changes: str
    what_unchanged: str
    who_affected: str
    rationale: str  # Why agree/disagree
    timestamp: datetime = field(default_factory=datetime.utcnow)

    def to_statement(self) -> str:
        """Convert to full statement text."""
        return (
            f"WHAT CHANGES: {self.what_changes}\n"
            f"WHAT UNCHANGED: {self.what_unchanged}\n"
            f"WHO AFFECTED: {self.who_affected}\n"
            f"RATIONALE: {self.rationale}"
        )

    def compute_hash(self) -> str:
        """Compute hash of the PoU statement."""
        content = self.to_statement()
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class SemanticCompatibilityResult:
    """Result of semantic compatibility check for an amendment."""
    is_compatible: bool
    drift_scores: Dict[str, float] = field(default_factory=dict)
    max_drift: float = 0.0
    affected_ncips: List[str] = field(default_factory=list)
    cross_language_impacts: List[str] = field(default_factory=list)
    requires_migration: bool = False
    migration_guidance: Optional[str] = None
    violations: List[str] = field(default_factory=list)


@dataclass
class Amendment:
    """
    A constitutional amendment proposal.
    Per NCIP-014 Section 5, must include required fields.
    """
    amendment_id: str
    amendment_class: AmendmentClass
    title: str
    rationale: str
    scope_of_impact: str
    affected_artifacts: List[ConstitutionalArtifact]
    proposed_changes: str
    migration_guidance: Optional[str] = None
    effective_date: Optional[datetime] = None
    status: AmendmentStatus = AmendmentStatus.DRAFT
    current_stage: RatificationStage = RatificationStage.PROPOSAL_POSTING
    retroactive: bool = False  # MUST be False per NCIP-014
    supersedes: List[str] = field(default_factory=list)
    fork_required: bool = False

    # Timeline tracking
    proposed_at: Optional[datetime] = None
    cooling_ends_at: Optional[datetime] = None
    deliberation_ends_at: Optional[datetime] = None
    ratified_at: Optional[datetime] = None
    semantic_lock_at: Optional[datetime] = None
    activated_at: Optional[datetime] = None

    # Voting
    votes: List[VoteRecord] = field(default_factory=list)
    vote_tally: Dict[str, float] = field(default_factory=dict)

    # Compatibility
    compatibility_result: Optional[SemanticCompatibilityResult] = None

    # Constitutional version
    constitution_version_before: str = ""
    constitution_version_after: str = ""

    def __post_init__(self):
        # Validate non-retroactivity
        if self.retroactive:
            raise ValueError("Amendments MUST NOT be retroactive per NCIP-014")

        # Class E requires fork
        if self.amendment_class == AmendmentClass.E:
            self.fork_required = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "amendment_id": self.amendment_id,
            "class": self.amendment_class.value,
            "title": self.title,
            "rationale": self.rationale,
            "scope_of_impact": self.scope_of_impact,
            "affected_artifacts": [a.value for a in self.affected_artifacts],
            "proposed_changes": self.proposed_changes,
            "migration_guidance": self.migration_guidance,
            "effective_date": self.effective_date.isoformat() if self.effective_date else None,
            "status": self.status.value,
            "current_stage": self.current_stage.name,
            "retroactive": self.retroactive,
            "supersedes": self.supersedes,
            "fork_required": self.fork_required,
            "proposed_at": self.proposed_at.isoformat() if self.proposed_at else None,
            "ratified_at": self.ratified_at.isoformat() if self.ratified_at else None,
            "activated_at": self.activated_at.isoformat() if self.activated_at else None,
        }


@dataclass
class EmergencyAmendment:
    """
    Emergency amendment with restricted scope per NCIP-014 Section 12.

    Constraints:
    - Limited to procedural safety
    - Time-bounded
    - Auto-expire unless ratified
    - MUST NOT alter semantics
    """
    amendment_id: str
    reason: str  # validator_halt, exploit_mitigation, network_safety_pause
    proposed_changes: str
    proposed_at: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    max_duration: timedelta = field(default_factory=lambda: timedelta(days=7))
    is_semantic: bool = False  # MUST be False
    ratified: bool = False
    expired: bool = False

    def __post_init__(self):
        if self.is_semantic:
            raise ValueError("Emergency amendments MUST NOT alter semantics")
        if self.expires_at is None:
            self.expires_at = self.proposed_at + self.max_duration

    @property
    def is_active(self) -> bool:
        """Check if emergency amendment is currently active."""
        if self.expired:
            return False
        return datetime.utcnow() < self.expires_at

    def check_expiry(self) -> bool:
        """Check and update expiry status."""
        if not self.ratified and datetime.utcnow() >= self.expires_at:
            self.expired = True
        return self.expired


@dataclass
class ConstitutionVersion:
    """Tracks constitution version for entries."""
    version: str
    effective_from: datetime
    amendments_included: List[str] = field(default_factory=list)
    previous_version: Optional[str] = None

    def increment(self, amendment_id: str) -> "ConstitutionVersion":
        """Create next version after amendment."""
        parts = self.version.split(".")
        major = int(parts[0])
        minor = int(parts[1]) if len(parts) > 1 else 0

        return ConstitutionVersion(
            version=f"{major}.{minor + 1}",
            effective_from=datetime.utcnow(),
            amendments_included=[amendment_id],
            previous_version=self.version
        )


class AmendmentManager:
    """
    Manages the constitutional amendment process per NCIP-014.

    Ensures:
    - Proper staging (no skipped stages)
    - Threshold enforcement
    - PoU requirements
    - Semantic compatibility
    - Non-retroactivity
    - Constitution versioning
    """

    # Voting thresholds by class
    THRESHOLDS = {
        AmendmentClass.A: 0.50,    # Simple majority (>50%)
        AmendmentClass.B: 0.67,    # Supermajority (>67%)
        AmendmentClass.C: 0.75,    # Constitutional quorum (>75%)
        AmendmentClass.D: 0.90,    # Near-unanimous (>90%)
        AmendmentClass.E: 1.00,    # Fork-only (100% or fork)
    }

    # Minimum cooling period (days)
    MIN_COOLING_PERIOD = timedelta(days=14)

    # Deliberation windows by class
    DELIBERATION_WINDOWS = {
        AmendmentClass.A: timedelta(days=7),
        AmendmentClass.B: timedelta(days=14),
        AmendmentClass.C: timedelta(days=21),
        AmendmentClass.D: timedelta(days=30),
        AmendmentClass.E: timedelta(days=60),
    }

    # Maximum drift allowed without migration
    MAX_DRIFT_WITHOUT_MIGRATION = 0.45  # D3 threshold

    def __init__(self):
        self.amendments: Dict[str, Amendment] = {}
        self.emergency_amendments: Dict[str, EmergencyAmendment] = {}
        self.current_constitution = ConstitutionVersion(
            version="3.0",
            effective_from=datetime.utcnow()
        )
        self.constitution_history: List[ConstitutionVersion] = [self.current_constitution]
        self.fork_registry: Dict[str, str] = {}  # fork_id -> constitution_version

    # -------------------------------------------------------------------------
    # Amendment Creation
    # -------------------------------------------------------------------------

    def create_amendment(
        self,
        amendment_id: str,
        amendment_class: AmendmentClass,
        title: str,
        rationale: str,
        scope_of_impact: str,
        affected_artifacts: List[ConstitutionalArtifact],
        proposed_changes: str,
        migration_guidance: Optional[str] = None,
        effective_date: Optional[datetime] = None
    ) -> Tuple[Amendment, List[str]]:
        """
        Create a new amendment proposal.

        Returns (amendment, validation_errors).
        """
        errors = []

        # Validate amendment ID format
        if not amendment_id.startswith("NCIP-014-"):
            errors.append("Amendment ID must start with 'NCIP-014-'")

        # Validate required fields
        if not rationale or len(rationale) < 50:
            errors.append("Rationale must be at least 50 characters")

        if not scope_of_impact or len(scope_of_impact) < 30:
            errors.append("Scope of impact must be at least 30 characters")

        if not affected_artifacts:
            errors.append("Must specify at least one affected artifact")

        if not proposed_changes or len(proposed_changes) < 50:
            errors.append("Proposed changes must be at least 50 characters")

        # Class D/E require migration guidance
        if amendment_class in [AmendmentClass.D, AmendmentClass.E]:
            if not migration_guidance:
                errors.append(f"Class {amendment_class.name} amendments require migration guidance")

        # Effective date must be in future
        if effective_date and effective_date <= datetime.utcnow():
            errors.append("Effective date must be in the future")

        if errors:
            return None, errors

        amendment = Amendment(
            amendment_id=amendment_id,
            amendment_class=amendment_class,
            title=title,
            rationale=rationale,
            scope_of_impact=scope_of_impact,
            affected_artifacts=affected_artifacts,
            proposed_changes=proposed_changes,
            migration_guidance=migration_guidance,
            effective_date=effective_date,
            constitution_version_before=self.current_constitution.version
        )

        self.amendments[amendment_id] = amendment
        return amendment, []

    def generate_amendment_id(
        self,
        amendment_class: AmendmentClass,
        year: Optional[int] = None
    ) -> str:
        """Generate a unique amendment ID."""
        year = year or datetime.utcnow().year

        # Count existing amendments of this class this year
        prefix = f"NCIP-014-{amendment_class.name}-{year}-"
        count = sum(1 for aid in self.amendments if aid.startswith(prefix))

        return f"{prefix}{count + 1:03d}"

    # -------------------------------------------------------------------------
    # Ratification Process
    # -------------------------------------------------------------------------

    def propose_amendment(self, amendment_id: str) -> Tuple[bool, str]:
        """
        Move amendment to proposed status and start cooling period.
        Stage 1 -> Stage 2.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.status != AmendmentStatus.DRAFT:
            return (False, f"Amendment must be in DRAFT status, is {amendment.status.value}")

        now = datetime.utcnow()
        amendment.status = AmendmentStatus.PROPOSED
        amendment.proposed_at = now
        amendment.current_stage = RatificationStage.COOLING_PERIOD
        amendment.cooling_ends_at = now + self.MIN_COOLING_PERIOD

        return (True, f"Amendment proposed. Cooling period ends at {amendment.cooling_ends_at}")

    def start_deliberation(self, amendment_id: str) -> Tuple[bool, str]:
        """
        Move from cooling to deliberation period.
        Stage 2 -> Stage 3.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.current_stage != RatificationStage.COOLING_PERIOD:
            return (False, "Must be in COOLING_PERIOD stage")

        now = datetime.utcnow()
        if now < amendment.cooling_ends_at:
            remaining = amendment.cooling_ends_at - now
            return (False, f"Cooling period not complete. {remaining} remaining")

        window = self.DELIBERATION_WINDOWS[amendment.amendment_class]
        amendment.status = AmendmentStatus.DELIBERATION
        amendment.current_stage = RatificationStage.DELIBERATION_WINDOW
        amendment.deliberation_ends_at = now + window

        return (True, f"Deliberation started. Window ends at {amendment.deliberation_ends_at}")

    def start_voting(self, amendment_id: str) -> Tuple[bool, str]:
        """
        Move from deliberation to voting.
        Stage 3 -> Stage 4.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.current_stage != RatificationStage.DELIBERATION_WINDOW:
            return (False, "Must be in DELIBERATION_WINDOW stage")

        now = datetime.utcnow()
        if now < amendment.deliberation_ends_at:
            remaining = amendment.deliberation_ends_at - now
            return (False, f"Deliberation not complete. {remaining} remaining")

        # Check semantic compatibility before voting
        if not amendment.compatibility_result:
            return (False, "Semantic compatibility check required before voting")

        if not amendment.compatibility_result.is_compatible:
            return (False, f"Amendment failed compatibility: {amendment.compatibility_result.violations}")

        amendment.status = AmendmentStatus.VOTING
        amendment.current_stage = RatificationStage.HUMAN_RATIFICATION

        return (True, "Voting period started")

    def cast_vote(
        self,
        amendment_id: str,
        voter_id: str,
        vote: str,
        pou: PoUStatement,
        weight: float = 1.0,
        validator_trust_score: Optional[float] = None,
        mediator_reputation: Optional[float] = None
    ) -> Tuple[bool, str]:
        """
        Cast a vote on an amendment. Requires valid PoU.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.status != AmendmentStatus.VOTING:
            return (False, "Amendment is not in voting stage")

        if vote not in ["approve", "reject", "abstain"]:
            return (False, "Vote must be 'approve', 'reject', or 'abstain'")

        # Validate PoU
        pou_statement = pou.to_statement()
        if len(pou_statement) < 100:
            return (False, "PoU statement too short. Must explain what changes, what doesn't, who affected, and why")

        if not pou.what_changes or not pou.what_unchanged:
            return (False, "PoU must specify both what changes and what remains unchanged")

        if not pou.who_affected:
            return (False, "PoU must specify who is affected")

        if not pou.rationale:
            return (False, "PoU must include rationale for vote")

        # Check for duplicate votes
        if any(v.voter_id == voter_id for v in amendment.votes):
            return (False, "Voter has already cast a vote")

        # Calculate effective weight
        effective_weight = weight
        if validator_trust_score is not None:
            effective_weight *= validator_trust_score
        if mediator_reputation is not None:
            effective_weight *= mediator_reputation

        vote_record = VoteRecord(
            voter_id=voter_id,
            vote=vote,
            pou_statement=pou_statement,
            pou_hash=pou.compute_hash(),
            weight=effective_weight,
            validator_trust_score=validator_trust_score,
            mediator_reputation=mediator_reputation
        )

        amendment.votes.append(vote_record)

        return (True, f"Vote recorded with weight {effective_weight:.2f}")

    def tally_votes(self, amendment_id: str) -> Dict[str, Any]:
        """Tally votes for an amendment."""
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return {"error": f"Amendment {amendment_id} not found"}

        approve_weight = sum(v.weight for v in amendment.votes if v.vote == "approve")
        reject_weight = sum(v.weight for v in amendment.votes if v.vote == "reject")
        abstain_weight = sum(v.weight for v in amendment.votes if v.vote == "abstain")
        total_weight = approve_weight + reject_weight + abstain_weight

        if total_weight == 0:
            approval_ratio = 0.0
        else:
            # Abstentions don't count against approval
            voting_weight = approve_weight + reject_weight
            approval_ratio = approve_weight / voting_weight if voting_weight > 0 else 0.0

        threshold = self.THRESHOLDS[amendment.amendment_class]

        amendment.vote_tally = {
            "approve": approve_weight,
            "reject": reject_weight,
            "abstain": abstain_weight,
            "total": total_weight,
            "approval_ratio": approval_ratio,
            "threshold": threshold,
            "meets_threshold": approval_ratio >= threshold
        }

        return amendment.vote_tally

    def finalize_ratification(self, amendment_id: str) -> Tuple[bool, str]:
        """
        Finalize ratification based on vote tally.
        Stage 4 -> Stage 5 (if approved) or REJECTED.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.status != AmendmentStatus.VOTING:
            return (False, "Amendment must be in VOTING status")

        tally = self.tally_votes(amendment_id)
        if "error" in tally:
            return (False, tally["error"])

        # Check if class E (fork required)
        if amendment.amendment_class == AmendmentClass.E:
            if not tally["meets_threshold"]:
                # Fork is constitutional right
                fork_id = self._create_fork(amendment_id)
                return (True, f"Consensus failed. Fork created: {fork_id}")

        if not tally["meets_threshold"]:
            amendment.status = AmendmentStatus.REJECTED
            return (False, f"Amendment rejected. Approval {tally['approval_ratio']:.1%} < threshold {tally['threshold']:.1%}")

        # Approved - apply semantic lock
        now = datetime.utcnow()
        amendment.status = AmendmentStatus.RATIFIED
        amendment.ratified_at = now
        amendment.semantic_lock_at = now
        amendment.current_stage = RatificationStage.SEMANTIC_LOCK

        return (True, f"Amendment ratified. Semantic lock applied at {now}")

    def activate_amendment(self, amendment_id: str) -> Tuple[bool, str]:
        """
        Activate a ratified amendment at or after effective_date.
        Stage 5 -> Stage 6.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.status != AmendmentStatus.RATIFIED:
            return (False, "Amendment must be RATIFIED before activation")

        now = datetime.utcnow()

        # Check effective date
        if amendment.effective_date and now < amendment.effective_date:
            return (False, f"Cannot activate before effective date {amendment.effective_date}")

        # Update constitution version
        new_version = self.current_constitution.increment(amendment_id)
        amendment.constitution_version_after = new_version.version

        self.current_constitution = new_version
        self.constitution_history.append(new_version)

        amendment.status = AmendmentStatus.ACTIVATED
        amendment.activated_at = now
        amendment.current_stage = RatificationStage.FUTURE_ACTIVATION

        return (True, f"Amendment activated. Constitution now v{new_version.version}")

    def _create_fork(self, amendment_id: str) -> str:
        """Create a constitutional fork when consensus fails on Class E."""
        fork_id = f"fork_{amendment_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        self.fork_registry[fork_id] = self.current_constitution.version
        return fork_id

    # -------------------------------------------------------------------------
    # Semantic Compatibility
    # -------------------------------------------------------------------------

    def check_semantic_compatibility(
        self,
        amendment_id: str,
        drift_scores: Optional[Dict[str, float]] = None
    ) -> SemanticCompatibilityResult:
        """
        Check semantic compatibility of an amendment.
        Per NCIP-014 Section 9, D3+ drift without migration is invalid.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return SemanticCompatibilityResult(
                is_compatible=False,
                violations=["Amendment not found"]
            )

        violations = []
        drift_scores = drift_scores or {}
        max_drift = max(drift_scores.values()) if drift_scores else 0.0

        # Check drift threshold
        if max_drift >= self.MAX_DRIFT_WITHOUT_MIGRATION:
            if not amendment.migration_guidance:
                violations.append(
                    f"Drift {max_drift:.2f} >= D3 threshold requires migration guidance"
                )

        # Check affected NCIPs for dependencies
        affected_ncips = [
            a.value for a in amendment.affected_artifacts
            if a.value.startswith("ncip_")
        ]

        # Check for prohibited actions
        if self._contains_prohibited_action(amendment):
            violations.append("Amendment contains prohibited constitutional action")

        result = SemanticCompatibilityResult(
            is_compatible=len(violations) == 0,
            drift_scores=drift_scores,
            max_drift=max_drift,
            affected_ncips=affected_ncips,
            requires_migration=max_drift >= self.MAX_DRIFT_WITHOUT_MIGRATION,
            migration_guidance=amendment.migration_guidance,
            violations=violations
        )

        amendment.compatibility_result = result
        return result

    def _contains_prohibited_action(self, amendment: Amendment) -> bool:
        """Check if amendment contains prohibited actions."""
        prohibited_keywords = [
            "retroactive",
            "reinterpret prior",
            "invalidate pou",
            "override semantic lock",
            "grant semantic authority to ai",
            "collapse refusal doctrine"
        ]

        content = (amendment.proposed_changes + " " + amendment.rationale).lower()

        for keyword in prohibited_keywords:
            if keyword in content:
                return True

        return False

    # -------------------------------------------------------------------------
    # Emergency Amendments
    # -------------------------------------------------------------------------

    def create_emergency_amendment(
        self,
        amendment_id: str,
        reason: str,
        proposed_changes: str,
        max_duration_days: int = 7
    ) -> Tuple[EmergencyAmendment, List[str]]:
        """
        Create an emergency amendment with restricted scope.
        Per NCIP-014 Section 12.
        """
        errors = []

        # Validate reason
        valid_reasons = ["validator_halt", "exploit_mitigation", "network_safety_pause"]
        if reason not in valid_reasons:
            errors.append(f"Invalid emergency reason. Must be one of: {valid_reasons}")

        # Check for semantic changes (prohibited)
        semantic_keywords = ["definition", "meaning", "interpret", "semantic"]
        if any(kw in proposed_changes.lower() for kw in semantic_keywords):
            errors.append("Emergency amendments MUST NOT alter semantics")

        if errors:
            return None, errors

        emergency = EmergencyAmendment(
            amendment_id=amendment_id,
            reason=reason,
            proposed_changes=proposed_changes,
            max_duration=timedelta(days=max_duration_days)
        )

        self.emergency_amendments[amendment_id] = emergency
        return emergency, []

    def ratify_emergency_amendment(self, amendment_id: str) -> Tuple[bool, str]:
        """Ratify an emergency amendment to prevent auto-expiry."""
        emergency = self.emergency_amendments.get(amendment_id)
        if not emergency:
            return (False, f"Emergency amendment {amendment_id} not found")

        if emergency.expired:
            return (False, "Emergency amendment has expired")

        emergency.ratified = True
        return (True, "Emergency amendment ratified")

    def check_emergency_expirations(self) -> List[str]:
        """Check and expire unratified emergency amendments."""
        expired = []
        for aid, emergency in self.emergency_amendments.items():
            if emergency.check_expiry():
                expired.append(aid)
        return expired

    # -------------------------------------------------------------------------
    # Constitution Versioning
    # -------------------------------------------------------------------------

    def get_constitution_version(self) -> str:
        """Get current constitution version."""
        return self.current_constitution.version

    def get_version_at_time(self, timestamp: datetime) -> Optional[str]:
        """Get constitution version that was active at a given time."""
        for version in reversed(self.constitution_history):
            if version.effective_from <= timestamp:
                return version.version
        return None

    def get_entry_constitution_version(self, entry_timestamp: datetime) -> str:
        """Get constitution version to bind to an entry."""
        version = self.get_version_at_time(entry_timestamp)
        return version or self.current_constitution.version

    # -------------------------------------------------------------------------
    # Query Methods
    # -------------------------------------------------------------------------

    def get_amendment(self, amendment_id: str) -> Optional[Amendment]:
        """Get an amendment by ID."""
        return self.amendments.get(amendment_id)

    def get_amendments_by_status(self, status: AmendmentStatus) -> List[Amendment]:
        """Get all amendments with a given status."""
        return [a for a in self.amendments.values() if a.status == status]

    def get_pending_amendments(self) -> List[Amendment]:
        """Get all amendments not yet activated or rejected."""
        active_statuses = [
            AmendmentStatus.DRAFT,
            AmendmentStatus.PROPOSED,
            AmendmentStatus.COOLING,
            AmendmentStatus.DELIBERATION,
            AmendmentStatus.VOTING,
            AmendmentStatus.RATIFIED
        ]
        return [a for a in self.amendments.values() if a.status in active_statuses]

    def get_activated_amendments(self) -> List[Amendment]:
        """Get all activated amendments."""
        return self.get_amendments_by_status(AmendmentStatus.ACTIVATED)

    def get_forks(self) -> Dict[str, str]:
        """Get all constitutional forks."""
        return self.fork_registry.copy()

    # -------------------------------------------------------------------------
    # Validation
    # -------------------------------------------------------------------------

    def validate_amendment_proposal(
        self,
        amendment: Amendment
    ) -> Tuple[bool, List[str]]:
        """
        Validate an amendment proposal meets all requirements.
        """
        errors = []

        # Non-retroactivity
        if amendment.retroactive:
            errors.append("CONSTITUTIONAL VIOLATION: Amendments cannot be retroactive")

        # Required fields
        if not amendment.rationale:
            errors.append("Missing required field: rationale")

        if not amendment.scope_of_impact:
            errors.append("Missing required field: scope_of_impact")

        if not amendment.affected_artifacts:
            errors.append("Must specify affected artifacts")

        if not amendment.proposed_changes:
            errors.append("Missing required field: proposed_changes")

        # Class-specific requirements
        if amendment.amendment_class in [AmendmentClass.D, AmendmentClass.E]:
            if not amendment.migration_guidance:
                errors.append(f"Class {amendment.amendment_class.name} requires migration guidance")

        # Check for prohibited content
        if self._contains_prohibited_action(amendment):
            errors.append("CONSTITUTIONAL VIOLATION: Contains prohibited action")

        return (len(errors) == 0, errors)

    def void_amendment(self, amendment_id: str, reason: str) -> Tuple[bool, str]:
        """
        Void an amendment for constitutional violations.
        """
        amendment = self.amendments.get(amendment_id)
        if not amendment:
            return (False, f"Amendment {amendment_id} not found")

        if amendment.status == AmendmentStatus.ACTIVATED:
            return (False, "Cannot void activated amendments")

        amendment.status = AmendmentStatus.VOID
        return (True, f"Amendment voided: {reason}")

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of amendment system status."""
        return {
            "constitution_version": self.current_constitution.version,
            "total_amendments": len(self.amendments),
            "by_status": {
                status.value: len(self.get_amendments_by_status(status))
                for status in AmendmentStatus
            },
            "by_class": {
                cls.value: len([a for a in self.amendments.values() if a.amendment_class == cls])
                for cls in AmendmentClass
            },
            "active_emergencies": len([e for e in self.emergency_amendments.values() if e.is_active]),
            "forks": len(self.fork_registry),
            "thresholds": {cls.name: f"{thresh:.0%}" for cls, thresh in self.THRESHOLDS.items()}
        }

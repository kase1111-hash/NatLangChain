"""
NCIP-011: Validator–Mediator Interaction & Weight Coupling

This module implements the coupling between validator authority and mediator
influence while preserving:
- Role separation (validators measure meaning, mediators surface alignment)
- Orthogonal authority (neither may substitute for the other)
- Plural, contextual, earned power
- Collusion resistance

Core Principle: Validators measure meaning. Mediators surface alignment.
Neither may substitute for the other. Authority is orthogonal, not hierarchical.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple, Any
import hashlib


class ActorRole(Enum):
    """Roles per NCIP-011 Section 3."""
    VALIDATOR = "validator"
    MEDIATOR = "mediator"
    HUMAN = "human"


class ProtocolViolationType(Enum):
    """Protocol violation types."""
    PV_V3_ROLE_CROSSING = "PV-V3"  # Crossing roles
    PV_V3_VALIDATOR_PROPOSING = "PV-V3-validator-proposing"
    PV_V3_MEDIATOR_VALIDATING = "PV-V3-mediator-validating"
    PV_V3_HUMAN_DELEGATING = "PV-V3-human-delegating"


class ValidatorAction(Enum):
    """Actions validators MAY do per NCIP-011 Section 3."""
    ASSESS_SEMANTIC_VALIDITY = "assess_semantic_validity"
    ASSESS_DRIFT = "assess_drift"
    ASSESS_POU_QUALITY = "assess_pou_quality"
    REVIEW_APPEAL = "review_appeal"
    RECOMMEND_LOCK = "recommend_lock"
    RECOMMEND_UNLOCK = "recommend_unlock"


class ValidatorProhibitedAction(Enum):
    """Actions validators may NOT do per NCIP-011 Section 3."""
    PROPOSE_TERMS = "propose_terms"
    NEGOTIATE_OUTCOMES = "negotiate_outcomes"
    RANK_PROPOSALS = "rank_proposals"
    SUPPRESS_COMPLIANT_PROPOSALS = "suppress_compliant_proposals"


class MediatorAction(Enum):
    """Actions mediators MAY do per NCIP-011 Section 3."""
    PROPOSE_ALIGNMENTS = "propose_alignments"
    PROPOSE_SETTLEMENTS = "propose_settlements"


class MediatorProhibitedAction(Enum):
    """Actions mediators may NOT do per NCIP-011 Section 3."""
    VALIDATE_SEMANTICS = "validate_semantics"
    OVERRIDE_DRIFT_RULINGS = "override_drift_rulings"
    GAME_VALIDATION = "game_validation"


class DisputePhase(Enum):
    """Dispute phases affecting weight interactions."""
    NONE = "none"
    ACTIVE = "active"          # During dispute
    POST_RESOLUTION = "post_resolution"


class WeightUpdateStatus(Enum):
    """Status of weight updates."""
    PENDING = "pending"        # In delay period
    APPLIED = "applied"        # Applied to ledger
    RETROACTIVE = "retroactive"  # Retroactively adjusted


@dataclass
class ValidatorWeight:
    """
    Validator Weight (VW) per NCIP-011 Section 4.1.

    Derived from NCIP-007:
    - Historical accuracy
    - Drift detection precision
    - PoU consistency
    - Appeal survival rate
    """
    validator_id: str
    historical_accuracy: float = 0.5
    drift_precision: float = 0.5
    pou_consistency: float = 0.5
    appeal_survival_rate: float = 0.5

    # Computed overall weight
    _weight: Optional[float] = None

    @property
    def weight(self) -> float:
        """Compute overall validator weight."""
        if self._weight is not None:
            return self._weight
        # Equal weighting of components
        self._weight = (
            self.historical_accuracy * 0.25 +
            self.drift_precision * 0.25 +
            self.pou_consistency * 0.25 +
            self.appeal_survival_rate * 0.25
        )
        return self._weight

    def invalidate_cache(self):
        """Invalidate cached weight."""
        self._weight = None


@dataclass
class MediatorWeight:
    """
    Mediator Weight (MW) per NCIP-011 Section 4.2.

    Derived from NCIP-010:
    - Acceptance rate of proposals
    - Settlement completion
    - Post-settlement dispute frequency
    - Time-to-alignment efficiency
    """
    mediator_id: str
    acceptance_rate: float = 0.5
    settlement_completion: float = 0.5
    post_settlement_dispute_frequency: float = 0.5  # Lower is better
    time_efficiency: float = 0.5

    # Computed overall weight
    _weight: Optional[float] = None

    @property
    def weight(self) -> float:
        """Compute overall mediator weight."""
        if self._weight is not None:
            return self._weight
        # Post-settlement dispute frequency is inverted (lower is better)
        dispute_score = 1.0 - self.post_settlement_dispute_frequency
        self._weight = (
            self.acceptance_rate * 0.25 +
            self.settlement_completion * 0.25 +
            dispute_score * 0.25 +
            self.time_efficiency * 0.25
        )
        return self._weight

    def invalidate_cache(self):
        """Invalidate cached weight."""
        self._weight = None


@dataclass
class SemanticConsistencyScore:
    """
    Semantic consistency scoring per NCIP-011 Section 6.

    Components:
    - Intent alignment score
    - Term registry consistency
    - Drift risk projection
    - PoU symmetry
    """
    proposal_id: str
    validator_id: str

    intent_alignment: float = 0.0
    term_registry_consistency: float = 0.0
    drift_risk_projection: float = 0.0  # Lower is better
    pou_symmetry: float = 0.0

    computed_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def score(self) -> float:
        """
        Compute semantic consistency score ∈ [0.0 – 1.0].

        This score does NOT approve the proposal.
        It only gates whether it may be presented.
        """
        # Drift risk is inverted (lower risk = higher score)
        drift_score = 1.0 - self.drift_risk_projection
        return (
            self.intent_alignment * 0.30 +
            self.term_registry_consistency * 0.25 +
            drift_score * 0.25 +
            self.pou_symmetry * 0.20
        )


@dataclass
class MediatorProposal:
    """A mediator proposal subject to influence gate."""
    proposal_id: str
    mediator_id: str
    proposal_type: str  # "alignment" or "settlement"
    content: str
    submitted_at: datetime = field(default_factory=datetime.utcnow)

    # Gate status
    gate_passed: bool = False
    gate_score: Optional[float] = None
    gate_threshold: float = 0.68

    # Validation scores from validators
    consistency_scores: Dict[str, SemanticConsistencyScore] = field(default_factory=dict)

    # Competition status
    hidden: bool = False  # True if below gate
    competition_rank: Optional[int] = None

    # Final selection
    selected: bool = False
    selected_by: Optional[str] = None  # Human selector ID


@dataclass
class InfluenceGateResult:
    """Result of the influence gate check."""
    proposal_id: str
    passed: bool
    gate_score: float
    threshold: float
    validator_contributions: Dict[str, float] = field(default_factory=dict)
    message: str = ""


@dataclass
class WeightUpdate:
    """
    A pending weight update per NCIP-011 Section 8.2.

    Weight changes are delayed (anti-gaming).
    """
    update_id: str
    actor_id: str
    actor_role: ActorRole
    field_name: str
    old_value: float
    new_value: float
    reason: str

    created_at: datetime = field(default_factory=datetime.utcnow)
    apply_after: Optional[datetime] = None
    status: WeightUpdateStatus = WeightUpdateStatus.PENDING

    # Delay in epochs (default 3 per Section 11)
    delay_epochs: int = 3


@dataclass
class ProtocolViolation:
    """A protocol violation for role crossing."""
    violation_id: str
    violation_type: ProtocolViolationType
    actor_id: str
    actor_role: ActorRole
    attempted_action: str
    detected_at: datetime = field(default_factory=datetime.utcnow)
    details: str = ""


class ValidatorMediatorCoupling:
    """
    Manages validator-mediator interaction and weight coupling per NCIP-011.

    Key features:
    - Role separation enforcement
    - Separate weight ledgers
    - Influence gate for mediator proposals
    - Semantic consistency scoring
    - Dispute phase handling
    - Delayed weight updates
    - Collusion resistance
    """

    # Default gate threshold per Section 11
    DEFAULT_GATE_THRESHOLD = 0.68

    # Weight update delay in epochs per Section 11
    DEFAULT_DELAY_EPOCHS = 3

    def __init__(self):
        self.validator_weights: Dict[str, ValidatorWeight] = {}
        self.mediator_weights: Dict[str, MediatorWeight] = {}
        self.proposals: Dict[str, MediatorProposal] = {}
        self.pending_updates: Dict[str, WeightUpdate] = {}
        self.violations: List[ProtocolViolation] = []

        self.gate_threshold = self.DEFAULT_GATE_THRESHOLD
        self.delay_epochs = self.DEFAULT_DELAY_EPOCHS

        # Dispute tracking
        self.active_disputes: Set[str] = set()  # Contract IDs with active disputes

        # Counters
        self.proposal_counter = 0
        self.update_counter = 0
        self.violation_counter = 0

    # -------------------------------------------------------------------------
    # Role Separation Enforcement
    # -------------------------------------------------------------------------

    def check_role_permission(
        self,
        actor_id: str,
        actor_role: ActorRole,
        action: str
    ) -> Tuple[bool, Optional[ProtocolViolation]]:
        """
        Check if an actor has permission for an action.

        Per NCIP-011 Section 3: Any attempt to cross roles triggers PV-V3.
        """
        if actor_role == ActorRole.VALIDATOR:
            # Check if action is prohibited for validators
            try:
                ValidatorProhibitedAction(action)
                # This is a prohibited action
                violation = self._create_violation(
                    ProtocolViolationType.PV_V3_VALIDATOR_PROPOSING,
                    actor_id, actor_role, action,
                    "Validators may NOT propose terms or negotiate outcomes"
                )
                return (False, violation)
            except ValueError:
                pass

            # Check if action is allowed
            try:
                ValidatorAction(action)
                return (True, None)
            except ValueError:
                pass

        elif actor_role == ActorRole.MEDIATOR:
            # Check if action is prohibited for mediators
            try:
                MediatorProhibitedAction(action)
                violation = self._create_violation(
                    ProtocolViolationType.PV_V3_MEDIATOR_VALIDATING,
                    actor_id, actor_role, action,
                    "Mediators may NOT validate semantics or override drift rulings"
                )
                return (False, violation)
            except ValueError:
                pass

            # Check if action is allowed
            try:
                MediatorAction(action)
                return (True, None)
            except ValueError:
                pass

        elif actor_role == ActorRole.HUMAN:
            # Humans may ratify, reject, escalate
            # But may NOT delegate final authority
            if action == "delegate_final_authority":
                violation = self._create_violation(
                    ProtocolViolationType.PV_V3_HUMAN_DELEGATING,
                    actor_id, actor_role, action,
                    "Humans may NOT delegate final authority"
                )
                return (False, violation)
            return (True, None)

        return (True, None)

    def _create_violation(
        self,
        violation_type: ProtocolViolationType,
        actor_id: str,
        actor_role: ActorRole,
        action: str,
        details: str
    ) -> ProtocolViolation:
        """Create and record a protocol violation."""
        self.violation_counter += 1
        violation = ProtocolViolation(
            violation_id=f"PV-{self.violation_counter:04d}",
            violation_type=violation_type,
            actor_id=actor_id,
            actor_role=actor_role,
            attempted_action=action,
            details=details
        )
        self.violations.append(violation)
        return violation

    # -------------------------------------------------------------------------
    # Weight Management
    # -------------------------------------------------------------------------

    def register_validator(
        self,
        validator_id: str,
        historical_accuracy: float = 0.5,
        drift_precision: float = 0.5,
        pou_consistency: float = 0.5,
        appeal_survival_rate: float = 0.5
    ) -> ValidatorWeight:
        """Register a validator with initial weights."""
        vw = ValidatorWeight(
            validator_id=validator_id,
            historical_accuracy=historical_accuracy,
            drift_precision=drift_precision,
            pou_consistency=pou_consistency,
            appeal_survival_rate=appeal_survival_rate
        )
        self.validator_weights[validator_id] = vw
        return vw

    def register_mediator(
        self,
        mediator_id: str,
        acceptance_rate: float = 0.5,
        settlement_completion: float = 0.5,
        post_settlement_dispute_frequency: float = 0.5,
        time_efficiency: float = 0.5
    ) -> MediatorWeight:
        """Register a mediator with initial weights."""
        mw = MediatorWeight(
            mediator_id=mediator_id,
            acceptance_rate=acceptance_rate,
            settlement_completion=settlement_completion,
            post_settlement_dispute_frequency=post_settlement_dispute_frequency,
            time_efficiency=time_efficiency
        )
        self.mediator_weights[mediator_id] = mw
        return mw

    def get_validator_weight(self, validator_id: str) -> Optional[float]:
        """Get a validator's current weight."""
        vw = self.validator_weights.get(validator_id)
        return vw.weight if vw else None

    def get_mediator_weight(self, mediator_id: str) -> Optional[float]:
        """Get a mediator's current weight."""
        mw = self.mediator_weights.get(mediator_id)
        return mw.weight if mw else None

    def schedule_weight_update(
        self,
        actor_id: str,
        actor_role: ActorRole,
        field_name: str,
        new_value: float,
        reason: str
    ) -> Optional[WeightUpdate]:
        """
        Schedule a weight update with delay.

        Per NCIP-011 Section 8.2: Weight changes are delayed (anti-gaming).
        """
        # Get current value
        if actor_role == ActorRole.VALIDATOR:
            vw = self.validator_weights.get(actor_id)
            if not vw:
                return None
            old_value = getattr(vw, field_name, None)
        elif actor_role == ActorRole.MEDIATOR:
            mw = self.mediator_weights.get(actor_id)
            if not mw:
                return None
            old_value = getattr(mw, field_name, None)
        else:
            return None

        if old_value is None:
            return None

        self.update_counter += 1
        update = WeightUpdate(
            update_id=f"WU-{self.update_counter:04d}",
            actor_id=actor_id,
            actor_role=actor_role,
            field_name=field_name,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
            delay_epochs=self.delay_epochs
        )
        # Set apply_after based on delay (assume 1 epoch = 1 day for simplicity)
        update.apply_after = datetime.utcnow() + timedelta(days=self.delay_epochs)

        self.pending_updates[update.update_id] = update
        return update

    def apply_pending_updates(self) -> List[WeightUpdate]:
        """Apply all pending updates that have passed their delay."""
        applied = []
        now = datetime.utcnow()

        for update in list(self.pending_updates.values()):
            if update.status != WeightUpdateStatus.PENDING:
                continue
            if update.apply_after and now < update.apply_after:
                continue

            # Apply the update
            if update.actor_role == ActorRole.VALIDATOR:
                vw = self.validator_weights.get(update.actor_id)
                if vw:
                    setattr(vw, update.field_name, update.new_value)
                    vw.invalidate_cache()
            elif update.actor_role == ActorRole.MEDIATOR:
                mw = self.mediator_weights.get(update.actor_id)
                if mw:
                    setattr(mw, update.field_name, update.new_value)
                    mw.invalidate_cache()

            update.status = WeightUpdateStatus.APPLIED
            applied.append(update)

        return applied

    # -------------------------------------------------------------------------
    # Semantic Consistency Scoring
    # -------------------------------------------------------------------------

    def compute_semantic_consistency(
        self,
        proposal_id: str,
        validator_id: str,
        intent_alignment: float,
        term_registry_consistency: float,
        drift_risk_projection: float,
        pou_symmetry: float
    ) -> SemanticConsistencyScore:
        """
        Compute semantic consistency score for a proposal.

        Per NCIP-011 Section 6: This score does NOT approve the proposal.
        It only gates whether it may be presented.
        """
        score = SemanticConsistencyScore(
            proposal_id=proposal_id,
            validator_id=validator_id,
            intent_alignment=intent_alignment,
            term_registry_consistency=term_registry_consistency,
            drift_risk_projection=drift_risk_projection,
            pou_symmetry=pou_symmetry
        )

        # Store in proposal if exists
        proposal = self.proposals.get(proposal_id)
        if proposal:
            proposal.consistency_scores[validator_id] = score

        return score

    # -------------------------------------------------------------------------
    # Influence Gate
    # -------------------------------------------------------------------------

    def submit_proposal(
        self,
        mediator_id: str,
        proposal_type: str,
        content: str
    ) -> Tuple[Optional[MediatorProposal], List[str]]:
        """
        Submit a mediator proposal.

        The proposal must pass the influence gate to be presented.
        """
        errors = []

        # Check mediator exists
        if mediator_id not in self.mediator_weights:
            errors.append(f"Mediator {mediator_id} not registered")
            return (None, errors)

        # Check role permission
        allowed, violation = self.check_role_permission(
            mediator_id, ActorRole.MEDIATOR, "propose_alignments"
        )
        if not allowed:
            errors.append(f"Role violation: {violation.details}")
            return (None, errors)

        self.proposal_counter += 1
        proposal_id = f"PROP-{datetime.utcnow().strftime('%Y%m%d')}-{self.proposal_counter:04d}"

        proposal = MediatorProposal(
            proposal_id=proposal_id,
            mediator_id=mediator_id,
            proposal_type=proposal_type,
            content=content,
            gate_threshold=self.gate_threshold
        )

        self.proposals[proposal_id] = proposal
        return (proposal, [])

    def check_influence_gate(
        self,
        proposal_id: str
    ) -> InfluenceGateResult:
        """
        Check if a proposal passes the influence gate.

        Per NCIP-011 Section 5.1:
        ∑(Validator VW × semantic_consistency_score) >= GateThreshold

        This ensures:
        - Mediators cannot push semantically weak proposals
        - Validators cannot choose winners
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return InfluenceGateResult(
                proposal_id=proposal_id,
                passed=False,
                gate_score=0.0,
                threshold=self.gate_threshold,
                message=f"Proposal {proposal_id} not found"
            )

        # Compute weighted sum
        total_score = 0.0
        contributions = {}

        for validator_id, consistency_score in proposal.consistency_scores.items():
            vw = self.validator_weights.get(validator_id)
            if not vw:
                continue

            contribution = vw.weight * consistency_score.score
            total_score += contribution
            contributions[validator_id] = contribution

        # Check gate
        passed = total_score >= self.gate_threshold
        proposal.gate_passed = passed
        proposal.gate_score = total_score
        proposal.hidden = not passed

        return InfluenceGateResult(
            proposal_id=proposal_id,
            passed=passed,
            gate_score=total_score,
            threshold=self.gate_threshold,
            validator_contributions=contributions,
            message="Gate passed" if passed else "Gate failed - proposal hidden"
        )

    # -------------------------------------------------------------------------
    # Competitive Mediation
    # -------------------------------------------------------------------------

    def get_visible_proposals(
        self,
        contract_id: Optional[str] = None
    ) -> List[MediatorProposal]:
        """
        Get all visible proposals (those that passed the gate).

        Per NCIP-011 Section 7: Proposals below gate are hidden.
        """
        visible = [p for p in self.proposals.values() if not p.hidden]

        # Sort by MW (primary), then by time
        def sort_key(p: MediatorProposal) -> Tuple[float, float]:
            mw = self.mediator_weights.get(p.mediator_id)
            weight = mw.weight if mw else 0.0
            return (-weight, p.submitted_at.timestamp())

        visible.sort(key=sort_key)

        # Assign competition ranks
        for rank, proposal in enumerate(visible, 1):
            proposal.competition_rank = rank

        return visible

    def select_proposal(
        self,
        proposal_id: str,
        selector_id: str
    ) -> Tuple[bool, str]:
        """
        Human selects a proposal from visible options.

        Per NCIP-011 Section 7: Human selection is the final arbiter.
        """
        proposal = self.proposals.get(proposal_id)
        if not proposal:
            return (False, f"Proposal {proposal_id} not found")

        if proposal.hidden:
            return (False, "Cannot select hidden proposal - gate not passed")

        proposal.selected = True
        proposal.selected_by = selector_id
        return (True, f"Proposal {proposal_id} selected by {selector_id}")

    # -------------------------------------------------------------------------
    # Dispute Handling
    # -------------------------------------------------------------------------

    def enter_dispute_phase(
        self,
        contract_id: str
    ) -> Dict[str, Any]:
        """
        Enter dispute phase for a contract.

        Per NCIP-011 Section 8.1:
        - Validator VW influence increases
        - Mediator MW influence decreases
        - No new proposals allowed once Semantic Lock engages
        """
        self.active_disputes.add(contract_id)

        return {
            "contract_id": contract_id,
            "phase": DisputePhase.ACTIVE.value,
            "validator_authority": "elevated",
            "mediator_influence": "reduced",
            "new_proposals_allowed": False
        }

    def exit_dispute_phase(
        self,
        contract_id: str,
        resolution_outcome: str
    ) -> Dict[str, Any]:
        """
        Exit dispute phase after resolution.

        Per NCIP-011 Section 8.2:
        - Mediator MW updated based on outcome
        - Validator VW updated based on appeal results
        - Weight changes are delayed
        """
        if contract_id in self.active_disputes:
            self.active_disputes.remove(contract_id)

        return {
            "contract_id": contract_id,
            "phase": DisputePhase.POST_RESOLUTION.value,
            "resolution_outcome": resolution_outcome,
            "weight_updates": "delayed per anti-gaming rules"
        }

    def is_in_dispute(self, contract_id: str) -> bool:
        """Check if a contract is in active dispute."""
        return contract_id in self.active_disputes

    def can_submit_proposal(self, contract_id: str) -> Tuple[bool, str]:
        """
        Check if new proposals can be submitted.

        Per NCIP-011 Section 8.1: No new proposals during dispute.
        """
        if contract_id in self.active_disputes:
            return (False, "No new proposals allowed during active dispute")
        return (True, "Proposals allowed")

    # -------------------------------------------------------------------------
    # Appeals & Overrides
    # -------------------------------------------------------------------------

    def record_appeal_outcome(
        self,
        validator_id: str,
        mediator_id: str,
        appeal_upheld: bool,
        slashing_applied: bool
    ) -> Dict[str, Any]:
        """
        Record appeal outcome and schedule weight updates.

        Per NCIP-011 Section 9:
        - Validators review semantics only
        - Mediator intent is irrelevant
        - Slashing handled per NCIP-010
        """
        updates = []

        # Update validator appeal survival rate
        vw = self.validator_weights.get(validator_id)
        if vw:
            # If appeal upheld, validator's decision was correct
            new_survival = min(1.0, vw.appeal_survival_rate + (0.05 if appeal_upheld else -0.05))
            update = self.schedule_weight_update(
                validator_id, ActorRole.VALIDATOR,
                "appeal_survival_rate", new_survival,
                f"Appeal {'upheld' if appeal_upheld else 'overturned'}"
            )
            if update:
                updates.append(update.update_id)

        # Update mediator if slashing applied
        if slashing_applied and mediator_id:
            mw = self.mediator_weights.get(mediator_id)
            if mw:
                new_freq = min(1.0, mw.post_settlement_dispute_frequency + 0.1)
                update = self.schedule_weight_update(
                    mediator_id, ActorRole.MEDIATOR,
                    "post_settlement_dispute_frequency", new_freq,
                    "Slashing applied after appeal"
                )
                if update:
                    updates.append(update.update_id)

        return {
            "validator_id": validator_id,
            "mediator_id": mediator_id,
            "appeal_upheld": appeal_upheld,
            "slashing_applied": slashing_applied,
            "scheduled_updates": updates
        }

    # -------------------------------------------------------------------------
    # Collusion Resistance
    # -------------------------------------------------------------------------

    def detect_collusion_signals(
        self,
        validator_id: str,
        mediator_id: str
    ) -> Dict[str, Any]:
        """
        Detect potential collusion signals.

        Per NCIP-011 Section 10, mechanisms include:
        - Separate weight ledgers
        - Gated interaction
        - Delayed weight updates
        - Appeal-based retroactive scoring
        """
        signals = []
        risk_level = "low"

        # Check if validator consistently passes mediator's proposals
        validator_proposals_passed = 0
        mediator_proposals_total = 0

        for proposal in self.proposals.values():
            if proposal.mediator_id == mediator_id:
                mediator_proposals_total += 1
                if validator_id in proposal.consistency_scores:
                    score = proposal.consistency_scores[validator_id]
                    if score.score >= 0.7:  # High consistency
                        validator_proposals_passed += 1

        if mediator_proposals_total >= 5:
            pass_rate = validator_proposals_passed / mediator_proposals_total
            if pass_rate > 0.9:
                signals.append("High pass rate between validator and mediator")
                risk_level = "medium"

        # Check for synchronized weight changes
        validator_updates = [u for u in self.pending_updates.values()
                          if u.actor_id == validator_id]
        mediator_updates = [u for u in self.pending_updates.values()
                          if u.actor_id == mediator_id]

        if validator_updates and mediator_updates:
            # Check if updates are close in time
            for vu in validator_updates:
                for mu in mediator_updates:
                    time_diff = abs((vu.created_at - mu.created_at).total_seconds())
                    if time_diff < 60:  # Within 1 minute
                        signals.append("Synchronized weight updates detected")
                        risk_level = "high"
                        break

        return {
            "validator_id": validator_id,
            "mediator_id": mediator_id,
            "signals": signals,
            "risk_level": risk_level,
            "recommendation": "Public audit trail" if signals else "No action needed"
        }

    # -------------------------------------------------------------------------
    # Machine-Readable Schema
    # -------------------------------------------------------------------------

    def generate_coupling_schema(self) -> Dict[str, Any]:
        """
        Generate machine-readable coupling schema per NCIP-011 Section 11.
        """
        return {
            "validator_mediator_coupling": {
                "version": "1.0",
                "role_separation": {
                    "enforce_strict": True,
                    "violation_code": "PV-V3"
                },
                "validator_weight": {
                    "source": "NCIP-007",
                    "applies_to": [
                        "semantic_validation",
                        "drift_detection",
                        "appeals"
                    ]
                },
                "mediator_weight": {
                    "source": "NCIP-010",
                    "applies_to": [
                        "proposal_visibility",
                        "fee_priority",
                        "matching_competitiveness"
                    ]
                },
                "influence_gate": {
                    "enabled": True,
                    "threshold": self.gate_threshold,
                    "aggregation": "weighted_sum"
                },
                "during_dispute": {
                    "mediator_influence": "reduced",
                    "validator_authority": "elevated",
                    "allow_new_proposals": False
                },
                "weight_updates": {
                    "delayed_epochs": self.delay_epochs,
                    "retroactive_adjustment": "allowed"
                }
            }
        }

    # -------------------------------------------------------------------------
    # Status & Reporting
    # -------------------------------------------------------------------------

    def get_status_summary(self) -> Dict[str, Any]:
        """Get summary of coupling system status."""
        return {
            "total_validators": len(self.validator_weights),
            "total_mediators": len(self.mediator_weights),
            "total_proposals": len(self.proposals),
            "visible_proposals": sum(1 for p in self.proposals.values() if not p.hidden),
            "hidden_proposals": sum(1 for p in self.proposals.values() if p.hidden),
            "pending_weight_updates": len([u for u in self.pending_updates.values()
                                          if u.status == WeightUpdateStatus.PENDING]),
            "protocol_violations": len(self.violations),
            "active_disputes": len(self.active_disputes),
            "gate_threshold": self.gate_threshold,
            "delay_epochs": self.delay_epochs,
            "principle": "Validators measure meaning. Mediators surface alignment. Neither may substitute for the other."
        }

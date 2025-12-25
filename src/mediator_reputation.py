"""
NatLangChain - Mediator Reputation, Bonding & Slashing
Implements NCIP-010: Market-based trust system for mediators

Core principle: Mediators earn influence only by being repeatedly correct,
aligned, and non-coercive. No mediator has authority, can finalize agreements,
or can override parties or validators.

Reputation affects only: proposal visibility, validator weighting, market selection.

Currency-Agnostic Design:
NatLangChain does not have its own native cryptocurrency. Bonds and stakes
are denominated in whatever currency is configured for the deployment
(e.g., ETH, USDC, DAI). The default token symbol is configurable.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
import hashlib
import math


# =============================================================================
# NCIP-010 Constants
# =============================================================================

# Default CTS weights (protocol-defined, may evolve via NCIP-008 precedent)
CTS_WEIGHTS = {
    "acceptance_rate": 0.20,       # w1
    "semantic_accuracy": 0.25,     # w2
    "appeal_survival": 0.15,       # w3
    "dispute_avoidance": 0.15,     # w4
    "coercion_signal": 0.15,       # w5 (penalty)
    "latency_discipline": 0.10    # w6 (penalty for late)
}

# Slashing percentages by offense
SLASHING_RATES = {
    "semantic_manipulation": (0.10, 0.30),  # 10-30% for D4 drift
    "repeated_invalid_proposals": (0.05, 0.15),  # 5-15% for 3x rejected
    "coercive_framing": (0.15, 0.15),  # Fixed 15%
    "appeal_reversal": (0.05, 0.20),  # 5-20%
    "collusion_signals": (0.05, 0.50)  # Progressive up to 50%
}

# Cooldown durations by offense type
COOLDOWN_DURATIONS = {
    "semantic_manipulation": 30,  # days
    "repeated_invalid_proposals": 7,
    "coercive_framing": 21,
    "appeal_reversal": 14,
    "collusion_signals": 60
}

# Maximum active proposals during cooldown
COOLDOWN_MAX_PROPOSALS = 1

# Minimum bond required to submit proposals (in configured staking currency)
MINIMUM_BOND = 10_000  # Units in configured currency (e.g., USDC, ETH equivalent)

# Default bond amount (in configured staking currency)
DEFAULT_BOND = 50_000  # Units in configured currency

# Default staking currency symbol (configurable per deployment)
DEFAULT_STAKING_CURRENCY = "USDC"  # Can be ETH, USDC, DAI, etc.


# =============================================================================
# Enums
# =============================================================================

class SlashingOffense(Enum):
    """Types of slashable offenses per NCIP-010 Section 6."""
    SEMANTIC_MANIPULATION = "semantic_manipulation"
    REPEATED_INVALID_PROPOSALS = "repeated_invalid_proposals"
    COERCIVE_FRAMING = "coercive_framing"
    APPEAL_REVERSAL = "appeal_reversal"
    COLLUSION_SIGNALS = "collusion_signals"


class CooldownReason(Enum):
    """Reasons for mediator cooldown."""
    SLASHING = "slashing"
    APPEAL_REVERSAL = "appeal_reversal"
    VOLUNTARY = "voluntary"
    ADMINISTRATIVE = "administrative"


class ProposalStatus(Enum):
    """Status of a mediator proposal."""
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"
    EXPIRED = "expired"


class MediatorStatus(Enum):
    """Status of a mediator in the system."""
    ACTIVE = "active"
    COOLDOWN = "cooldown"
    SUSPENDED = "suspended"
    UNBONDED = "unbonded"


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ReputationScores:
    """
    Reputation is a vector, not a scalar (NCIP-010 Section 4).
    """
    acceptance_rate: float = 0.5  # AR: % of proposals ratified
    semantic_accuracy: float = 0.5  # SA: Validator-measured drift score
    appeal_survival: float = 1.0  # AS: % surviving appeals (starts at 100%)
    dispute_avoidance: float = 1.0  # DA: Low downstream dispute frequency
    coercion_signal: float = 0.0  # CS: Penalty for pressure tactics
    latency_discipline: float = 1.0  # LD: Responsiveness

    def to_dict(self) -> Dict[str, float]:
        """Convert to dictionary representation."""
        return {
            "acceptance_rate": self.acceptance_rate,
            "semantic_accuracy": self.semantic_accuracy,
            "appeal_survival": self.appeal_survival,
            "dispute_avoidance": self.dispute_avoidance,
            "coercion_signal": self.coercion_signal,
            "latency_discipline": self.latency_discipline
        }


@dataclass
class Bond:
    """Mediator stake bond in configured staking currency."""
    amount: float
    token: str = DEFAULT_STAKING_CURRENCY  # Configurable per deployment
    locked: bool = True
    locked_at: datetime = field(default_factory=datetime.utcnow)
    unlock_requested_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "amount": self.amount,
            "token": self.token,
            "locked": self.locked,
            "locked_at": self.locked_at.isoformat(),
            "unlock_requested_at": self.unlock_requested_at.isoformat() if self.unlock_requested_at else None
        }


@dataclass
class Cooldown:
    """Active cooldown period."""
    cooldown_id: str
    reason: CooldownReason
    offense: Optional[SlashingOffense] = None
    started_at: datetime = field(default_factory=datetime.utcnow)
    duration_days: int = 14
    max_active_proposals: int = COOLDOWN_MAX_PROPOSALS
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def ends_at(self) -> datetime:
        """When the cooldown ends."""
        return self.started_at + timedelta(days=self.duration_days)

    @property
    def is_active(self) -> bool:
        """Check if cooldown is still active."""
        return datetime.utcnow() < self.ends_at

    @property
    def time_remaining_seconds(self) -> float:
        """Seconds remaining in cooldown."""
        remaining = (self.ends_at - datetime.utcnow()).total_seconds()
        return max(0, remaining)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "cooldown_id": self.cooldown_id,
            "reason": self.reason.value,
            "offense": self.offense.value if self.offense else None,
            "started_at": self.started_at.isoformat(),
            "duration_days": self.duration_days,
            "ends_at": self.ends_at.isoformat(),
            "is_active": self.is_active,
            "max_active_proposals": self.max_active_proposals
        }


@dataclass
class SlashingEvent:
    """Record of a slashing event."""
    event_id: str
    mediator_id: str
    offense: SlashingOffense
    amount_slashed: float
    percentage: float
    timestamp: datetime = field(default_factory=datetime.utcnow)
    evidence: Dict[str, Any] = field(default_factory=dict)
    treasury_portion: float = 0.0
    affected_party_portion: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "mediator_id": self.mediator_id,
            "offense": self.offense.value,
            "amount_slashed": self.amount_slashed,
            "percentage": self.percentage,
            "timestamp": self.timestamp.isoformat(),
            "treasury_portion": self.treasury_portion,
            "affected_party_portion": self.affected_party_portion
        }


@dataclass
class MediatorProposal:
    """A proposal submitted by a mediator."""
    proposal_id: str
    mediator_id: str
    contract_id: str
    content: str
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=datetime.utcnow)
    responded_at: Optional[datetime] = None
    response_latency_seconds: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "proposal_id": self.proposal_id,
            "mediator_id": self.mediator_id,
            "contract_id": self.contract_id,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "responded_at": self.responded_at.isoformat() if self.responded_at else None,
            "response_latency_seconds": self.response_latency_seconds
        }


@dataclass
class MediatorProfile:
    """
    Full mediator profile with reputation, bonding, and status.
    """
    mediator_id: str
    bond: Bond
    scores: ReputationScores = field(default_factory=ReputationScores)
    composite_trust_score: float = 0.5  # CTS
    status: MediatorStatus = MediatorStatus.ACTIVE
    supported_domains: List[str] = field(default_factory=list)
    models_used: List[str] = field(default_factory=list)
    registered_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    active_cooldowns: List[Cooldown] = field(default_factory=list)
    total_slashed: float = 0.0
    proposal_count: int = 0
    accepted_count: int = 0
    rejected_count: int = 0
    appeal_count: int = 0
    appeal_losses: int = 0
    slashing_history: List[SlashingEvent] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "mediator_id": self.mediator_id,
            "bond": self.bond.to_dict(),
            "scores": self.scores.to_dict(),
            "composite_trust_score": self.composite_trust_score,
            "status": self.status.value,
            "supported_domains": self.supported_domains,
            "models_used": self.models_used,
            "registered_at": self.registered_at.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "active_cooldowns": [c.to_dict() for c in self.active_cooldowns if c.is_active],
            "total_slashed": self.total_slashed,
            "proposal_count": self.proposal_count,
            "accepted_count": self.accepted_count,
            "rejected_count": self.rejected_count,
            "appeal_count": self.appeal_count,
            "appeal_losses": self.appeal_losses
        }


# =============================================================================
# Mediator Reputation Manager
# =============================================================================

class MediatorReputationManager:
    """
    Manages mediator reputation, bonding, and slashing per NCIP-010.

    Core principle: Mediators earn influence only by being repeatedly
    correct, aligned, and non-coercive.
    """

    def __init__(self):
        """Initialize the reputation manager."""
        self.mediators: Dict[str, MediatorProfile] = {}
        self.proposals: Dict[str, MediatorProposal] = {}
        self.treasury_balance: float = 0.0
        self._event_counter = 0

    def _generate_id(self, prefix: str) -> str:
        """Generate a unique ID."""
        self._event_counter += 1
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{prefix}:{timestamp}:{self._event_counter}"
        return f"{prefix}_{hashlib.sha256(hash_input.encode()).hexdigest()[:12]}"

    # =========================================================================
    # Registration & Bonding
    # =========================================================================

    def register_mediator(
        self,
        mediator_id: str,
        stake_amount: float = DEFAULT_BOND,
        supported_domains: Optional[List[str]] = None,
        models_used: Optional[List[str]] = None
    ) -> MediatorProfile:
        """
        Register a new mediator with required bond.

        Per NCIP-010 Section 3.1:
        - All mediator nodes MUST register a persistent mediator ID
        - Post a reputation bond (stake)
        - Declare supported domains (optional)

        Args:
            mediator_id: Unique identifier for the mediator
            stake_amount: Bond amount in NLC tokens
            supported_domains: Optional list of supported domains
            models_used: Optional list of AI models used

        Returns:
            The new mediator profile

        Raises:
            ValueError: If mediator already registered or bond too low
        """
        if mediator_id in self.mediators:
            raise ValueError(f"Mediator {mediator_id} already registered")

        if stake_amount < MINIMUM_BOND:
            raise ValueError(
                f"Bond amount {stake_amount} below minimum {MINIMUM_BOND} NLC"
            )

        bond = Bond(amount=stake_amount)

        profile = MediatorProfile(
            mediator_id=mediator_id,
            bond=bond,
            supported_domains=supported_domains or [],
            models_used=models_used or []
        )

        # Calculate initial CTS
        profile.composite_trust_score = self._calculate_cts(profile)

        self.mediators[mediator_id] = profile
        return profile

    def get_mediator(self, mediator_id: str) -> Optional[MediatorProfile]:
        """Get a mediator's profile."""
        return self.mediators.get(mediator_id)

    def is_bonded(self, mediator_id: str) -> bool:
        """Check if a mediator has a valid bond."""
        profile = self.mediators.get(mediator_id)
        if not profile:
            return False
        return profile.bond.locked and profile.bond.amount >= MINIMUM_BOND

    def can_submit_proposals(self, mediator_id: str) -> Tuple[bool, str]:
        """
        Check if a mediator can submit proposals.

        Unbonded mediators MAY observe but MAY NOT submit proposals.

        Returns:
            Tuple of (can_submit, reason)
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return False, "Mediator not registered"

        if not self.is_bonded(mediator_id):
            return False, "Mediator is unbonded"

        if profile.status == MediatorStatus.SUSPENDED:
            return False, "Mediator is suspended"

        if profile.status == MediatorStatus.UNBONDED:
            return False, "Mediator has no active bond"

        # Check cooldowns
        active_cooldowns = [c for c in profile.active_cooldowns if c.is_active]
        if active_cooldowns:
            # Count active proposals
            active_proposals = sum(
                1 for p in self.proposals.values()
                if p.mediator_id == mediator_id and p.status == ProposalStatus.PENDING
            )
            max_allowed = min(c.max_active_proposals for c in active_cooldowns)
            if active_proposals >= max_allowed:
                return False, f"Cooldown limits proposals to {max_allowed}"

        return True, "OK"

    # =========================================================================
    # Reputation Score Calculation
    # =========================================================================

    def _calculate_cts(self, profile: MediatorProfile) -> float:
        """
        Calculate Composite Trust Score (CTS) per NCIP-010 Section 5.

        Formula: CTS = w1·AR + w2·SA + w3·AS + w4·DA − w5·CS − w6·(1-LD)
        """
        scores = profile.scores
        weights = CTS_WEIGHTS

        cts = (
            weights["acceptance_rate"] * scores.acceptance_rate +
            weights["semantic_accuracy"] * scores.semantic_accuracy +
            weights["appeal_survival"] * scores.appeal_survival +
            weights["dispute_avoidance"] * scores.dispute_avoidance -
            weights["coercion_signal"] * scores.coercion_signal -
            weights["latency_discipline"] * (1.0 - scores.latency_discipline)
        )

        # Clamp to [0, 1]
        return max(0.0, min(1.0, cts))

    def update_reputation(
        self,
        mediator_id: str,
        dimension: str,
        value: float
    ) -> Optional[float]:
        """
        Update a specific reputation dimension.

        Args:
            mediator_id: The mediator to update
            dimension: Which dimension to update
            value: New value (will be clamped to [0, 1])

        Returns:
            New CTS, or None if mediator not found
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return None

        # Clamp value
        value = max(0.0, min(1.0, value))

        # Update the appropriate dimension
        if dimension == "acceptance_rate":
            profile.scores.acceptance_rate = value
        elif dimension == "semantic_accuracy":
            profile.scores.semantic_accuracy = value
        elif dimension == "appeal_survival":
            profile.scores.appeal_survival = value
        elif dimension == "dispute_avoidance":
            profile.scores.dispute_avoidance = value
        elif dimension == "coercion_signal":
            profile.scores.coercion_signal = value
        elif dimension == "latency_discipline":
            profile.scores.latency_discipline = value
        else:
            return None

        # Recalculate CTS
        profile.composite_trust_score = self._calculate_cts(profile)
        profile.last_activity = datetime.utcnow()

        return profile.composite_trust_score

    def record_proposal_outcome(
        self,
        mediator_id: str,
        accepted: bool,
        semantic_drift_score: Optional[float] = None,
        latency_seconds: Optional[float] = None,
        coercion_detected: bool = False
    ) -> Dict[str, Any]:
        """
        Record the outcome of a proposal and update reputation.

        Args:
            mediator_id: The mediator who made the proposal
            accepted: Whether the proposal was accepted
            semantic_drift_score: Validator-measured drift (0=perfect, 1=bad)
            latency_seconds: How long the mediator took to respond
            coercion_detected: Whether coercion was detected

        Returns:
            Updated reputation summary
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return {"error": f"Mediator {mediator_id} not found"}

        profile.proposal_count += 1
        if accepted:
            profile.accepted_count += 1
        else:
            profile.rejected_count += 1

        # Update acceptance rate (exponential moving average)
        alpha = 0.1  # Smoothing factor
        new_ar = 1.0 if accepted else 0.0
        profile.scores.acceptance_rate = (
            alpha * new_ar + (1 - alpha) * profile.scores.acceptance_rate
        )

        # Update semantic accuracy if provided
        if semantic_drift_score is not None:
            # Convert drift to accuracy (1 - drift)
            accuracy = max(0.0, 1.0 - semantic_drift_score)
            profile.scores.semantic_accuracy = (
                alpha * accuracy + (1 - alpha) * profile.scores.semantic_accuracy
            )

        # Update latency discipline if provided
        if latency_seconds is not None:
            # Good latency: < 60 seconds = 1.0, > 3600 = 0.0
            if latency_seconds < 60:
                ld = 1.0
            elif latency_seconds > 3600:
                ld = 0.0
            else:
                ld = 1.0 - (latency_seconds - 60) / (3600 - 60)

            profile.scores.latency_discipline = (
                alpha * ld + (1 - alpha) * profile.scores.latency_discipline
            )

        # Update coercion signal if detected
        if coercion_detected:
            profile.scores.coercion_signal = min(
                1.0, profile.scores.coercion_signal + 0.1
            )
        else:
            # Slowly decay coercion signal
            profile.scores.coercion_signal = max(
                0.0, profile.scores.coercion_signal - 0.01
            )

        # Recalculate CTS
        profile.composite_trust_score = self._calculate_cts(profile)
        profile.last_activity = datetime.utcnow()

        return {
            "mediator_id": mediator_id,
            "new_cts": profile.composite_trust_score,
            "scores": profile.scores.to_dict(),
            "proposal_count": profile.proposal_count,
            "accepted_count": profile.accepted_count
        }

    def record_appeal_outcome(
        self,
        mediator_id: str,
        appeal_survived: bool
    ) -> Dict[str, Any]:
        """
        Record the outcome of an appeal affecting a mediator.

        Args:
            mediator_id: The mediator involved
            appeal_survived: True if mediator's position survived the appeal

        Returns:
            Updated reputation summary
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return {"error": f"Mediator {mediator_id} not found"}

        profile.appeal_count += 1
        if not appeal_survived:
            profile.appeal_losses += 1

        # Update appeal survival rate
        if profile.appeal_count > 0:
            profile.scores.appeal_survival = (
                1.0 - (profile.appeal_losses / profile.appeal_count)
            )

        # Recalculate CTS
        profile.composite_trust_score = self._calculate_cts(profile)

        return {
            "mediator_id": mediator_id,
            "appeal_survived": appeal_survived,
            "appeal_survival_rate": profile.scores.appeal_survival,
            "new_cts": profile.composite_trust_score
        }

    def record_downstream_dispute(
        self,
        mediator_id: str,
        dispute_occurred: bool
    ) -> Dict[str, Any]:
        """
        Record whether a downstream dispute occurred after mediation.

        Args:
            mediator_id: The mediator involved
            dispute_occurred: Whether a dispute arose

        Returns:
            Updated reputation summary
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return {"error": f"Mediator {mediator_id} not found"}

        alpha = 0.05  # Slow-moving average for dispute avoidance
        new_da = 0.0 if dispute_occurred else 1.0
        profile.scores.dispute_avoidance = (
            alpha * new_da + (1 - alpha) * profile.scores.dispute_avoidance
        )

        # Recalculate CTS
        profile.composite_trust_score = self._calculate_cts(profile)

        return {
            "mediator_id": mediator_id,
            "dispute_avoidance": profile.scores.dispute_avoidance,
            "new_cts": profile.composite_trust_score
        }

    # =========================================================================
    # Slashing
    # =========================================================================

    def slash(
        self,
        mediator_id: str,
        offense: SlashingOffense,
        severity: float = 0.5,
        evidence: Optional[Dict[str, Any]] = None,
        affected_party_id: Optional[str] = None
    ) -> Optional[SlashingEvent]:
        """
        Slash a mediator's bond for an offense.

        Slashing is automatic, deterministic, and non-discretionary.

        Args:
            mediator_id: The mediator to slash
            offense: Type of offense
            severity: Severity factor (0-1) affecting percentage slashed
            evidence: Evidence of the offense
            affected_party_id: If there's an affected party to compensate

        Returns:
            SlashingEvent, or None if mediator not found
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return None

        # Calculate slash percentage based on offense and severity
        min_pct, max_pct = SLASHING_RATES.get(
            offense.value, (0.05, 0.15)
        )
        slash_percentage = min_pct + severity * (max_pct - min_pct)

        # Calculate amount to slash
        amount_to_slash = profile.bond.amount * slash_percentage

        # Ensure we don't slash more than the bond
        amount_to_slash = min(amount_to_slash, profile.bond.amount)

        # Split between treasury and affected party
        if affected_party_id:
            affected_party_portion = amount_to_slash * 0.5
            treasury_portion = amount_to_slash * 0.5
        else:
            affected_party_portion = 0.0
            treasury_portion = amount_to_slash

        # Apply slashing
        profile.bond.amount -= amount_to_slash
        profile.total_slashed += amount_to_slash
        self.treasury_balance += treasury_portion

        # Create slashing event
        event = SlashingEvent(
            event_id=self._generate_id("slash"),
            mediator_id=mediator_id,
            offense=offense,
            amount_slashed=amount_to_slash,
            percentage=slash_percentage,
            evidence=evidence or {},
            treasury_portion=treasury_portion,
            affected_party_portion=affected_party_portion
        )

        profile.slashing_history.append(event)

        # Apply cooldown
        self._apply_cooldown(profile, offense)

        # Check if bond drops below minimum
        if profile.bond.amount < MINIMUM_BOND:
            profile.status = MediatorStatus.UNBONDED

        return event

    def _apply_cooldown(
        self,
        profile: MediatorProfile,
        offense: SlashingOffense
    ) -> Cooldown:
        """Apply a cooldown period after slashing."""
        duration = COOLDOWN_DURATIONS.get(offense.value, 14)

        cooldown = Cooldown(
            cooldown_id=self._generate_id("cooldown"),
            reason=CooldownReason.SLASHING,
            offense=offense,
            duration_days=duration
        )

        profile.active_cooldowns.append(cooldown)
        if profile.status == MediatorStatus.ACTIVE:
            profile.status = MediatorStatus.COOLDOWN

        return cooldown

    def check_repeated_invalid_proposals(
        self,
        mediator_id: str,
        window_days: int = 30
    ) -> Tuple[bool, int]:
        """
        Check if mediator has 3+ rejected proposals in the window.

        Args:
            mediator_id: The mediator to check
            window_days: How far back to look

        Returns:
            Tuple of (should_slash, rejection_count)
        """
        profile = self.mediators.get(mediator_id)
        if not profile:
            return False, 0

        cutoff = datetime.utcnow() - timedelta(days=window_days)

        rejected_count = sum(
            1 for p in self.proposals.values()
            if p.mediator_id == mediator_id
            and p.status == ProposalStatus.REJECTED
            and p.created_at > cutoff
        )

        return rejected_count >= 3, rejected_count

    # =========================================================================
    # Market Dynamics
    # =========================================================================

    def get_proposal_ranking(
        self,
        mediator_ids: List[str],
        include_cts: bool = True,
        diversity_weight: float = 0.2
    ) -> List[Dict[str, Any]]:
        """
        Rank mediator proposals by CTS with diversity weighting.

        Per NCIP-010 Section 8:
        - Proposals ranked by CTS
        - Diminishing returns on volume
        - Diversity-weighted sampling

        Args:
            mediator_ids: List of mediators with proposals
            include_cts: Whether to include CTS in results
            diversity_weight: Weight for diversity bonus

        Returns:
            Ranked list of mediators with scores
        """
        rankings = []

        for mid in mediator_ids:
            profile = self.mediators.get(mid)
            if not profile:
                continue

            # Base score is CTS
            base_score = profile.composite_trust_score

            # Apply diminishing returns on volume
            volume_factor = 1.0 / (1.0 + 0.1 * profile.proposal_count)

            # Diversity bonus for less common domains/models
            diversity_bonus = 0.0
            if profile.supported_domains:
                # Bonus for having specialized domains
                diversity_bonus += diversity_weight * 0.5
            if profile.models_used and len(profile.models_used) > 1:
                # Bonus for multi-model approach
                diversity_bonus += diversity_weight * 0.5

            final_score = base_score * volume_factor + diversity_bonus

            rankings.append({
                "mediator_id": mid,
                "final_score": final_score,
                "cts": profile.composite_trust_score if include_cts else None,
                "volume_factor": volume_factor,
                "diversity_bonus": diversity_bonus,
                "status": profile.status.value
            })

        # Sort by final score descending
        rankings.sort(key=lambda x: x["final_score"], reverse=True)

        return rankings

    def sample_proposals_by_trust(
        self,
        mediator_ids: List[str],
        sample_size: int = 3
    ) -> List[str]:
        """
        Sample mediators proportional to their trust scores.

        Per NCIP-010 Section 8.1: Validators sample proposals proportional to trust.

        Args:
            mediator_ids: List of mediator IDs to sample from
            sample_size: Number of mediators to sample

        Returns:
            List of sampled mediator IDs
        """
        if not mediator_ids:
            return []

        # Get CTS for each mediator
        weights = []
        valid_ids = []
        for mid in mediator_ids:
            profile = self.mediators.get(mid)
            if profile and profile.status in [MediatorStatus.ACTIVE, MediatorStatus.COOLDOWN]:
                weights.append(profile.composite_trust_score + 0.1)  # Add small constant
                valid_ids.append(mid)

        if not valid_ids:
            return []

        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return valid_ids[:sample_size]

        probabilities = [w / total_weight for w in weights]

        # Sample without replacement
        import random
        sampled = []
        remaining_ids = list(valid_ids)
        remaining_probs = list(probabilities)

        for _ in range(min(sample_size, len(remaining_ids))):
            if not remaining_ids:
                break

            # Weighted random choice
            r = random.random()
            cumulative = 0.0
            chosen_idx = 0
            for i, p in enumerate(remaining_probs):
                cumulative += p
                if r <= cumulative:
                    chosen_idx = i
                    break

            sampled.append(remaining_ids[chosen_idx])

            # Remove chosen mediator
            del remaining_ids[chosen_idx]
            del remaining_probs[chosen_idx]

            # Renormalize remaining probabilities
            total = sum(remaining_probs)
            if total > 0:
                remaining_probs = [p / total for p in remaining_probs]

        return sampled

    # =========================================================================
    # Treasury & Subsidy
    # =========================================================================

    def get_treasury_balance(self) -> float:
        """Get the current treasury balance from slashing."""
        return self.treasury_balance

    def allocate_defensive_subsidy(
        self,
        amount: float,
        purpose: str
    ) -> Dict[str, Any]:
        """
        Allocate treasury funds for defensive purposes.

        Per NCIP-010 Section 9:
        - Defensive dispute subsidies
        - Escalation bounty pools
        - Harassment-mitigation reserves

        Args:
            amount: Amount to allocate
            purpose: Purpose of allocation

        Returns:
            Allocation result
        """
        if amount > self.treasury_balance:
            return {
                "success": False,
                "message": f"Insufficient treasury balance: {self.treasury_balance} < {amount}"
            }

        self.treasury_balance -= amount

        return {
            "success": True,
            "amount": amount,
            "purpose": purpose,
            "remaining_balance": self.treasury_balance
        }

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_mediator_summary(self, mediator_id: str) -> Dict[str, Any]:
        """Get a summary of a mediator's reputation."""
        profile = self.mediators.get(mediator_id)
        if not profile:
            return {"error": f"Mediator {mediator_id} not found"}

        return {
            "mediator_id": mediator_id,
            "status": profile.status.value,
            "composite_trust_score": profile.composite_trust_score,
            "bond_amount": profile.bond.amount,
            "is_bonded": self.is_bonded(mediator_id),
            "can_submit": self.can_submit_proposals(mediator_id),
            "scores": profile.scores.to_dict(),
            "total_proposals": profile.proposal_count,
            "acceptance_rate": (
                profile.accepted_count / profile.proposal_count
                if profile.proposal_count > 0 else 0
            ),
            "total_slashed": profile.total_slashed,
            "active_cooldowns": len([c for c in profile.active_cooldowns if c.is_active])
        }

    def list_mediators(
        self,
        min_cts: Optional[float] = None,
        status: Optional[MediatorStatus] = None,
        domain: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List mediators matching criteria.

        Args:
            min_cts: Minimum composite trust score
            status: Filter by status
            domain: Filter by supported domain

        Returns:
            List of mediator summaries
        """
        results = []

        for mid, profile in self.mediators.items():
            # Apply filters
            if min_cts is not None and profile.composite_trust_score < min_cts:
                continue

            if status is not None and profile.status != status:
                continue

            if domain is not None and domain not in profile.supported_domains:
                continue

            results.append(self.get_mediator_summary(mid))

        # Sort by CTS descending
        results.sort(
            key=lambda x: x.get("composite_trust_score", 0),
            reverse=True
        )

        return results

    def cleanup_expired_cooldowns(self) -> int:
        """
        Remove expired cooldowns and update mediator statuses.

        Returns:
            Number of cooldowns removed
        """
        removed = 0

        for profile in self.mediators.values():
            original_count = len(profile.active_cooldowns)
            profile.active_cooldowns = [
                c for c in profile.active_cooldowns if c.is_active
            ]
            removed += original_count - len(profile.active_cooldowns)

            # Update status if no more cooldowns
            if not profile.active_cooldowns and profile.status == MediatorStatus.COOLDOWN:
                if profile.bond.amount >= MINIMUM_BOND:
                    profile.status = MediatorStatus.ACTIVE
                else:
                    profile.status = MediatorStatus.UNBONDED

        return removed


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_manager: Optional[MediatorReputationManager] = None


def get_reputation_manager() -> MediatorReputationManager:
    """Get the default reputation manager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = MediatorReputationManager()
    return _default_manager


def reset_reputation_manager() -> None:
    """Reset the default reputation manager (useful for testing)."""
    global _default_manager
    _default_manager = None


def get_ncip_010_config() -> Dict[str, Any]:
    """Get NCIP-010 configuration."""
    return {
        "version": "1.0",
        "cts_weights": CTS_WEIGHTS,
        "slashing_rates": {
            k: {"min": v[0], "max": v[1]}
            for k, v in SLASHING_RATES.items()
        },
        "cooldown_durations": COOLDOWN_DURATIONS,
        "minimum_bond": MINIMUM_BOND,
        "default_bond": DEFAULT_BOND,
        "cooldown_max_proposals": COOLDOWN_MAX_PROPOSALS
    }

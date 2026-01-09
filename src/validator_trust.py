"""
NatLangChain - Validator Trust Scoring & Reliability Weighting
Implements NCIP-007: Trust profiles, decay/recovery, and consensus weighting

Trust influences weight, not authority.
Validators never decide outcomes alone, never override Semantic Locks,
and never gain semantic authorship.
"""

import hashlib
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

# =============================================================================
# NCIP-007 Constants (from machine-readable schema)
# =============================================================================

# Base weights by validator type
BASE_WEIGHTS = {"llm": 1.0, "hybrid": 1.1, "symbolic": 0.9, "human": 1.2}

# Maximum effective weight any single validator can have (anti-centralization)
MAX_EFFECTIVE_WEIGHT = 0.35

# Decay parameters
DECAY_LAMBDA = 0.002  # Decay rate constant
INACTIVITY_THRESHOLD_DAYS = 30  # Days before decay begins

# Safeguards
MIN_VALIDATOR_DIVERSITY = 3  # Minimum validators for valid consensus
MINORITY_SIGNAL_VISIBILITY = True  # Low-trust signals must be visible


# =============================================================================
# Enums
# =============================================================================


class ValidatorType(Enum):
    """Types of validators in the NatLangChain ecosystem."""

    LLM = "llm"
    HYBRID = "hybrid"
    SYMBOLIC = "symbolic"
    HUMAN = "human"


class TrustScope(Enum):
    """
    Trust is scoped, not global.
    A validator may be trusted in one scope and weak in another.
    """

    SEMANTIC_PARSING = "semantic_parsing"
    DRIFT_DETECTION = "drift_detection"
    PROOF_OF_UNDERSTANDING = "proof_of_understanding"
    DISPUTE_ANALYSIS = "dispute_analysis"
    LEGAL_TRANSLATION_REVIEW = "legal_translation_review"


class TrustSignalType(Enum):
    """Types of trust signals."""

    POSITIVE = "positive"
    NEGATIVE = "negative"


class PositiveSignal(Enum):
    """
    Positive signals that increase trust (Section 5.1).
    """

    CONSENSUS_MATCH = "consensus_match"  # Matches consensus outcomes
    POU_RATIFIED = "pou_ratified"  # Produces PoUs later ratified by humans
    CORRECT_DRIFT_FLAG = "correct_drift_flag"  # Correctly flags semantic drift
    DISPUTE_PERFORMANCE = "dispute_performance"  # Performs well in escalated disputes
    CONSISTENCY = "consistency"  # Remains consistent across re-validations


class NegativeSignal(Enum):
    """
    Negative signals that decrease trust (Section 5.2).
    """

    OVERRULED_BY_LOCK = "overruled_by_lock"  # Overruled by Semantic Lock
    FALSE_POSITIVE_DRIFT = "false_positive_drift"  # High false-positive drift detection
    UNAUTHORIZED_INTERPRETATION = (
        "unauthorized_interpretation"  # Introduces unauthorized interpretations
    )
    CONSENSUS_DISAGREEMENT = "consensus_disagreement"  # Disagrees with consensus disproportionately
    HARASSMENT_PATTERN = "harassment_pattern"  # Implicated in harassment patterns


# =============================================================================
# Data Classes
# =============================================================================


@dataclass
class ValidatorIdentity:
    """
    Each validator has a persistent identity (Section 3).
    """

    validator_id: str
    validator_type: ValidatorType
    model_version: str | None = None
    operator_id: str | None = None
    declared_capabilities: list[TrustScope] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "validator_id": self.validator_id,
            "validator_type": self.validator_type.value,
            "model_version": self.model_version,
            "operator_id": self.operator_id,
            "declared_capabilities": [c.value for c in self.declared_capabilities],
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class ScopedScore:
    """Score for a specific trust scope."""

    scope: TrustScope
    score: float  # 0.0 to 1.0
    sample_size: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "scope": self.scope.value,
            "score": self.score,
            "sample_size": self.sample_size,
            "last_updated": self.last_updated.isoformat(),
        }


@dataclass
class TrustEvent:
    """A single trust-affecting event."""

    event_id: str
    validator_id: str
    signal_type: TrustSignalType
    signal: str  # PositiveSignal or NegativeSignal value
    scope: TrustScope
    magnitude: float  # How much trust changed
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "event_id": self.event_id,
            "validator_id": self.validator_id,
            "signal_type": self.signal_type.value,
            "signal": self.signal,
            "scope": self.scope.value,
            "magnitude": self.magnitude,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class TrustProfile:
    """
    Each validator maintains a Trust Profile (Section 4).
    """

    validator_id: str
    version: str = "1.0"
    overall_score: float = 0.5  # Default neutral score
    scoped_scores: dict[TrustScope, ScopedScore] = field(default_factory=dict)
    confidence_interval: float = 0.15  # Default high uncertainty
    sample_size: int = 0
    last_updated: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    is_frozen: bool = False  # True during disputes
    frozen_at: datetime | None = None
    freeze_reason: str | None = None
    events: list[TrustEvent] = field(default_factory=list)

    def get_scoped_score(self, scope: TrustScope) -> float:
        """Get score for a specific scope, defaulting to overall if not set."""
        if scope in self.scoped_scores:
            return self.scoped_scores[scope].score
        return self.overall_score

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "validator_id": self.validator_id,
            "version": self.version,
            "overall_score": self.overall_score,
            "scoped_scores": {
                scope.value: score.to_dict() for scope, score in self.scoped_scores.items()
            },
            "confidence_interval": self.confidence_interval,
            "sample_size": self.sample_size,
            "last_updated": self.last_updated.isoformat(),
            "last_activity": self.last_activity.isoformat(),
            "is_frozen": self.is_frozen,
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "freeze_reason": self.freeze_reason,
        }


@dataclass
class WeightedSignal:
    """A validator's signal with its computed weight."""

    validator_id: str
    signal_value: Any  # The actual validation output
    raw_weight: float
    effective_weight: float
    trust_score: float
    scope_modifier: float
    is_minority: bool = False  # For visibility tracking


@dataclass
class ConsensusInput:
    """Input for weighted consensus calculation."""

    signals: list[WeightedSignal]
    min_validators: int = MIN_VALIDATOR_DIVERSITY
    enforce_diversity: bool = True


# =============================================================================
# Trust Score Manager
# =============================================================================


class TrustManager:
    """
    Manages validator trust profiles, decay, recovery, and weighting.

    Core principle (Section 2): Trust influences weight, not authority.
    """

    def __init__(self):
        """Initialize the trust manager."""
        self.profiles: dict[str, TrustProfile] = {}
        self.identities: dict[str, ValidatorIdentity] = {}
        self._event_counter = 0

    def _generate_event_id(self) -> str:
        """Generate a unique event ID."""
        self._event_counter += 1
        timestamp = datetime.utcnow().isoformat()
        hash_input = f"{timestamp}:{self._event_counter}"
        return hashlib.sha256(hash_input.encode()).hexdigest()[:16]

    # =========================================================================
    # Profile Management
    # =========================================================================

    def register_validator(
        self,
        validator_id: str,
        validator_type: ValidatorType,
        model_version: str | None = None,
        operator_id: str | None = None,
        declared_capabilities: list[TrustScope] | None = None,
    ) -> TrustProfile:
        """
        Register a new validator and create its trust profile.

        Args:
            validator_id: Unique identifier for the validator
            validator_type: Type of validator (LLM, hybrid, symbolic, human)
            model_version: Model version (for LLM/hybrid)
            operator_id: Operator ID (for human validators)
            declared_capabilities: List of scopes the validator claims competency in

        Returns:
            The new trust profile
        """
        if validator_id in self.profiles:
            raise ValueError(f"Validator {validator_id} already registered")

        # Create identity
        identity = ValidatorIdentity(
            validator_id=validator_id,
            validator_type=validator_type,
            model_version=model_version,
            operator_id=operator_id,
            declared_capabilities=declared_capabilities or [],
        )
        self.identities[validator_id] = identity

        # Create profile with initial scores
        profile = TrustProfile(validator_id=validator_id)

        # Initialize scoped scores for declared capabilities
        for scope in declared_capabilities or []:
            profile.scoped_scores[scope] = ScopedScore(
                scope=scope,
                score=0.5,  # Neutral starting score
                sample_size=0,
            )

        self.profiles[validator_id] = profile
        return profile

    def get_profile(self, validator_id: str) -> TrustProfile | None:
        """Get a validator's trust profile."""
        return self.profiles.get(validator_id)

    def get_identity(self, validator_id: str) -> ValidatorIdentity | None:
        """Get a validator's identity."""
        return self.identities.get(validator_id)

    # =========================================================================
    # Trust Score Updates
    # =========================================================================

    def record_positive_signal(
        self,
        validator_id: str,
        signal: PositiveSignal,
        scope: TrustScope,
        magnitude: float = 0.05,
        metadata: dict[str, Any] | None = None,
    ) -> TrustEvent | None:
        """
        Record a positive trust signal for a validator.

        Args:
            validator_id: The validator receiving the signal
            signal: Type of positive signal
            scope: The scope this signal applies to
            magnitude: How much to increase trust (default 0.05)
            metadata: Additional context about the signal

        Returns:
            The trust event, or None if validator not found or frozen
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return None

        # Check if frozen (Section 9)
        if profile.is_frozen:
            return None

        # Create event
        event = TrustEvent(
            event_id=self._generate_event_id(),
            validator_id=validator_id,
            signal_type=TrustSignalType.POSITIVE,
            signal=signal.value,
            scope=scope,
            magnitude=magnitude,
            metadata=metadata or {},
        )

        # Update scoped score
        if scope not in profile.scoped_scores:
            profile.scoped_scores[scope] = ScopedScore(
                scope=scope, score=profile.overall_score, sample_size=0
            )

        scoped = profile.scoped_scores[scope]
        scoped.score = min(1.0, scoped.score + magnitude)
        scoped.sample_size += 1
        scoped.last_updated = datetime.utcnow()

        # Update overall score (weighted average of scoped scores)
        self._recalculate_overall_score(profile)

        # Update activity timestamp
        profile.last_activity = datetime.utcnow()
        profile.last_updated = datetime.utcnow()
        profile.sample_size += 1
        profile.events.append(event)

        # Reduce confidence interval as sample size grows
        self._update_confidence_interval(profile)

        return event

    def record_negative_signal(
        self,
        validator_id: str,
        signal: NegativeSignal,
        scope: TrustScope,
        magnitude: float = 0.05,
        metadata: dict[str, Any] | None = None,
    ) -> TrustEvent | None:
        """
        Record a negative trust signal for a validator.

        Args:
            validator_id: The validator receiving the signal
            signal: Type of negative signal
            scope: The scope this signal applies to
            magnitude: How much to decrease trust (default 0.05)
            metadata: Additional context about the signal

        Returns:
            The trust event, or None if validator not found or frozen
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return None

        # Check if frozen (Section 9)
        if profile.is_frozen:
            return None

        # Apply accelerated decay for harassment patterns (Section 11)
        if signal == NegativeSignal.HARASSMENT_PATTERN:
            magnitude *= 2.0  # Accelerated decay

        # Create event
        event = TrustEvent(
            event_id=self._generate_event_id(),
            validator_id=validator_id,
            signal_type=TrustSignalType.NEGATIVE,
            signal=signal.value,
            scope=scope,
            magnitude=magnitude,
            metadata=metadata or {},
        )

        # Update scoped score
        if scope not in profile.scoped_scores:
            profile.scoped_scores[scope] = ScopedScore(
                scope=scope, score=profile.overall_score, sample_size=0
            )

        scoped = profile.scoped_scores[scope]
        scoped.score = max(0.0, scoped.score - magnitude)
        scoped.sample_size += 1
        scoped.last_updated = datetime.utcnow()

        # Update overall score
        self._recalculate_overall_score(profile)

        # Update activity timestamp
        profile.last_activity = datetime.utcnow()
        profile.last_updated = datetime.utcnow()
        profile.sample_size += 1
        profile.events.append(event)

        # Update confidence interval
        self._update_confidence_interval(profile)

        return event

    def _recalculate_overall_score(self, profile: TrustProfile) -> None:
        """Recalculate overall score as weighted average of scoped scores."""
        if not profile.scoped_scores:
            return

        total_weight = 0
        weighted_sum = 0

        for scoped in profile.scoped_scores.values():
            weight = scoped.sample_size + 1  # Add 1 to avoid zero weight
            weighted_sum += scoped.score * weight
            total_weight += weight

        if total_weight > 0:
            profile.overall_score = weighted_sum / total_weight

    def _update_confidence_interval(self, profile: TrustProfile) -> None:
        """
        Update confidence interval based on sample size.
        More samples = tighter confidence interval.
        """
        if profile.sample_size == 0:
            profile.confidence_interval = 0.15  # High uncertainty
        elif profile.sample_size < 10:
            profile.confidence_interval = 0.12
        elif profile.sample_size < 50:
            profile.confidence_interval = 0.09
        elif profile.sample_size < 100:
            profile.confidence_interval = 0.07
        elif profile.sample_size < 500:
            profile.confidence_interval = 0.05
        else:
            profile.confidence_interval = 0.03  # Low uncertainty

    # =========================================================================
    # Trust Decay (Section 8.1)
    # =========================================================================

    def apply_temporal_decay(
        self, validator_id: str, reference_time: datetime | None = None
    ) -> TrustProfile | None:
        """
        Apply temporal decay to a validator's trust score.

        Formula: score_t = score_0 * e^(-lambda * delta_t)

        Decay only applies after INACTIVITY_THRESHOLD_DAYS of inactivity.

        Args:
            validator_id: The validator to apply decay to
            reference_time: Time to measure decay from (default: now)

        Returns:
            Updated profile, or None if not found or frozen
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return None

        # No decay while frozen
        if profile.is_frozen:
            return profile

        reference_time = reference_time or datetime.utcnow()
        days_inactive = (reference_time - profile.last_activity).days

        # Only decay after threshold
        if days_inactive <= INACTIVITY_THRESHOLD_DAYS:
            return profile

        # Calculate decay
        decay_days = days_inactive - INACTIVITY_THRESHOLD_DAYS
        decay_factor = math.exp(-DECAY_LAMBDA * decay_days)

        # Apply decay to overall score
        profile.overall_score *= decay_factor

        # Apply decay to scoped scores
        for scoped in profile.scoped_scores.values():
            scoped.score *= decay_factor
            scoped.last_updated = reference_time

        profile.last_updated = reference_time

        return profile

    def apply_decay_to_all(self, reference_time: datetime | None = None) -> list[str]:
        """
        Apply temporal decay to all registered validators.

        Args:
            reference_time: Time to measure decay from

        Returns:
            List of validator IDs that had decay applied
        """
        decayed = []
        reference_time = reference_time or datetime.utcnow()

        for validator_id in self.profiles:
            profile = self.profiles[validator_id]
            days_inactive = (reference_time - profile.last_activity).days

            if days_inactive > INACTIVITY_THRESHOLD_DAYS:
                self.apply_temporal_decay(validator_id, reference_time)
                decayed.append(validator_id)

        return decayed

    # =========================================================================
    # Trust Recovery (Section 8.2)
    # =========================================================================

    def initiate_recovery(
        self, validator_id: str, recovery_type: str = "low_stakes_validation"
    ) -> dict[str, Any]:
        """
        Initiate trust recovery process for a validator.

        Recovery options:
        - low_stakes_validation: Participate in low-stakes validations
        - benchmark_challenge: Pass benchmark challenges
        - corrected_behavior: Demonstrate corrected behavior post-penalty

        Args:
            validator_id: The validator seeking recovery
            recovery_type: Type of recovery process

        Returns:
            Recovery status and requirements
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return {"status": "error", "message": f"Validator {validator_id} not found"}

        if profile.is_frozen:
            return {"status": "error", "message": "Cannot initiate recovery while trust is frozen"}

        recovery_requirements = {
            "low_stakes_validation": {
                "required_validations": 10,
                "max_stake_level": "low",
                "required_success_rate": 0.8,
            },
            "benchmark_challenge": {"required_challenges": 5, "min_score": 0.75},
            "corrected_behavior": {"observation_period_days": 14, "max_negative_signals": 1},
        }

        if recovery_type not in recovery_requirements:
            return {"status": "error", "message": f"Unknown recovery type: {recovery_type}"}

        return {
            "status": "initiated",
            "validator_id": validator_id,
            "recovery_type": recovery_type,
            "current_score": profile.overall_score,
            "requirements": recovery_requirements[recovery_type],
            "message": "Recovery process initiated",
        }

    # =========================================================================
    # Weighting Function (Section 6)
    # =========================================================================

    def calculate_effective_weight(
        self, validator_id: str, scope: TrustScope, scope_modifier: float = 1.0
    ) -> float:
        """
        Calculate effective weight for a validator's signal.

        Formula: effective_weight = base_weight * trust_score * scope_modifier

        Weight is capped at MAX_EFFECTIVE_WEIGHT (anti-centralization).

        Args:
            validator_id: The validator
            scope: The scope for this weight calculation
            scope_modifier: Task relevance modifier (default 1.0)

        Returns:
            Effective weight (0.0 to MAX_EFFECTIVE_WEIGHT)
        """
        profile = self.profiles.get(validator_id)
        identity = self.identities.get(validator_id)

        if not profile or not identity:
            return 0.0

        # Get base weight for validator type
        base_weight = BASE_WEIGHTS.get(identity.validator_type.value, 1.0)

        # Get trust score for scope
        trust_score = profile.get_scoped_score(scope)

        # Calculate effective weight
        effective_weight = base_weight * trust_score * scope_modifier

        # Apply cap (Section 10)
        return min(effective_weight, MAX_EFFECTIVE_WEIGHT)

    def get_weighted_signal(
        self, validator_id: str, signal_value: Any, scope: TrustScope, scope_modifier: float = 1.0
    ) -> WeightedSignal | None:
        """
        Create a weighted signal from a validator's output.

        Args:
            validator_id: The validator
            signal_value: The validation output
            scope: The scope for this signal
            scope_modifier: Task relevance modifier

        Returns:
            WeightedSignal, or None if validator not found
        """
        profile = self.profiles.get(validator_id)
        identity = self.identities.get(validator_id)

        if not profile or not identity:
            return None

        base_weight = BASE_WEIGHTS.get(identity.validator_type.value, 1.0)
        trust_score = profile.get_scoped_score(scope)
        effective_weight = self.calculate_effective_weight(validator_id, scope, scope_modifier)

        return WeightedSignal(
            validator_id=validator_id,
            signal_value=signal_value,
            raw_weight=base_weight,
            effective_weight=effective_weight,
            trust_score=trust_score,
            scope_modifier=scope_modifier,
        )

    # =========================================================================
    # Dispute Handling (Section 9)
    # =========================================================================

    def freeze_trust(self, validator_id: str, dispute_id: str) -> bool:
        """
        Freeze a validator's trust score at dispute start.

        During disputes:
        - Validator trust is frozen at dispute start
        - Post-hoc trust updates are prohibited
        - Dispute outcomes feed back into future trust updates

        Args:
            validator_id: The validator to freeze
            dispute_id: The dispute triggering the freeze

        Returns:
            True if freeze was successful
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return False

        profile.is_frozen = True
        profile.frozen_at = datetime.utcnow()
        profile.freeze_reason = f"dispute:{dispute_id}"

        return True

    def unfreeze_trust(
        self, validator_id: str, dispute_outcome: dict[str, Any] | None = None
    ) -> bool:
        """
        Unfreeze a validator's trust after dispute resolution.

        Optionally applies outcome-based trust updates.

        Args:
            validator_id: The validator to unfreeze
            dispute_outcome: Optional dispute resolution data

        Returns:
            True if unfreeze was successful
        """
        profile = self.profiles.get(validator_id)
        if not profile:
            return False

        profile.is_frozen = False
        profile.frozen_at = None
        profile.freeze_reason = None

        # Apply dispute outcome as trust signal if provided
        if dispute_outcome:
            outcome_type = dispute_outcome.get("outcome_type")
            scope = dispute_outcome.get("scope", TrustScope.DISPUTE_ANALYSIS)

            if outcome_type == "positive":
                self.record_positive_signal(
                    validator_id,
                    PositiveSignal.DISPUTE_PERFORMANCE,
                    scope,
                    magnitude=dispute_outcome.get("magnitude", 0.05),
                )
            elif outcome_type == "negative":
                self.record_negative_signal(
                    validator_id,
                    NegativeSignal.OVERRULED_BY_LOCK,
                    scope,
                    magnitude=dispute_outcome.get("magnitude", 0.05),
                )

        return True

    def freeze_all_for_dispute(self, dispute_id: str) -> list[str]:
        """
        Freeze all validators' trust for a dispute.

        Args:
            dispute_id: The dispute ID

        Returns:
            List of frozen validator IDs
        """
        frozen = []
        for validator_id in self.profiles:
            if self.freeze_trust(validator_id, dispute_id):
                frozen.append(validator_id)
        return frozen

    # =========================================================================
    # Anti-Centralization Safeguards (Section 10)
    # =========================================================================

    def check_diversity_threshold(self, validator_ids: list[str]) -> dict[str, Any]:
        """
        Check if validator set meets diversity threshold.

        Args:
            validator_ids: List of validators to check

        Returns:
            Diversity check result
        """
        unique_validators = len(set(validator_ids))
        unique_types = set()

        for vid in validator_ids:
            identity = self.identities.get(vid)
            if identity:
                unique_types.add(identity.validator_type)

        meets_threshold = unique_validators >= MIN_VALIDATOR_DIVERSITY

        return {
            "meets_threshold": meets_threshold,
            "unique_validators": unique_validators,
            "required_validators": MIN_VALIDATOR_DIVERSITY,
            "unique_types": len(unique_types),
            "types_present": [t.value for t in unique_types],
        }

    def identify_minority_signals(
        self, weighted_signals: list[WeightedSignal], threshold: float = 0.25
    ) -> list[WeightedSignal]:
        """
        Identify minority signals that must remain visible.

        Low-trust minority signals must be visible (not dominant).

        Args:
            weighted_signals: List of weighted signals
            threshold: Trust threshold below which signals are minority

        Returns:
            List of minority signals
        """
        minority = []
        for signal in weighted_signals:
            if signal.trust_score < threshold:
                signal.is_minority = True
                minority.append(signal)
        return minority

    def validate_consensus_input(
        self, signals: list[WeightedSignal], scope: TrustScope
    ) -> dict[str, Any]:
        """
        Validate inputs for weighted consensus calculation.

        Checks:
        - Minimum validator diversity
        - Weight cap enforcement
        - Minority signal visibility

        Args:
            signals: Weighted signals from validators
            scope: The scope of this consensus

        Returns:
            Validation result with any issues
        """
        issues = []
        warnings = []

        # Check diversity
        validator_ids = [s.validator_id for s in signals]
        diversity = self.check_diversity_threshold(validator_ids)
        if not diversity["meets_threshold"]:
            issues.append(
                f"Insufficient validator diversity: {diversity['unique_validators']} "
                f"of {diversity['required_validators']} required"
            )

        # Check weight caps
        for signal in signals:
            if signal.effective_weight > MAX_EFFECTIVE_WEIGHT:
                issues.append(
                    f"Validator {signal.validator_id} exceeds weight cap: "
                    f"{signal.effective_weight:.3f} > {MAX_EFFECTIVE_WEIGHT}"
                )

        # Check minority visibility
        if MINORITY_SIGNAL_VISIBILITY:
            minority = self.identify_minority_signals(signals)
            if minority:
                warnings.append(
                    f"{len(minority)} minority signals present (visible but not dominant)"
                )

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "diversity": diversity,
            "minority_count": len(self.identify_minority_signals(signals)),
        }

    # =========================================================================
    # Convenience Methods
    # =========================================================================

    def get_trust_summary(self, validator_id: str) -> dict[str, Any]:
        """Get a summary of a validator's trust status."""
        profile = self.profiles.get(validator_id)
        identity = self.identities.get(validator_id)

        if not profile or not identity:
            return {"error": f"Validator {validator_id} not found"}

        return {
            "validator_id": validator_id,
            "validator_type": identity.validator_type.value,
            "overall_score": profile.overall_score,
            "confidence_interval": profile.confidence_interval,
            "sample_size": profile.sample_size,
            "is_frozen": profile.is_frozen,
            "days_since_activity": (datetime.utcnow() - profile.last_activity).days,
            "scoped_scores": {
                scope.value: score.score for scope, score in profile.scoped_scores.items()
            },
            "base_weight": BASE_WEIGHTS.get(identity.validator_type.value, 1.0),
        }

    def list_validators(
        self,
        min_score: float | None = None,
        validator_type: ValidatorType | None = None,
        scope: TrustScope | None = None,
    ) -> list[dict[str, Any]]:
        """
        List validators matching criteria.

        Args:
            min_score: Minimum overall score
            validator_type: Filter by validator type
            scope: Filter by scope capability

        Returns:
            List of validator summaries
        """
        results = []

        for vid, profile in self.profiles.items():
            identity = self.identities.get(vid)
            if not identity:
                continue

            # Apply filters
            if min_score is not None and profile.overall_score < min_score:
                continue

            if validator_type is not None and identity.validator_type != validator_type:
                continue

            if scope is not None and scope not in profile.scoped_scores:
                continue

            results.append(self.get_trust_summary(vid))

        # Sort by overall score descending
        results.sort(key=lambda x: x.get("overall_score", 0), reverse=True)

        return results


# =============================================================================
# Module-level convenience functions
# =============================================================================

_default_manager: TrustManager | None = None


def get_trust_manager() -> TrustManager:
    """Get the default trust manager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = TrustManager()
    return _default_manager


def reset_trust_manager() -> None:
    """Reset the default trust manager (useful for testing)."""
    global _default_manager
    _default_manager = None


def calculate_weighted_consensus(
    signals: list[WeightedSignal], aggregation: str = "weighted_average"
) -> dict[str, Any]:
    """
    Calculate weighted consensus from validator signals.

    Per Section 7:
    - Low-trust validators cannot dominate
    - High-trust validators cannot finalize alone

    Args:
        signals: List of weighted signals
        aggregation: Aggregation method ("weighted_average" or "majority")

    Returns:
        Consensus result
    """
    if not signals:
        return {"consensus": None, "error": "No signals provided"}

    total_weight = sum(s.effective_weight for s in signals)
    if total_weight == 0:
        return {"consensus": None, "error": "Total weight is zero"}

    # Check diversity
    manager = get_trust_manager()
    validation = manager.validate_consensus_input(
        signals,
        TrustScope.SEMANTIC_PARSING,  # Default scope
    )

    if not validation["valid"]:
        return {"consensus": None, "error": "Validation failed", "issues": validation["issues"]}

    # For now, just return the weighted signals summary
    # Actual aggregation depends on signal type
    return {
        "consensus": "calculated",
        "total_weight": total_weight,
        "signal_count": len(signals),
        "validation": validation,
        "weights": [
            {
                "validator_id": s.validator_id,
                "effective_weight": s.effective_weight,
                "normalized_weight": s.effective_weight / total_weight,
            }
            for s in signals
        ],
    }


def get_ncip_007_config() -> dict[str, Any]:
    """Get NCIP-007 configuration."""
    return {
        "version": "1.0",
        "base_weights": BASE_WEIGHTS,
        "max_effective_weight": MAX_EFFECTIVE_WEIGHT,
        "decay": {"lambda": DECAY_LAMBDA, "inactivity_threshold_days": INACTIVITY_THRESHOLD_DAYS},
        "safeguards": {
            "min_validator_diversity": MIN_VALIDATOR_DIVERSITY,
            "enforce_weight_cap": True,
            "minority_signal_visibility": MINORITY_SIGNAL_VISIBILITY,
        },
    }

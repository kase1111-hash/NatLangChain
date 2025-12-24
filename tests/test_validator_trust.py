"""
Tests for NCIP-007: Validator Trust Scoring & Reliability Weighting

Tests cover:
- Validator registration and identity management
- Trust profile creation and management
- Positive and negative signal recording
- Temporal decay and recovery
- Weighting function calculation
- Dispute freeze/unfreeze
- Anti-centralization safeguards
- Consensus integration
"""

import pytest
from datetime import datetime, timedelta
import math
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validator_trust import (
    # Enums
    ValidatorType,
    TrustScope,
    TrustSignalType,
    PositiveSignal,
    NegativeSignal,
    # Data classes
    ValidatorIdentity,
    ScopedScore,
    TrustEvent,
    TrustProfile,
    WeightedSignal,
    # Manager
    TrustManager,
    # Constants
    BASE_WEIGHTS,
    MAX_EFFECTIVE_WEIGHT,
    DECAY_LAMBDA,
    INACTIVITY_THRESHOLD_DAYS,
    MIN_VALIDATOR_DIVERSITY,
    # Functions
    get_trust_manager,
    reset_trust_manager,
    calculate_weighted_consensus,
    get_ncip_007_config,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def trust_manager():
    """Create a fresh trust manager for each test."""
    return TrustManager()


@pytest.fixture
def registered_validators(trust_manager):
    """Register a set of validators for testing."""
    validators = []

    # LLM validator
    trust_manager.register_validator(
        validator_id="vld-001",
        validator_type=ValidatorType.LLM,
        model_version="claude-3-opus",
        declared_capabilities=[
            TrustScope.SEMANTIC_PARSING,
            TrustScope.PROOF_OF_UNDERSTANDING
        ]
    )
    validators.append("vld-001")

    # Hybrid validator
    trust_manager.register_validator(
        validator_id="vld-002",
        validator_type=ValidatorType.HYBRID,
        model_version="hybrid-v2",
        declared_capabilities=[
            TrustScope.DRIFT_DETECTION,
            TrustScope.DISPUTE_ANALYSIS
        ]
    )
    validators.append("vld-002")

    # Symbolic validator
    trust_manager.register_validator(
        validator_id="vld-003",
        validator_type=ValidatorType.SYMBOLIC,
        declared_capabilities=[TrustScope.SEMANTIC_PARSING]
    )
    validators.append("vld-003")

    # Human validator
    trust_manager.register_validator(
        validator_id="vld-004",
        validator_type=ValidatorType.HUMAN,
        operator_id="operator-001",
        declared_capabilities=[
            TrustScope.DISPUTE_ANALYSIS,
            TrustScope.LEGAL_TRANSLATION_REVIEW
        ]
    )
    validators.append("vld-004")

    return validators


# =============================================================================
# Validator Registration Tests
# =============================================================================

class TestValidatorRegistration:
    """Tests for validator registration and identity management."""

    def test_register_llm_validator(self, trust_manager):
        """Test registering an LLM validator."""
        profile = trust_manager.register_validator(
            validator_id="vld-llm",
            validator_type=ValidatorType.LLM,
            model_version="claude-3-5-sonnet"
        )

        assert profile.validator_id == "vld-llm"
        assert profile.overall_score == 0.5  # Neutral starting score
        assert profile.sample_size == 0

        identity = trust_manager.get_identity("vld-llm")
        assert identity.validator_type == ValidatorType.LLM
        assert identity.model_version == "claude-3-5-sonnet"

    def test_register_human_validator(self, trust_manager):
        """Test registering a human validator."""
        profile = trust_manager.register_validator(
            validator_id="vld-human",
            validator_type=ValidatorType.HUMAN,
            operator_id="john_doe"
        )

        identity = trust_manager.get_identity("vld-human")
        assert identity.validator_type == ValidatorType.HUMAN
        assert identity.operator_id == "john_doe"

    def test_register_with_capabilities(self, trust_manager):
        """Test registering with declared capabilities."""
        capabilities = [
            TrustScope.SEMANTIC_PARSING,
            TrustScope.DRIFT_DETECTION
        ]

        profile = trust_manager.register_validator(
            validator_id="vld-cap",
            validator_type=ValidatorType.HYBRID,
            declared_capabilities=capabilities
        )

        # Should have scoped scores initialized
        assert TrustScope.SEMANTIC_PARSING in profile.scoped_scores
        assert TrustScope.DRIFT_DETECTION in profile.scoped_scores
        assert profile.scoped_scores[TrustScope.SEMANTIC_PARSING].score == 0.5

    def test_duplicate_registration_fails(self, trust_manager):
        """Test that duplicate registration raises error."""
        trust_manager.register_validator(
            validator_id="vld-dup",
            validator_type=ValidatorType.LLM
        )

        with pytest.raises(ValueError, match="already registered"):
            trust_manager.register_validator(
                validator_id="vld-dup",
                validator_type=ValidatorType.LLM
            )

    def test_get_nonexistent_profile(self, trust_manager):
        """Test getting a profile that doesn't exist."""
        profile = trust_manager.get_profile("nonexistent")
        assert profile is None

    def test_identity_to_dict(self, trust_manager):
        """Test identity serialization."""
        trust_manager.register_validator(
            validator_id="vld-ser",
            validator_type=ValidatorType.HYBRID,
            model_version="v1.0",
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        identity = trust_manager.get_identity("vld-ser")
        data = identity.to_dict()

        assert data["validator_id"] == "vld-ser"
        assert data["validator_type"] == "hybrid"
        assert data["model_version"] == "v1.0"
        assert "semantic_parsing" in data["declared_capabilities"]


# =============================================================================
# Trust Score Update Tests
# =============================================================================

class TestTrustScoreUpdates:
    """Tests for trust score recording and updates."""

    def test_record_positive_signal(self, trust_manager):
        """Test recording a positive trust signal."""
        trust_manager.register_validator(
            validator_id="vld-pos",
            validator_type=ValidatorType.LLM
        )

        event = trust_manager.record_positive_signal(
            validator_id="vld-pos",
            signal=PositiveSignal.CONSENSUS_MATCH,
            scope=TrustScope.SEMANTIC_PARSING,
            magnitude=0.1
        )

        assert event is not None
        assert event.signal_type == TrustSignalType.POSITIVE
        assert event.signal == "consensus_match"
        assert event.magnitude == 0.1

        profile = trust_manager.get_profile("vld-pos")
        assert profile.scoped_scores[TrustScope.SEMANTIC_PARSING].score == 0.6
        assert profile.sample_size == 1

    def test_record_negative_signal(self, trust_manager):
        """Test recording a negative trust signal."""
        trust_manager.register_validator(
            validator_id="vld-neg",
            validator_type=ValidatorType.LLM
        )

        event = trust_manager.record_negative_signal(
            validator_id="vld-neg",
            signal=NegativeSignal.FALSE_POSITIVE_DRIFT,
            scope=TrustScope.DRIFT_DETECTION,
            magnitude=0.1
        )

        assert event is not None
        assert event.signal_type == TrustSignalType.NEGATIVE

        profile = trust_manager.get_profile("vld-neg")
        assert profile.scoped_scores[TrustScope.DRIFT_DETECTION].score == 0.4

    def test_harassment_accelerated_decay(self, trust_manager):
        """Test that harassment signals have accelerated decay."""
        trust_manager.register_validator(
            validator_id="vld-harass",
            validator_type=ValidatorType.LLM
        )

        # Standard negative signal
        trust_manager.record_negative_signal(
            validator_id="vld-harass",
            signal=NegativeSignal.FALSE_POSITIVE_DRIFT,
            scope=TrustScope.DRIFT_DETECTION,
            magnitude=0.05
        )

        profile1 = trust_manager.get_profile("vld-harass")
        score_after_normal = profile1.scoped_scores[TrustScope.DRIFT_DETECTION].score

        # Harassment signal (2x magnitude)
        trust_manager.record_negative_signal(
            validator_id="vld-harass",
            signal=NegativeSignal.HARASSMENT_PATTERN,
            scope=TrustScope.DRIFT_DETECTION,
            magnitude=0.05  # Will be doubled to 0.10
        )

        profile2 = trust_manager.get_profile("vld-harass")
        score_after_harass = profile2.scoped_scores[TrustScope.DRIFT_DETECTION].score

        # Harassment caused larger decrease
        expected_after_harass = score_after_normal - 0.10
        assert abs(score_after_harass - expected_after_harass) < 0.001

    def test_score_bounded_at_one(self, trust_manager):
        """Test that scores are capped at 1.0."""
        trust_manager.register_validator(
            validator_id="vld-max",
            validator_type=ValidatorType.LLM,
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        # Start at 0.5, add 0.6 should cap at 1.0
        for _ in range(10):
            trust_manager.record_positive_signal(
                validator_id="vld-max",
                signal=PositiveSignal.CONSENSUS_MATCH,
                scope=TrustScope.SEMANTIC_PARSING,
                magnitude=0.1
            )

        profile = trust_manager.get_profile("vld-max")
        assert profile.scoped_scores[TrustScope.SEMANTIC_PARSING].score <= 1.0

    def test_score_bounded_at_zero(self, trust_manager):
        """Test that scores are floored at 0.0."""
        trust_manager.register_validator(
            validator_id="vld-min",
            validator_type=ValidatorType.LLM,
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        # Start at 0.5, subtract 0.6 should floor at 0.0
        for _ in range(10):
            trust_manager.record_negative_signal(
                validator_id="vld-min",
                signal=NegativeSignal.FALSE_POSITIVE_DRIFT,
                scope=TrustScope.SEMANTIC_PARSING,
                magnitude=0.1
            )

        profile = trust_manager.get_profile("vld-min")
        assert profile.scoped_scores[TrustScope.SEMANTIC_PARSING].score >= 0.0

    def test_frozen_validator_rejects_signals(self, trust_manager):
        """Test that frozen validators reject trust updates."""
        trust_manager.register_validator(
            validator_id="vld-frozen",
            validator_type=ValidatorType.LLM
        )

        # Freeze the validator
        trust_manager.freeze_trust("vld-frozen", "dispute-001")

        # Attempt to record signal
        event = trust_manager.record_positive_signal(
            validator_id="vld-frozen",
            signal=PositiveSignal.CONSENSUS_MATCH,
            scope=TrustScope.SEMANTIC_PARSING
        )

        assert event is None

    def test_overall_score_recalculation(self, trust_manager):
        """Test that overall score is recalculated correctly."""
        trust_manager.register_validator(
            validator_id="vld-overall",
            validator_type=ValidatorType.LLM
        )

        # Add signals to different scopes
        trust_manager.record_positive_signal(
            validator_id="vld-overall",
            signal=PositiveSignal.CONSENSUS_MATCH,
            scope=TrustScope.SEMANTIC_PARSING,
            magnitude=0.3
        )

        trust_manager.record_negative_signal(
            validator_id="vld-overall",
            signal=NegativeSignal.FALSE_POSITIVE_DRIFT,
            scope=TrustScope.DRIFT_DETECTION,
            magnitude=0.2
        )

        profile = trust_manager.get_profile("vld-overall")

        # Overall should be weighted average
        assert 0.3 < profile.overall_score < 0.8

    def test_confidence_interval_shrinks(self, trust_manager):
        """Test that confidence interval shrinks with more samples."""
        trust_manager.register_validator(
            validator_id="vld-conf",
            validator_type=ValidatorType.LLM
        )

        initial_ci = trust_manager.get_profile("vld-conf").confidence_interval

        # Add many signals
        for _ in range(100):
            trust_manager.record_positive_signal(
                validator_id="vld-conf",
                signal=PositiveSignal.CONSISTENCY,
                scope=TrustScope.SEMANTIC_PARSING,
                magnitude=0.001
            )

        final_ci = trust_manager.get_profile("vld-conf").confidence_interval

        assert final_ci < initial_ci


# =============================================================================
# Temporal Decay Tests
# =============================================================================

class TestTemporalDecay:
    """Tests for trust decay over time."""

    def test_no_decay_within_threshold(self, trust_manager):
        """Test that no decay occurs within inactivity threshold."""
        trust_manager.register_validator(
            validator_id="vld-recent",
            validator_type=ValidatorType.LLM
        )

        # Set activity to 20 days ago (within threshold)
        profile = trust_manager.get_profile("vld-recent")
        profile.last_activity = datetime.utcnow() - timedelta(days=20)
        profile.overall_score = 0.8

        trust_manager.apply_temporal_decay("vld-recent")

        assert trust_manager.get_profile("vld-recent").overall_score == 0.8

    def test_decay_after_threshold(self, trust_manager):
        """Test that decay occurs after inactivity threshold."""
        trust_manager.register_validator(
            validator_id="vld-old",
            validator_type=ValidatorType.LLM
        )

        # Set activity to 60 days ago (beyond threshold)
        profile = trust_manager.get_profile("vld-old")
        profile.last_activity = datetime.utcnow() - timedelta(days=60)
        profile.overall_score = 0.8

        trust_manager.apply_temporal_decay("vld-old")

        # Score should have decayed
        assert trust_manager.get_profile("vld-old").overall_score < 0.8

    def test_decay_formula(self, trust_manager):
        """Test that decay follows exponential formula."""
        trust_manager.register_validator(
            validator_id="vld-formula",
            validator_type=ValidatorType.LLM
        )

        initial_score = 0.8
        days_inactive = 60
        days_past_threshold = days_inactive - INACTIVITY_THRESHOLD_DAYS

        profile = trust_manager.get_profile("vld-formula")
        profile.last_activity = datetime.utcnow() - timedelta(days=days_inactive)
        profile.overall_score = initial_score

        trust_manager.apply_temporal_decay("vld-formula")

        expected_score = initial_score * math.exp(-DECAY_LAMBDA * days_past_threshold)
        actual_score = trust_manager.get_profile("vld-formula").overall_score

        assert abs(actual_score - expected_score) < 0.001

    def test_frozen_validator_no_decay(self, trust_manager):
        """Test that frozen validators don't decay."""
        trust_manager.register_validator(
            validator_id="vld-freeze-decay",
            validator_type=ValidatorType.LLM
        )

        profile = trust_manager.get_profile("vld-freeze-decay")
        profile.last_activity = datetime.utcnow() - timedelta(days=60)
        profile.overall_score = 0.8

        trust_manager.freeze_trust("vld-freeze-decay", "dispute-001")
        trust_manager.apply_temporal_decay("vld-freeze-decay")

        assert trust_manager.get_profile("vld-freeze-decay").overall_score == 0.8

    def test_apply_decay_to_all(self, trust_manager, registered_validators):
        """Test applying decay to all validators."""
        # Set all validators to inactive
        for vid in registered_validators:
            profile = trust_manager.get_profile(vid)
            profile.last_activity = datetime.utcnow() - timedelta(days=60)
            profile.overall_score = 0.7

        decayed = trust_manager.apply_decay_to_all()

        assert len(decayed) == len(registered_validators)
        for vid in registered_validators:
            assert trust_manager.get_profile(vid).overall_score < 0.7


# =============================================================================
# Recovery Tests
# =============================================================================

class TestTrustRecovery:
    """Tests for trust recovery mechanisms."""

    def test_initiate_low_stakes_recovery(self, trust_manager):
        """Test initiating low-stakes validation recovery."""
        trust_manager.register_validator(
            validator_id="vld-recover",
            validator_type=ValidatorType.LLM
        )

        # Lower the score
        profile = trust_manager.get_profile("vld-recover")
        profile.overall_score = 0.3

        result = trust_manager.initiate_recovery(
            "vld-recover",
            "low_stakes_validation"
        )

        assert result["status"] == "initiated"
        assert result["recovery_type"] == "low_stakes_validation"
        assert "required_validations" in result["requirements"]

    def test_initiate_benchmark_recovery(self, trust_manager):
        """Test initiating benchmark challenge recovery."""
        trust_manager.register_validator(
            validator_id="vld-benchmark",
            validator_type=ValidatorType.LLM
        )

        result = trust_manager.initiate_recovery(
            "vld-benchmark",
            "benchmark_challenge"
        )

        assert result["status"] == "initiated"
        assert "required_challenges" in result["requirements"]

    def test_recovery_fails_when_frozen(self, trust_manager):
        """Test that recovery cannot start when frozen."""
        trust_manager.register_validator(
            validator_id="vld-frozen-recover",
            validator_type=ValidatorType.LLM
        )

        trust_manager.freeze_trust("vld-frozen-recover", "dispute-001")

        result = trust_manager.initiate_recovery("vld-frozen-recover")

        assert result["status"] == "error"
        assert "frozen" in result["message"]

    def test_recovery_unknown_validator(self, trust_manager):
        """Test recovery for non-existent validator."""
        result = trust_manager.initiate_recovery("nonexistent")

        assert result["status"] == "error"
        assert "not found" in result["message"]


# =============================================================================
# Weighting Function Tests
# =============================================================================

class TestWeightingFunction:
    """Tests for effective weight calculation."""

    def test_base_weights_by_type(self, trust_manager):
        """Test that base weights vary by validator type."""
        for vtype, expected_weight in [
            (ValidatorType.LLM, 1.0),
            (ValidatorType.HYBRID, 1.1),
            (ValidatorType.SYMBOLIC, 0.9),
            (ValidatorType.HUMAN, 1.2)
        ]:
            trust_manager.register_validator(
                validator_id=f"vld-{vtype.value}",
                validator_type=vtype
            )

            identity = trust_manager.get_identity(f"vld-{vtype.value}")
            assert BASE_WEIGHTS[identity.validator_type.value] == expected_weight

    def test_effective_weight_formula(self, trust_manager):
        """Test effective_weight = base_weight * trust_score * scope_modifier."""
        trust_manager.register_validator(
            validator_id="vld-weight",
            validator_type=ValidatorType.HYBRID,  # base_weight = 1.1
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        # Set known trust score
        profile = trust_manager.get_profile("vld-weight")
        profile.scoped_scores[TrustScope.SEMANTIC_PARSING].score = 0.8

        scope_modifier = 0.9
        expected = 1.1 * 0.8 * 0.9  # = 0.792

        actual = trust_manager.calculate_effective_weight(
            "vld-weight",
            TrustScope.SEMANTIC_PARSING,
            scope_modifier
        )

        assert abs(actual - expected) < 0.001

    def test_weight_capped_at_max(self, trust_manager):
        """Test that weight is capped at MAX_EFFECTIVE_WEIGHT."""
        trust_manager.register_validator(
            validator_id="vld-cap",
            validator_type=ValidatorType.HUMAN,  # base_weight = 1.2
            declared_capabilities=[TrustScope.DISPUTE_ANALYSIS]
        )

        # Set high trust score
        profile = trust_manager.get_profile("vld-cap")
        profile.scoped_scores[TrustScope.DISPUTE_ANALYSIS].score = 1.0

        # Without cap: 1.2 * 1.0 * 1.0 = 1.2
        actual = trust_manager.calculate_effective_weight(
            "vld-cap",
            TrustScope.DISPUTE_ANALYSIS,
            1.0
        )

        assert actual == MAX_EFFECTIVE_WEIGHT

    def test_weighted_signal_creation(self, trust_manager):
        """Test creating a weighted signal."""
        trust_manager.register_validator(
            validator_id="vld-signal",
            validator_type=ValidatorType.LLM
        )

        signal = trust_manager.get_weighted_signal(
            "vld-signal",
            signal_value={"decision": "VALID"},
            scope=TrustScope.SEMANTIC_PARSING,
            scope_modifier=1.0
        )

        assert signal is not None
        assert signal.validator_id == "vld-signal"
        assert signal.signal_value == {"decision": "VALID"}
        assert signal.raw_weight == 1.0
        assert signal.effective_weight > 0

    def test_unknown_validator_zero_weight(self, trust_manager):
        """Test that unknown validator gets zero weight."""
        weight = trust_manager.calculate_effective_weight(
            "nonexistent",
            TrustScope.SEMANTIC_PARSING
        )

        assert weight == 0.0


# =============================================================================
# Dispute Handling Tests
# =============================================================================

class TestDisputeHandling:
    """Tests for trust freeze/unfreeze during disputes."""

    def test_freeze_trust(self, trust_manager):
        """Test freezing a validator's trust."""
        trust_manager.register_validator(
            validator_id="vld-freeze",
            validator_type=ValidatorType.LLM
        )

        success = trust_manager.freeze_trust("vld-freeze", "dispute-123")

        assert success
        profile = trust_manager.get_profile("vld-freeze")
        assert profile.is_frozen
        assert profile.freeze_reason == "dispute:dispute-123"

    def test_unfreeze_trust(self, trust_manager):
        """Test unfreezing a validator's trust."""
        trust_manager.register_validator(
            validator_id="vld-unfreeze",
            validator_type=ValidatorType.LLM
        )

        trust_manager.freeze_trust("vld-unfreeze", "dispute-123")
        success = trust_manager.unfreeze_trust("vld-unfreeze")

        assert success
        profile = trust_manager.get_profile("vld-unfreeze")
        assert not profile.is_frozen
        assert profile.freeze_reason is None

    def test_unfreeze_with_positive_outcome(self, trust_manager):
        """Test unfreezing with positive dispute outcome."""
        trust_manager.register_validator(
            validator_id="vld-outcome-pos",
            validator_type=ValidatorType.LLM,
            declared_capabilities=[TrustScope.DISPUTE_ANALYSIS]
        )

        initial_score = trust_manager.get_profile("vld-outcome-pos").overall_score

        trust_manager.freeze_trust("vld-outcome-pos", "dispute-123")
        trust_manager.unfreeze_trust("vld-outcome-pos", {
            "outcome_type": "positive",
            "scope": TrustScope.DISPUTE_ANALYSIS,
            "magnitude": 0.1
        })

        final_score = trust_manager.get_profile("vld-outcome-pos").overall_score
        assert final_score > initial_score

    def test_unfreeze_with_negative_outcome(self, trust_manager):
        """Test unfreezing with negative dispute outcome."""
        trust_manager.register_validator(
            validator_id="vld-outcome-neg",
            validator_type=ValidatorType.LLM,
            declared_capabilities=[TrustScope.DISPUTE_ANALYSIS]
        )

        initial_score = trust_manager.get_profile("vld-outcome-neg").overall_score

        trust_manager.freeze_trust("vld-outcome-neg", "dispute-123")
        trust_manager.unfreeze_trust("vld-outcome-neg", {
            "outcome_type": "negative",
            "scope": TrustScope.DISPUTE_ANALYSIS,
            "magnitude": 0.1
        })

        final_score = trust_manager.get_profile("vld-outcome-neg").overall_score
        assert final_score < initial_score

    def test_freeze_all_for_dispute(self, trust_manager, registered_validators):
        """Test freezing all validators for a dispute."""
        frozen = trust_manager.freeze_all_for_dispute("dispute-456")

        assert len(frozen) == len(registered_validators)
        for vid in registered_validators:
            assert trust_manager.get_profile(vid).is_frozen


# =============================================================================
# Anti-Centralization Safeguards Tests
# =============================================================================

class TestAntiCentralization:
    """Tests for anti-centralization safeguards."""

    def test_diversity_threshold_met(self, trust_manager, registered_validators):
        """Test diversity threshold check when met."""
        result = trust_manager.check_diversity_threshold(registered_validators)

        assert result["meets_threshold"]
        assert result["unique_validators"] >= MIN_VALIDATOR_DIVERSITY
        assert result["unique_types"] == 4  # All 4 types

    def test_diversity_threshold_not_met(self, trust_manager):
        """Test diversity threshold check when not met."""
        trust_manager.register_validator(
            validator_id="vld-only1",
            validator_type=ValidatorType.LLM
        )
        trust_manager.register_validator(
            validator_id="vld-only2",
            validator_type=ValidatorType.LLM
        )

        result = trust_manager.check_diversity_threshold(["vld-only1", "vld-only2"])

        assert not result["meets_threshold"]
        assert result["unique_validators"] == 2
        assert result["required_validators"] == MIN_VALIDATOR_DIVERSITY

    def test_identify_minority_signals(self, trust_manager):
        """Test identifying minority signals."""
        trust_manager.register_validator(
            validator_id="vld-high",
            validator_type=ValidatorType.LLM
        )
        trust_manager.register_validator(
            validator_id="vld-low",
            validator_type=ValidatorType.LLM
        )

        # Set different trust scores
        trust_manager.get_profile("vld-high").overall_score = 0.8
        trust_manager.get_profile("vld-low").overall_score = 0.1

        signals = [
            WeightedSignal(
                validator_id="vld-high",
                signal_value="A",
                raw_weight=1.0,
                effective_weight=0.8,
                trust_score=0.8,
                scope_modifier=1.0
            ),
            WeightedSignal(
                validator_id="vld-low",
                signal_value="B",
                raw_weight=1.0,
                effective_weight=0.1,
                trust_score=0.1,
                scope_modifier=1.0
            )
        ]

        minority = trust_manager.identify_minority_signals(signals)

        assert len(minority) == 1
        assert minority[0].validator_id == "vld-low"
        assert minority[0].is_minority

    def test_validate_consensus_input_valid(self, trust_manager, registered_validators):
        """Test consensus input validation with valid input."""
        signals = []
        for vid in registered_validators:
            signal = trust_manager.get_weighted_signal(
                vid,
                signal_value="VALID",
                scope=TrustScope.SEMANTIC_PARSING
            )
            if signal:
                signals.append(signal)

        result = trust_manager.validate_consensus_input(
            signals,
            TrustScope.SEMANTIC_PARSING
        )

        assert result["valid"]
        assert len(result["issues"]) == 0

    def test_validate_consensus_input_insufficient_diversity(self, trust_manager):
        """Test consensus input validation with insufficient diversity."""
        trust_manager.register_validator(
            validator_id="vld-solo",
            validator_type=ValidatorType.LLM
        )

        signals = [
            trust_manager.get_weighted_signal(
                "vld-solo",
                signal_value="VALID",
                scope=TrustScope.SEMANTIC_PARSING
            )
        ]

        result = trust_manager.validate_consensus_input(
            signals,
            TrustScope.SEMANTIC_PARSING
        )

        assert not result["valid"]
        assert any("diversity" in issue.lower() for issue in result["issues"])


# =============================================================================
# Consensus Integration Tests
# =============================================================================

class TestConsensusIntegration:
    """Tests for weighted consensus calculation."""

    def test_calculate_weighted_consensus(self, trust_manager, registered_validators):
        """Test weighted consensus calculation."""
        signals = []
        for vid in registered_validators:
            signal = trust_manager.get_weighted_signal(
                vid,
                signal_value="VALID",
                scope=TrustScope.SEMANTIC_PARSING
            )
            if signal:
                signals.append(signal)

        # Reset and use default manager
        reset_trust_manager()

        result = calculate_weighted_consensus(signals)

        assert result["consensus"] == "calculated"
        assert result["signal_count"] == len(signals)
        assert result["total_weight"] > 0

    def test_consensus_empty_signals(self):
        """Test consensus with no signals."""
        reset_trust_manager()
        result = calculate_weighted_consensus([])

        assert result["consensus"] is None
        assert "No signals" in result["error"]


# =============================================================================
# Module Function Tests
# =============================================================================

class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_get_trust_manager_singleton(self):
        """Test that get_trust_manager returns singleton."""
        reset_trust_manager()

        manager1 = get_trust_manager()
        manager2 = get_trust_manager()

        assert manager1 is manager2

    def test_reset_trust_manager(self):
        """Test resetting the trust manager."""
        manager1 = get_trust_manager()
        manager1.register_validator(
            validator_id="vld-reset",
            validator_type=ValidatorType.LLM
        )

        reset_trust_manager()
        manager2 = get_trust_manager()

        assert manager2.get_profile("vld-reset") is None

    def test_get_ncip_007_config(self):
        """Test getting NCIP-007 configuration."""
        config = get_ncip_007_config()

        assert config["version"] == "1.0"
        assert config["base_weights"] == BASE_WEIGHTS
        assert config["max_effective_weight"] == MAX_EFFECTIVE_WEIGHT
        assert config["decay"]["lambda"] == DECAY_LAMBDA
        assert config["safeguards"]["min_validator_diversity"] == MIN_VALIDATOR_DIVERSITY


# =============================================================================
# Trust Summary and Listing Tests
# =============================================================================

class TestTrustSummary:
    """Tests for trust summary and validator listing."""

    def test_get_trust_summary(self, trust_manager):
        """Test getting a validator's trust summary."""
        trust_manager.register_validator(
            validator_id="vld-summary",
            validator_type=ValidatorType.HYBRID,
            model_version="v2.0",
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        summary = trust_manager.get_trust_summary("vld-summary")

        assert summary["validator_id"] == "vld-summary"
        assert summary["validator_type"] == "hybrid"
        assert summary["overall_score"] == 0.5
        assert summary["base_weight"] == 1.1
        assert not summary["is_frozen"]

    def test_get_trust_summary_unknown(self, trust_manager):
        """Test getting summary for unknown validator."""
        summary = trust_manager.get_trust_summary("nonexistent")

        assert "error" in summary

    def test_list_validators(self, trust_manager, registered_validators):
        """Test listing all validators."""
        validators = trust_manager.list_validators()

        assert len(validators) == len(registered_validators)

    def test_list_validators_by_score(self, trust_manager, registered_validators):
        """Test listing validators by minimum score."""
        # Set one validator's score high
        trust_manager.get_profile("vld-001").overall_score = 0.9

        validators = trust_manager.list_validators(min_score=0.8)

        assert len(validators) == 1
        assert validators[0]["validator_id"] == "vld-001"

    def test_list_validators_by_type(self, trust_manager, registered_validators):
        """Test listing validators by type."""
        validators = trust_manager.list_validators(
            validator_type=ValidatorType.HUMAN
        )

        assert len(validators) == 1
        assert validators[0]["validator_type"] == "human"


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Tests for data class serialization."""

    def test_trust_profile_to_dict(self, trust_manager):
        """Test trust profile serialization."""
        trust_manager.register_validator(
            validator_id="vld-ser",
            validator_type=ValidatorType.LLM,
            declared_capabilities=[TrustScope.SEMANTIC_PARSING]
        )

        profile = trust_manager.get_profile("vld-ser")
        data = profile.to_dict()

        assert data["validator_id"] == "vld-ser"
        assert data["version"] == "1.0"
        assert data["overall_score"] == 0.5
        assert "semantic_parsing" in data["scoped_scores"]
        assert data["is_frozen"] is False

    def test_trust_event_to_dict(self, trust_manager):
        """Test trust event serialization."""
        trust_manager.register_validator(
            validator_id="vld-event-ser",
            validator_type=ValidatorType.LLM
        )

        event = trust_manager.record_positive_signal(
            validator_id="vld-event-ser",
            signal=PositiveSignal.CONSENSUS_MATCH,
            scope=TrustScope.SEMANTIC_PARSING,
            metadata={"context": "test"}
        )

        data = event.to_dict()

        assert data["validator_id"] == "vld-event-ser"
        assert data["signal_type"] == "positive"
        assert data["signal"] == "consensus_match"
        assert data["metadata"]["context"] == "test"

    def test_scoped_score_to_dict(self):
        """Test scoped score serialization."""
        score = ScopedScore(
            scope=TrustScope.DRIFT_DETECTION,
            score=0.75,
            sample_size=42
        )

        data = score.to_dict()

        assert data["scope"] == "drift_detection"
        assert data["score"] == 0.75
        assert data["sample_size"] == 42


# =============================================================================
# Edge Cases
# =============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_signal_to_nonexistent_validator(self, trust_manager):
        """Test recording signal to nonexistent validator."""
        event = trust_manager.record_positive_signal(
            validator_id="nonexistent",
            signal=PositiveSignal.CONSENSUS_MATCH,
            scope=TrustScope.SEMANTIC_PARSING
        )

        assert event is None

    def test_freeze_nonexistent_validator(self, trust_manager):
        """Test freezing nonexistent validator."""
        success = trust_manager.freeze_trust("nonexistent", "dispute-001")

        assert not success

    def test_unfreeze_nonexistent_validator(self, trust_manager):
        """Test unfreezing nonexistent validator."""
        success = trust_manager.unfreeze_trust("nonexistent")

        assert not success

    def test_scoped_score_fallback_to_overall(self, trust_manager):
        """Test that scoped score falls back to overall if not set."""
        trust_manager.register_validator(
            validator_id="vld-fallback",
            validator_type=ValidatorType.LLM
        )

        profile = trust_manager.get_profile("vld-fallback")
        profile.overall_score = 0.7

        # Get score for scope that wasn't declared
        score = profile.get_scoped_score(TrustScope.LEGAL_TRANSLATION_REVIEW)

        assert score == 0.7

    def test_all_positive_signals_covered(self, trust_manager):
        """Test that all positive signal types work."""
        trust_manager.register_validator(
            validator_id="vld-all-pos",
            validator_type=ValidatorType.LLM
        )

        for signal in PositiveSignal:
            event = trust_manager.record_positive_signal(
                validator_id="vld-all-pos",
                signal=signal,
                scope=TrustScope.SEMANTIC_PARSING
            )
            assert event is not None

    def test_all_negative_signals_covered(self, trust_manager):
        """Test that all negative signal types work."""
        trust_manager.register_validator(
            validator_id="vld-all-neg",
            validator_type=ValidatorType.LLM
        )

        # Start with high score to allow all decreases
        trust_manager.get_profile("vld-all-neg").overall_score = 1.0

        for signal in NegativeSignal:
            event = trust_manager.record_negative_signal(
                validator_id="vld-all-neg",
                signal=signal,
                scope=TrustScope.SEMANTIC_PARSING,
                magnitude=0.05
            )
            assert event is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

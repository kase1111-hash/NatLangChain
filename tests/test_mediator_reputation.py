"""
Tests for NCIP-010: Mediator Reputation, Bonding & Slashing

Tests cover:
- Mediator registration and bonding
- Reputation score calculation
- Composite Trust Score (CTS)
- Slashing conditions and execution
- Cooldown periods
- Market dynamics and ranking
- Treasury management
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mediator_reputation import (
    # Enums
    SlashingOffense,
    CooldownReason,
    ProposalStatus,
    MediatorStatus,
    # Data classes
    ReputationScores,
    Bond,
    Cooldown,
    SlashingEvent,
    MediatorProfile,
    MediatorProposal,
    # Manager
    MediatorReputationManager,
    # Constants
    CTS_WEIGHTS,
    SLASHING_RATES,
    COOLDOWN_DURATIONS,
    MINIMUM_BOND,
    DEFAULT_BOND,
    # Functions
    get_reputation_manager,
    reset_reputation_manager,
    get_ncip_010_config,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def manager():
    """Create a fresh reputation manager for each test."""
    return MediatorReputationManager()


@pytest.fixture
def registered_mediators(manager):
    """Register a set of mediators for testing."""
    mediators = []

    manager.register_mediator(
        mediator_id="med-001",
        stake_amount=50000,
        supported_domains=["software", "licensing"],
        models_used=["claude"]
    )
    mediators.append("med-001")

    manager.register_mediator(
        mediator_id="med-002",
        stake_amount=75000,
        supported_domains=["employment"],
        models_used=["gpt-4", "claude"]
    )
    mediators.append("med-002")

    manager.register_mediator(
        mediator_id="med-003",
        stake_amount=30000,
        supported_domains=["real-estate"]
    )
    mediators.append("med-003")

    return mediators


# =============================================================================
# Registration & Bonding Tests
# =============================================================================

class TestMediatorRegistration:
    """Tests for mediator registration and bonding."""

    def test_register_mediator(self, manager):
        """Test registering a new mediator."""
        profile = manager.register_mediator(
            mediator_id="med-test",
            stake_amount=50000,
            supported_domains=["software"],
            models_used=["claude"]
        )

        assert profile.mediator_id == "med-test"
        assert profile.bond.amount == 50000
        assert profile.status == MediatorStatus.ACTIVE
        assert "software" in profile.supported_domains

    def test_register_with_minimum_bond(self, manager):
        """Test registering with minimum bond amount."""
        profile = manager.register_mediator(
            mediator_id="med-min",
            stake_amount=MINIMUM_BOND
        )

        assert profile.bond.amount == MINIMUM_BOND
        assert manager.is_bonded("med-min")

    def test_register_below_minimum_fails(self, manager):
        """Test that registration below minimum bond fails."""
        with pytest.raises(ValueError, match="below minimum"):
            manager.register_mediator(
                mediator_id="med-low",
                stake_amount=MINIMUM_BOND - 1
            )

    def test_duplicate_registration_fails(self, manager):
        """Test that duplicate registration fails."""
        manager.register_mediator(mediator_id="med-dup", stake_amount=50000)

        with pytest.raises(ValueError, match="already registered"):
            manager.register_mediator(mediator_id="med-dup", stake_amount=50000)

    def test_is_bonded(self, manager):
        """Test is_bonded check."""
        manager.register_mediator(mediator_id="med-bonded", stake_amount=50000)

        assert manager.is_bonded("med-bonded")
        assert not manager.is_bonded("nonexistent")

    def test_can_submit_proposals_active(self, manager):
        """Test that active mediator can submit proposals."""
        manager.register_mediator(mediator_id="med-active", stake_amount=50000)

        can_submit, reason = manager.can_submit_proposals("med-active")
        assert can_submit
        assert reason == "OK"

    def test_can_submit_proposals_unbonded(self, manager):
        """Test that unbonded mediator cannot submit proposals."""
        can_submit, reason = manager.can_submit_proposals("nonexistent")
        assert not can_submit
        assert "not registered" in reason.lower()


# =============================================================================
# Reputation Score Tests
# =============================================================================

class TestReputationScores:
    """Tests for reputation score calculation."""

    def test_initial_scores(self, manager):
        """Test that initial scores are neutral."""
        profile = manager.register_mediator(mediator_id="med-init", stake_amount=50000)

        scores = profile.scores
        assert scores.acceptance_rate == 0.5
        assert scores.semantic_accuracy == 0.5
        assert scores.appeal_survival == 1.0
        assert scores.dispute_avoidance == 1.0
        assert scores.coercion_signal == 0.0
        assert scores.latency_discipline == 1.0

    def test_update_single_dimension(self, manager):
        """Test updating a single reputation dimension."""
        manager.register_mediator(mediator_id="med-update", stake_amount=50000)

        new_cts = manager.update_reputation("med-update", "acceptance_rate", 0.9)

        assert new_cts is not None
        profile = manager.get_mediator("med-update")
        assert profile.scores.acceptance_rate == 0.9

    def test_score_clamped_to_bounds(self, manager):
        """Test that scores are clamped to [0, 1]."""
        manager.register_mediator(mediator_id="med-clamp", stake_amount=50000)

        manager.update_reputation("med-clamp", "acceptance_rate", 1.5)
        profile = manager.get_mediator("med-clamp")
        assert profile.scores.acceptance_rate == 1.0

        manager.update_reputation("med-clamp", "semantic_accuracy", -0.5)
        assert manager.get_mediator("med-clamp").scores.semantic_accuracy == 0.0

    def test_record_proposal_outcome_accepted(self, manager):
        """Test recording an accepted proposal outcome."""
        manager.register_mediator(mediator_id="med-outcome", stake_amount=50000)

        result = manager.record_proposal_outcome(
            mediator_id="med-outcome",
            accepted=True,
            semantic_drift_score=0.1,
            latency_seconds=30
        )

        assert result["mediator_id"] == "med-outcome"
        assert result["new_cts"] > 0
        profile = manager.get_mediator("med-outcome")
        assert profile.accepted_count == 1
        assert profile.proposal_count == 1

    def test_record_proposal_outcome_rejected(self, manager):
        """Test recording a rejected proposal outcome."""
        manager.register_mediator(mediator_id="med-rejected", stake_amount=50000)

        manager.record_proposal_outcome(
            mediator_id="med-rejected",
            accepted=False
        )

        profile = manager.get_mediator("med-rejected")
        assert profile.rejected_count == 1

    def test_coercion_detection_penalty(self, manager):
        """Test that coercion detection increases penalty."""
        manager.register_mediator(mediator_id="med-coerce", stake_amount=50000)

        initial_cs = manager.get_mediator("med-coerce").scores.coercion_signal

        manager.record_proposal_outcome(
            mediator_id="med-coerce",
            accepted=True,
            coercion_detected=True
        )

        final_cs = manager.get_mediator("med-coerce").scores.coercion_signal
        assert final_cs > initial_cs

    def test_appeal_outcome_survived(self, manager):
        """Test recording a survived appeal."""
        manager.register_mediator(mediator_id="med-appeal", stake_amount=50000)

        result = manager.record_appeal_outcome("med-appeal", appeal_survived=True)

        profile = manager.get_mediator("med-appeal")
        assert profile.appeal_count == 1
        assert profile.appeal_losses == 0
        assert profile.scores.appeal_survival == 1.0

    def test_appeal_outcome_lost(self, manager):
        """Test recording a lost appeal."""
        manager.register_mediator(mediator_id="med-lost", stake_amount=50000)

        result = manager.record_appeal_outcome("med-lost", appeal_survived=False)

        profile = manager.get_mediator("med-lost")
        assert profile.appeal_losses == 1
        assert profile.scores.appeal_survival == 0.0

    def test_downstream_dispute_affects_score(self, manager):
        """Test that downstream disputes affect reputation."""
        manager.register_mediator(mediator_id="med-dispute", stake_amount=50000)

        initial_da = manager.get_mediator("med-dispute").scores.dispute_avoidance

        manager.record_downstream_dispute("med-dispute", dispute_occurred=True)

        final_da = manager.get_mediator("med-dispute").scores.dispute_avoidance
        assert final_da < initial_da


# =============================================================================
# Composite Trust Score Tests
# =============================================================================

class TestCompositeTrustScore:
    """Tests for CTS calculation."""

    def test_initial_cts(self, manager):
        """Test initial CTS calculation."""
        profile = manager.register_mediator(mediator_id="med-cts", stake_amount=50000)

        # Initial CTS should be positive with neutral/good starting scores
        assert profile.composite_trust_score > 0

    def test_cts_increases_with_good_scores(self, manager):
        """Test that CTS increases with good scores."""
        manager.register_mediator(mediator_id="med-good", stake_amount=50000)

        initial_cts = manager.get_mediator("med-good").composite_trust_score

        # Improve all positive dimensions
        manager.update_reputation("med-good", "acceptance_rate", 0.95)
        manager.update_reputation("med-good", "semantic_accuracy", 0.95)
        manager.update_reputation("med-good", "appeal_survival", 0.95)
        manager.update_reputation("med-good", "dispute_avoidance", 0.95)

        final_cts = manager.get_mediator("med-good").composite_trust_score
        assert final_cts > initial_cts

    def test_cts_decreases_with_coercion(self, manager):
        """Test that CTS decreases with coercion signal."""
        manager.register_mediator(mediator_id="med-coerce-cts", stake_amount=50000)

        initial_cts = manager.get_mediator("med-coerce-cts").composite_trust_score

        manager.update_reputation("med-coerce-cts", "coercion_signal", 0.5)

        final_cts = manager.get_mediator("med-coerce-cts").composite_trust_score
        assert final_cts < initial_cts

    def test_cts_clamped_to_zero_one(self, manager):
        """Test that CTS is clamped to [0, 1]."""
        manager.register_mediator(mediator_id="med-clamp-cts", stake_amount=50000)

        profile = manager.get_mediator("med-clamp-cts")
        assert 0 <= profile.composite_trust_score <= 1


# =============================================================================
# Slashing Tests
# =============================================================================

class TestSlashing:
    """Tests for slashing conditions and execution."""

    def test_slash_semantic_manipulation(self, manager):
        """Test slashing for semantic manipulation."""
        manager.register_mediator(mediator_id="med-slash", stake_amount=50000)

        event = manager.slash(
            mediator_id="med-slash",
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=0.5,
            evidence={"drift_level": "D4"}
        )

        assert event is not None
        assert event.offense == SlashingOffense.SEMANTIC_MANIPULATION
        assert event.amount_slashed > 0

        profile = manager.get_mediator("med-slash")
        assert profile.bond.amount < 50000
        assert profile.total_slashed > 0

    def test_slash_percentage_by_severity(self, manager):
        """Test that slash percentage scales with severity."""
        manager.register_mediator(mediator_id="med-sev-low", stake_amount=50000)
        manager.register_mediator(mediator_id="med-sev-high", stake_amount=50000)

        event_low = manager.slash(
            mediator_id="med-sev-low",
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=0.0
        )

        event_high = manager.slash(
            mediator_id="med-sev-high",
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=1.0
        )

        assert event_high.percentage > event_low.percentage

    def test_slash_creates_cooldown(self, manager):
        """Test that slashing creates a cooldown."""
        manager.register_mediator(mediator_id="med-cooldown", stake_amount=50000)

        manager.slash(
            mediator_id="med-cooldown",
            offense=SlashingOffense.APPEAL_REVERSAL,
            severity=0.5
        )

        profile = manager.get_mediator("med-cooldown")
        assert len(profile.active_cooldowns) > 0
        assert profile.status == MediatorStatus.COOLDOWN

    def test_slash_to_treasury(self, manager):
        """Test that slashed funds go to treasury."""
        manager.register_mediator(mediator_id="med-treasury", stake_amount=50000)

        initial_treasury = manager.get_treasury_balance()

        manager.slash(
            mediator_id="med-treasury",
            offense=SlashingOffense.COERCIVE_FRAMING,
            severity=0.5
        )

        final_treasury = manager.get_treasury_balance()
        assert final_treasury > initial_treasury

    def test_slash_with_affected_party(self, manager):
        """Test slashing with affected party compensation."""
        manager.register_mediator(mediator_id="med-affected", stake_amount=50000)

        event = manager.slash(
            mediator_id="med-affected",
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=0.5,
            affected_party_id="victim-001"
        )

        # 50% goes to affected party, 50% to treasury
        assert event.affected_party_portion > 0
        assert event.treasury_portion > 0
        assert abs(event.affected_party_portion - event.treasury_portion) < 0.01

    def test_slash_below_minimum_unbonds(self, manager):
        """Test that slashing below minimum unbonds the mediator."""
        manager.register_mediator(mediator_id="med-unbond", stake_amount=15000)

        # Slash heavily
        manager.slash(
            mediator_id="med-unbond",
            offense=SlashingOffense.COLLUSION_SIGNALS,
            severity=1.0  # Max severity
        )

        profile = manager.get_mediator("med-unbond")
        if profile.bond.amount < MINIMUM_BOND:
            assert profile.status == MediatorStatus.UNBONDED

    def test_check_repeated_invalid_proposals(self, manager):
        """Test checking for repeated invalid proposals."""
        manager.register_mediator(mediator_id="med-repeat", stake_amount=50000)

        # Add rejected proposals
        for i in range(3):
            proposal = MediatorProposal(
                proposal_id=f"prop-{i}",
                mediator_id="med-repeat",
                contract_id="contract-001",
                content="test",
                status=ProposalStatus.REJECTED
            )
            manager.proposals[proposal.proposal_id] = proposal

        should_slash, count = manager.check_repeated_invalid_proposals("med-repeat")
        assert should_slash
        assert count == 3


# =============================================================================
# Cooldown Tests
# =============================================================================

class TestCooldowns:
    """Tests for cooldown periods."""

    def test_cooldown_limits_proposals(self, manager):
        """Test that cooldowns limit proposal submission."""
        manager.register_mediator(mediator_id="med-limit", stake_amount=50000)

        # Apply slashing to trigger cooldown
        manager.slash(
            mediator_id="med-limit",
            offense=SlashingOffense.REPEATED_INVALID_PROPOSALS,
            severity=0.5
        )

        # Add a pending proposal
        proposal = MediatorProposal(
            proposal_id="prop-limit",
            mediator_id="med-limit",
            contract_id="contract-001",
            content="test",
            status=ProposalStatus.PENDING
        )
        manager.proposals[proposal.proposal_id] = proposal

        # Should not be able to submit more
        can_submit, reason = manager.can_submit_proposals("med-limit")
        assert not can_submit
        assert "cooldown" in reason.lower()

    def test_cooldown_is_active(self, manager):
        """Test cooldown is_active property."""
        cooldown = Cooldown(
            cooldown_id="cd-001",
            reason=CooldownReason.SLASHING,
            duration_days=1
        )
        assert cooldown.is_active

    def test_cooldown_expired(self, manager):
        """Test cooldown expiration."""
        cooldown = Cooldown(
            cooldown_id="cd-002",
            reason=CooldownReason.SLASHING,
            started_at=datetime.utcnow() - timedelta(days=30),
            duration_days=14
        )
        assert not cooldown.is_active

    def test_cleanup_expired_cooldowns(self, manager):
        """Test cleaning up expired cooldowns."""
        manager.register_mediator(mediator_id="med-cleanup", stake_amount=50000)

        profile = manager.get_mediator("med-cleanup")

        # Add an expired cooldown
        expired = Cooldown(
            cooldown_id="cd-expired",
            reason=CooldownReason.SLASHING,
            started_at=datetime.utcnow() - timedelta(days=30),
            duration_days=7
        )
        profile.active_cooldowns.append(expired)
        profile.status = MediatorStatus.COOLDOWN

        removed = manager.cleanup_expired_cooldowns()

        assert removed == 1
        assert len(profile.active_cooldowns) == 0
        assert profile.status == MediatorStatus.ACTIVE


# =============================================================================
# Market Dynamics Tests
# =============================================================================

class TestMarketDynamics:
    """Tests for market dynamics and ranking."""

    def test_proposal_ranking_by_cts(self, manager, registered_mediators):
        """Test that proposals are ranked by CTS."""
        # Set different CTS values
        manager.update_reputation("med-001", "acceptance_rate", 0.9)
        manager.update_reputation("med-002", "acceptance_rate", 0.7)
        manager.update_reputation("med-003", "acceptance_rate", 0.5)

        rankings = manager.get_proposal_ranking(registered_mediators)

        # Higher CTS should rank higher
        assert len(rankings) == 3
        cts_values = [r["cts"] for r in rankings]
        # Rankings should be sorted descending by final_score
        final_scores = [r["final_score"] for r in rankings]
        assert final_scores == sorted(final_scores, reverse=True)

    def test_ranking_includes_diversity_bonus(self, manager, registered_mediators):
        """Test that diversity bonus is applied."""
        rankings = manager.get_proposal_ranking(
            registered_mediators,
            diversity_weight=0.2
        )

        # med-002 has multiple models, should get diversity bonus
        med002_ranking = next(r for r in rankings if r["mediator_id"] == "med-002")
        assert med002_ranking["diversity_bonus"] > 0

    def test_sample_proposals_by_trust(self, manager, registered_mediators):
        """Test trust-weighted sampling."""
        # Set very different CTS values
        manager.update_reputation("med-001", "acceptance_rate", 0.95)
        manager.update_reputation("med-002", "acceptance_rate", 0.5)
        manager.update_reputation("med-003", "acceptance_rate", 0.3)

        # Sample multiple times and check distribution
        samples = []
        for _ in range(100):
            sample = manager.sample_proposals_by_trust(
                registered_mediators,
                sample_size=1
            )
            if sample:
                samples.extend(sample)

        # High CTS mediator should be sampled more often
        from collections import Counter
        counts = Counter(samples)

        # med-001 should be sampled most frequently (it has highest CTS)
        assert counts["med-001"] > counts.get("med-003", 0)


# =============================================================================
# Treasury Tests
# =============================================================================

class TestTreasury:
    """Tests for treasury management."""

    def test_treasury_accumulates_slashing(self, manager):
        """Test that treasury accumulates slashing funds."""
        manager.register_mediator(mediator_id="med-acc", stake_amount=50000)

        assert manager.get_treasury_balance() == 0

        manager.slash(
            mediator_id="med-acc",
            offense=SlashingOffense.COERCIVE_FRAMING,
            severity=0.5
        )

        assert manager.get_treasury_balance() > 0

    def test_allocate_defensive_subsidy(self, manager):
        """Test allocating funds for defensive purposes."""
        manager.register_mediator(mediator_id="med-subsidy", stake_amount=50000)

        # Build up treasury
        manager.slash(
            mediator_id="med-subsidy",
            offense=SlashingOffense.SEMANTIC_MANIPULATION,
            severity=1.0
        )

        initial_balance = manager.get_treasury_balance()

        result = manager.allocate_defensive_subsidy(
            amount=1000,
            purpose="harassment_mitigation"
        )

        assert result["success"]
        assert manager.get_treasury_balance() < initial_balance

    def test_allocate_exceeds_balance_fails(self, manager):
        """Test that allocation exceeding balance fails."""
        result = manager.allocate_defensive_subsidy(
            amount=1000000,
            purpose="test"
        )

        assert not result["success"]
        assert "insufficient" in result["message"].lower()


# =============================================================================
# Utility Tests
# =============================================================================

class TestUtilities:
    """Tests for utility functions."""

    def test_get_mediator_summary(self, manager):
        """Test getting mediator summary."""
        manager.register_mediator(mediator_id="med-summary", stake_amount=50000)

        summary = manager.get_mediator_summary("med-summary")

        assert summary["mediator_id"] == "med-summary"
        assert "composite_trust_score" in summary
        assert "scores" in summary
        assert summary["is_bonded"]

    def test_list_mediators(self, manager, registered_mediators):
        """Test listing mediators."""
        mediators = manager.list_mediators()

        assert len(mediators) == 3

    def test_list_mediators_by_min_cts(self, manager, registered_mediators):
        """Test listing mediators by minimum CTS."""
        # Set one mediator to have low CTS
        manager.update_reputation("med-003", "acceptance_rate", 0.1)
        manager.update_reputation("med-003", "semantic_accuracy", 0.1)

        mediators = manager.list_mediators(min_cts=0.5)

        # med-003 should be filtered out
        assert all(m["composite_trust_score"] >= 0.5 for m in mediators)

    def test_list_mediators_by_domain(self, manager, registered_mediators):
        """Test listing mediators by domain."""
        mediators = manager.list_mediators(domain="software")

        # Only med-001 supports software
        assert len(mediators) == 1
        assert mediators[0]["mediator_id"] == "med-001"


# =============================================================================
# Module Function Tests
# =============================================================================

class TestModuleFunctions:
    """Tests for module-level functions."""

    def test_get_reputation_manager_singleton(self):
        """Test that get_reputation_manager returns singleton."""
        reset_reputation_manager()

        manager1 = get_reputation_manager()
        manager2 = get_reputation_manager()

        assert manager1 is manager2

    def test_reset_reputation_manager(self):
        """Test resetting the reputation manager."""
        manager1 = get_reputation_manager()
        manager1.register_mediator(mediator_id="med-reset", stake_amount=50000)

        reset_reputation_manager()
        manager2 = get_reputation_manager()

        assert manager2.get_mediator("med-reset") is None

    def test_get_ncip_010_config(self):
        """Test getting NCIP-010 configuration."""
        config = get_ncip_010_config()

        assert config["version"] == "1.0"
        assert "cts_weights" in config
        assert "slashing_rates" in config
        assert config["minimum_bond"] == MINIMUM_BOND


# =============================================================================
# Serialization Tests
# =============================================================================

class TestSerialization:
    """Tests for data class serialization."""

    def test_reputation_scores_to_dict(self):
        """Test reputation scores serialization."""
        scores = ReputationScores(
            acceptance_rate=0.8,
            semantic_accuracy=0.9
        )

        data = scores.to_dict()

        assert data["acceptance_rate"] == 0.8
        assert data["semantic_accuracy"] == 0.9

    def test_bond_to_dict(self):
        """Test bond serialization."""
        bond = Bond(amount=50000, token="NLC")

        data = bond.to_dict()

        assert data["amount"] == 50000
        assert data["token"] == "NLC"
        assert data["locked"] is True

    def test_cooldown_to_dict(self):
        """Test cooldown serialization."""
        cooldown = Cooldown(
            cooldown_id="cd-ser",
            reason=CooldownReason.SLASHING,
            duration_days=14
        )

        data = cooldown.to_dict()

        assert data["cooldown_id"] == "cd-ser"
        assert data["reason"] == "slashing"
        assert data["duration_days"] == 14

    def test_mediator_profile_to_dict(self, manager):
        """Test mediator profile serialization."""
        profile = manager.register_mediator(
            mediator_id="med-ser",
            stake_amount=50000,
            supported_domains=["software"]
        )

        data = profile.to_dict()

        assert data["mediator_id"] == "med-ser"
        assert "bond" in data
        assert "scores" in data
        assert "software" in data["supported_domains"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

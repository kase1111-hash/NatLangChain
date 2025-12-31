"""
Tests for NCIP-011: Validator–Mediator Interaction & Weight Coupling

Tests cover:
- Role separation enforcement
- Weight domain separation
- Influence gate mechanics
- Semantic consistency scoring
- Competitive mediation
- Dispute phase handling
- Collusion resistance
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from validator_mediator_coupling import (
    ActorRole,
    DisputePhase,
    MediatorWeight,
    ProtocolViolationType,
    SemanticConsistencyScore,
    ValidatorMediatorCoupling,
    ValidatorWeight,
    WeightUpdateStatus,
)


class TestRoleSeparation:
    """Test role separation enforcement per NCIP-011 Section 3."""

    def test_validator_can_assess_semantics(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1")

        allowed, violation = coupling.check_role_permission(
            "v1", ActorRole.VALIDATOR, "assess_semantic_validity"
        )
        assert allowed is True
        assert violation is None

    def test_validator_cannot_propose_terms(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1")

        allowed, violation = coupling.check_role_permission(
            "v1", ActorRole.VALIDATOR, "propose_terms"
        )
        assert allowed is False
        assert violation is not None
        assert violation.violation_type == ProtocolViolationType.PV_V3_VALIDATOR_PROPOSING

    def test_validator_cannot_negotiate_outcomes(self):
        coupling = ValidatorMediatorCoupling()

        allowed, violation = coupling.check_role_permission(
            "v1", ActorRole.VALIDATOR, "negotiate_outcomes"
        )
        assert allowed is False
        assert "PV-V3" in violation.violation_type.value

    def test_mediator_can_propose_alignments(self):
        coupling = ValidatorMediatorCoupling()

        allowed, violation = coupling.check_role_permission(
            "m1", ActorRole.MEDIATOR, "propose_alignments"
        )
        assert allowed is True
        assert violation is None

    def test_mediator_cannot_validate_semantics(self):
        coupling = ValidatorMediatorCoupling()

        allowed, violation = coupling.check_role_permission(
            "m1", ActorRole.MEDIATOR, "validate_semantics"
        )
        assert allowed is False
        assert violation.violation_type == ProtocolViolationType.PV_V3_MEDIATOR_VALIDATING

    def test_mediator_cannot_override_drift_rulings(self):
        coupling = ValidatorMediatorCoupling()

        allowed, _violation = coupling.check_role_permission(
            "m1", ActorRole.MEDIATOR, "override_drift_rulings"
        )
        assert allowed is False

    def test_human_cannot_delegate_final_authority(self):
        coupling = ValidatorMediatorCoupling()

        allowed, violation = coupling.check_role_permission(
            "h1", ActorRole.HUMAN, "delegate_final_authority"
        )
        assert allowed is False
        assert violation.violation_type == ProtocolViolationType.PV_V3_HUMAN_DELEGATING


class TestWeightDomains:
    """Test separate weight domains per NCIP-011 Section 4."""

    def test_validator_weight_computation(self):
        vw = ValidatorWeight(
            validator_id="v1",
            historical_accuracy=0.8,
            drift_precision=0.9,
            pou_consistency=0.85,
            appeal_survival_rate=0.75
        )

        expected = 0.8 * 0.25 + 0.9 * 0.25 + 0.85 * 0.25 + 0.75 * 0.25
        assert abs(vw.weight - expected) < 0.001

    def test_mediator_weight_computation(self):
        mw = MediatorWeight(
            mediator_id="m1",
            acceptance_rate=0.7,
            settlement_completion=0.8,
            post_settlement_dispute_frequency=0.2,  # Lower is better
            time_efficiency=0.9
        )

        # post_settlement_dispute_frequency is inverted
        dispute_score = 1.0 - 0.2
        expected = 0.7 * 0.25 + 0.8 * 0.25 + dispute_score * 0.25 + 0.9 * 0.25
        assert abs(mw.weight - expected) < 0.001

    def test_register_validator(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.9)

        assert coupling.get_validator_weight("v1") is not None
        assert coupling.validator_weights["v1"].historical_accuracy == 0.9

    def test_register_mediator(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1", acceptance_rate=0.8)

        assert coupling.get_mediator_weight("m1") is not None
        assert coupling.mediator_weights["m1"].acceptance_rate == 0.8


class TestSemanticConsistencyScoring:
    """Test semantic consistency scoring per NCIP-011 Section 6."""

    def test_compute_consistency_score(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")
        coupling.register_validator("v1")

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Test content")

        score = coupling.compute_semantic_consistency(
            proposal.proposal_id,
            "v1",
            intent_alignment=0.9,
            term_registry_consistency=0.85,
            drift_risk_projection=0.1,  # Low risk
            pou_symmetry=0.8
        )

        # Expected: 0.9*0.30 + 0.85*0.25 + 0.9*0.25 + 0.8*0.20
        expected = 0.9 * 0.30 + 0.85 * 0.25 + 0.9 * 0.25 + 0.8 * 0.20
        assert abs(score.score - expected) < 0.001

    def test_high_drift_risk_lowers_score(self):
        score_low_risk = SemanticConsistencyScore(
            proposal_id="p1",
            validator_id="v1",
            intent_alignment=0.8,
            term_registry_consistency=0.8,
            drift_risk_projection=0.1,
            pou_symmetry=0.8
        )

        score_high_risk = SemanticConsistencyScore(
            proposal_id="p2",
            validator_id="v1",
            intent_alignment=0.8,
            term_registry_consistency=0.8,
            drift_risk_projection=0.9,  # High risk
            pou_symmetry=0.8
        )

        assert score_low_risk.score > score_high_risk.score


class TestInfluenceGate:
    """Test influence gate per NCIP-011 Section 5."""

    def test_proposal_passes_gate(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")
        coupling.register_validator("v1", historical_accuracy=0.9, drift_precision=0.9,
                                   pou_consistency=0.9, appeal_survival_rate=0.9)
        coupling.register_validator("v2", historical_accuracy=0.85, drift_precision=0.85,
                                   pou_consistency=0.85, appeal_survival_rate=0.85)

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Good proposal")

        # Add high consistency scores
        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v1",
            intent_alignment=0.9, term_registry_consistency=0.9,
            drift_risk_projection=0.1, pou_symmetry=0.9
        )
        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v2",
            intent_alignment=0.85, term_registry_consistency=0.85,
            drift_risk_projection=0.15, pou_symmetry=0.85
        )

        result = coupling.check_influence_gate(proposal.proposal_id)

        assert result.passed is True
        assert result.gate_score >= coupling.gate_threshold
        assert proposal.hidden is False

    def test_proposal_fails_gate(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")
        coupling.register_validator("v1", historical_accuracy=0.3, drift_precision=0.3,
                                   pou_consistency=0.3, appeal_survival_rate=0.3)

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Weak proposal")

        # Add low consistency score
        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v1",
            intent_alignment=0.3, term_registry_consistency=0.3,
            drift_risk_projection=0.8, pou_symmetry=0.3
        )

        result = coupling.check_influence_gate(proposal.proposal_id)

        assert result.passed is False
        assert result.gate_score < coupling.gate_threshold
        assert proposal.hidden is True

    def test_gate_threshold_configurable(self):
        coupling = ValidatorMediatorCoupling()
        coupling.gate_threshold = 0.4  # Lower threshold

        coupling.register_mediator("m1")
        coupling.register_validator("v1", historical_accuracy=0.6, drift_precision=0.6,
                                   pou_consistency=0.6, appeal_survival_rate=0.6)

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Medium proposal")

        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v1",
            intent_alignment=0.7, term_registry_consistency=0.7,
            drift_risk_projection=0.3, pou_symmetry=0.7
        )

        result = coupling.check_influence_gate(proposal.proposal_id)

        # With lower threshold, should pass
        # VW = 0.6, consistency ~= 0.7, gate score ~= 0.42
        assert result.passed is True


class TestCompetitiveMediation:
    """Test competitive mediation per NCIP-011 Section 7."""

    def test_visible_proposals_sorted_by_weight(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.9, drift_precision=0.9,
                                   pou_consistency=0.9, appeal_survival_rate=0.9)

        # Mediator with higher weight
        coupling.register_mediator("m1", acceptance_rate=0.9, settlement_completion=0.9,
                                  post_settlement_dispute_frequency=0.1, time_efficiency=0.9)
        # Mediator with lower weight
        coupling.register_mediator("m2", acceptance_rate=0.5, settlement_completion=0.5,
                                  post_settlement_dispute_frequency=0.5, time_efficiency=0.5)

        # Submit proposals
        p1, _ = coupling.submit_proposal("m1", "alignment", "High weight proposal")
        p2, _ = coupling.submit_proposal("m2", "alignment", "Low weight proposal")

        # Add consistency scores
        for pid in [p1.proposal_id, p2.proposal_id]:
            coupling.compute_semantic_consistency(
                pid, "v1", intent_alignment=0.9, term_registry_consistency=0.9,
                drift_risk_projection=0.1, pou_symmetry=0.9
            )
            coupling.check_influence_gate(pid)

        visible = coupling.get_visible_proposals()

        assert len(visible) == 2
        # Higher weight mediator should be first
        assert visible[0].mediator_id == "m1"
        assert visible[0].competition_rank == 1
        assert visible[1].mediator_id == "m2"
        assert visible[1].competition_rank == 2

    def test_hidden_proposals_not_visible(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")
        coupling.register_validator("v1", historical_accuracy=0.2, drift_precision=0.2,
                                   pou_consistency=0.2, appeal_survival_rate=0.2)

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Will fail gate")

        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v1",
            intent_alignment=0.2, term_registry_consistency=0.2,
            drift_risk_projection=0.9, pou_symmetry=0.2
        )
        coupling.check_influence_gate(proposal.proposal_id)

        visible = coupling.get_visible_proposals()
        assert len(visible) == 0

    def test_human_selection(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")
        coupling.register_validator("v1", historical_accuracy=0.9, drift_precision=0.9,
                                   pou_consistency=0.9, appeal_survival_rate=0.9)

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Good proposal")

        coupling.compute_semantic_consistency(
            proposal.proposal_id, "v1",
            intent_alignment=0.9, term_registry_consistency=0.9,
            drift_risk_projection=0.1, pou_symmetry=0.9
        )
        coupling.check_influence_gate(proposal.proposal_id)

        success, _msg = coupling.select_proposal(proposal.proposal_id, "human-001")

        assert success is True
        assert proposal.selected is True
        assert proposal.selected_by == "human-001"

    def test_cannot_select_hidden_proposal(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_mediator("m1")

        proposal, _ = coupling.submit_proposal("m1", "alignment", "Will fail")
        proposal.hidden = True  # Manually hide

        success, msg = coupling.select_proposal(proposal.proposal_id, "human-001")

        assert success is False
        assert "hidden" in msg.lower()


class TestDisputePhase:
    """Test dispute phase handling per NCIP-011 Section 8."""

    def test_enter_dispute_phase(self):
        coupling = ValidatorMediatorCoupling()

        result = coupling.enter_dispute_phase("contract-001")

        assert result["phase"] == DisputePhase.ACTIVE.value
        assert result["validator_authority"] == "elevated"
        assert result["mediator_influence"] == "reduced"
        assert result["new_proposals_allowed"] is False

    def test_no_proposals_during_dispute(self):
        coupling = ValidatorMediatorCoupling()
        coupling.enter_dispute_phase("contract-001")

        can_submit, msg = coupling.can_submit_proposal("contract-001")

        assert can_submit is False
        assert "dispute" in msg.lower()

    def test_proposals_allowed_outside_dispute(self):
        coupling = ValidatorMediatorCoupling()

        can_submit, _msg = coupling.can_submit_proposal("contract-002")

        assert can_submit is True

    def test_exit_dispute_phase(self):
        coupling = ValidatorMediatorCoupling()
        coupling.enter_dispute_phase("contract-001")

        result = coupling.exit_dispute_phase("contract-001", "resolved")

        assert result["phase"] == DisputePhase.POST_RESOLUTION.value
        assert coupling.is_in_dispute("contract-001") is False


class TestWeightUpdates:
    """Test delayed weight updates per NCIP-011 Section 8.2."""

    def test_schedule_weight_update(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.5)

        update = coupling.schedule_weight_update(
            "v1", ActorRole.VALIDATOR,
            "historical_accuracy", 0.7,
            "Improved accuracy"
        )

        assert update is not None
        assert update.status == WeightUpdateStatus.PENDING
        assert update.old_value == 0.5
        assert update.new_value == 0.7
        assert update.delay_epochs == coupling.delay_epochs

    def test_weight_not_applied_immediately(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.5)

        coupling.schedule_weight_update(
            "v1", ActorRole.VALIDATOR,
            "historical_accuracy", 0.7,
            "Should not apply yet"
        )

        # Weight should still be old value
        assert coupling.validator_weights["v1"].historical_accuracy == 0.5

    def test_apply_pending_updates(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.5)

        update = coupling.schedule_weight_update(
            "v1", ActorRole.VALIDATOR,
            "historical_accuracy", 0.7,
            "Will be applied"
        )

        # Manually set apply_after to past
        update.apply_after = datetime.utcnow() - timedelta(days=1)

        applied = coupling.apply_pending_updates()

        assert len(applied) == 1
        assert coupling.validator_weights["v1"].historical_accuracy == 0.7
        assert applied[0].status == WeightUpdateStatus.APPLIED


class TestAppealOutcome:
    """Test appeal outcome handling per NCIP-011 Section 9."""

    def test_record_appeal_upheld(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", appeal_survival_rate=0.5)
        coupling.register_mediator("m1")

        result = coupling.record_appeal_outcome(
            "v1", "m1", appeal_upheld=True, slashing_applied=False
        )

        assert len(result["scheduled_updates"]) >= 1

    def test_record_appeal_with_slashing(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1")
        coupling.register_mediator("m1", post_settlement_dispute_frequency=0.3)

        result = coupling.record_appeal_outcome(
            "v1", "m1", appeal_upheld=False, slashing_applied=True
        )

        # Should have updates for both validator and mediator
        assert len(result["scheduled_updates"]) >= 2


class TestCollusionResistance:
    """Test collusion resistance per NCIP-011 Section 10."""

    def test_detect_high_pass_rate(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1", historical_accuracy=0.9, drift_precision=0.9,
                                   pou_consistency=0.9, appeal_survival_rate=0.9)
        coupling.register_mediator("m1")

        # Create multiple proposals from same mediator, all passed by same validator
        for i in range(6):
            proposal, _ = coupling.submit_proposal("m1", "alignment", f"Proposal {i}")
            coupling.compute_semantic_consistency(
                proposal.proposal_id, "v1",
                intent_alignment=0.9, term_registry_consistency=0.9,
                drift_risk_projection=0.1, pou_symmetry=0.9
            )

        result = coupling.detect_collusion_signals("v1", "m1")

        assert result["risk_level"] in ["medium", "high"]
        assert len(result["signals"]) > 0

    def test_no_collusion_signals_normal_case(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1")
        coupling.register_mediator("m1")

        result = coupling.detect_collusion_signals("v1", "m1")

        assert result["risk_level"] == "low"
        assert len(result["signals"]) == 0


class TestCouplingSchema:
    """Test machine-readable schema per NCIP-011 Section 11."""

    def test_generate_coupling_schema(self):
        coupling = ValidatorMediatorCoupling()
        schema = coupling.generate_coupling_schema()

        assert "validator_mediator_coupling" in schema
        config = schema["validator_mediator_coupling"]

        assert config["version"] == "1.0"
        assert config["role_separation"]["enforce_strict"] is True
        assert config["role_separation"]["violation_code"] == "PV-V3"
        assert config["influence_gate"]["enabled"] is True
        assert config["influence_gate"]["threshold"] == coupling.gate_threshold
        assert config["during_dispute"]["allow_new_proposals"] is False
        assert config["weight_updates"]["delayed_epochs"] == coupling.delay_epochs


class TestStatusSummary:
    """Test status summary."""

    def test_empty_status(self):
        coupling = ValidatorMediatorCoupling()
        summary = coupling.get_status_summary()

        assert summary["total_validators"] == 0
        assert summary["total_mediators"] == 0
        assert summary["total_proposals"] == 0
        assert "principle" in summary

    def test_status_with_data(self):
        coupling = ValidatorMediatorCoupling()
        coupling.register_validator("v1")
        coupling.register_mediator("m1")
        coupling.submit_proposal("m1", "alignment", "Test")

        summary = coupling.get_status_summary()

        assert summary["total_validators"] == 1
        assert summary["total_mediators"] == 1
        assert summary["total_proposals"] == 1


class TestProtocolViolations:
    """Test protocol violation tracking."""

    def test_violations_recorded(self):
        coupling = ValidatorMediatorCoupling()

        coupling.check_role_permission("v1", ActorRole.VALIDATOR, "propose_terms")
        coupling.check_role_permission("m1", ActorRole.MEDIATOR, "validate_semantics")

        assert len(coupling.violations) == 2

    def test_violation_details(self):
        coupling = ValidatorMediatorCoupling()

        _, violation = coupling.check_role_permission(
            "v1", ActorRole.VALIDATOR, "propose_terms"
        )

        assert violation.actor_id == "v1"
        assert violation.actor_role == ActorRole.VALIDATOR
        assert violation.attempted_action == "propose_terms"
        assert len(violation.details) > 0

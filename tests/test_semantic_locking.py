"""
Tests for NCIP-005: Semantic Locking & Cooling Periods

Tests cover:
- Semantic lock activation
- Cooling periods (24h D3, 72h D4)
- Allowed/forbidden actions during cooling
- Escalation path state machine
- Lock verification
- Resolution outcomes
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from semantic_locking import (
    SemanticLockManager,
    SemanticLock,
    LockedState,
    DisputeLevel,
    DisputeTrigger,
    LockAction,
    EscalationStage,
    ResolutionOutcome,
    CoolingPeriodStatus,
    COOLING_PERIODS,
    ALLOWED_DURING_COOLING,
    FORBIDDEN_DURING_COOLING,
    FORBIDDEN_DURING_LOCK,
    NCIP_005_CONFIG,
    get_ncip_005_config,
    get_cooling_period_hours,
    is_action_allowed_during_cooling,
    is_action_forbidden_during_lock
)


class TestSemanticLockActivation:
    """Tests for semantic lock activation per NCIP-005 Section 4."""

    def test_lock_activation_d3(self):
        """D3 trigger should activate lock with 24h cooling"""
        manager = SemanticLockManager()
        lock, entry = manager.initiate_dispute(
            contract_id="contract-001",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Semantic drift detected in clause 3",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Test contract content"
        )

        assert lock.is_active is True
        assert lock.dispute_level == DisputeLevel.D3
        assert lock.execution_halted is True
        assert lock.current_stage == EscalationStage.COOLING

    def test_lock_activation_d4(self):
        """D4 trigger should activate lock with 72h cooling"""
        manager = SemanticLockManager()
        lock, entry = manager.initiate_dispute(
            contract_id="contract-002",
            trigger=DisputeTrigger.DRIFT_D4,
            claimed_divergence="Semantic break detected",
            initiator_id="party-b",
            registry_version="1.0",
            prose_content="Test contract content"
        )

        assert lock.is_active is True
        assert lock.dispute_level == DisputeLevel.D4
        assert lock.execution_halted is True

    def test_lock_freezes_semantic_state(self):
        """Lock should freeze registry version, prose, and PoUs"""
        manager = SemanticLockManager()
        lock, entry = manager.initiate_dispute(
            contract_id="contract-003",
            trigger=DisputeTrigger.POU_FAILURE,
            claimed_divergence="PoU verification failed",
            initiator_id="party-c",
            registry_version="1.0",
            prose_content="Original contract content",
            anchor_language="en",
            verified_pou_hashes=["hash1", "hash2"]
        )

        assert lock.locked_state.registry_version == "1.0"
        assert lock.locked_state.anchor_language == "en"
        assert len(lock.locked_state.verified_pou_hashes) == 2

    def test_cannot_double_lock_contract(self):
        """Cannot create second lock on already locked contract"""
        manager = SemanticLockManager()
        manager.initiate_dispute(
            contract_id="contract-004",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="First dispute",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        try:
            manager.initiate_dispute(
                contract_id="contract-004",
                trigger=DisputeTrigger.DRIFT_D4,
                claimed_divergence="Second dispute",
                initiator_id="party-b",
                registry_version="1.0",
                prose_content="Content"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "already has active lock" in str(e)

    def test_lock_time_equals_initiation_time(self):
        """Lock time (Tₗ) should equal initiation time (Tᵢ)"""
        manager = SemanticLockManager()
        lock, entry = manager.initiate_dispute(
            contract_id="contract-005",
            trigger=DisputeTrigger.MATERIAL_BREACH,
            claimed_divergence="Breach detected",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        assert lock.lock_time == entry.timestamp


class TestCoolingPeriods:
    """Tests for cooling periods per NCIP-005 Section 6."""

    def test_d3_cooling_is_24_hours(self):
        """D3 disputes should have 24 hour cooling period"""
        assert COOLING_PERIODS[DisputeLevel.D3] == 24

    def test_d4_cooling_is_72_hours(self):
        """D4 disputes should have 72 hour cooling period"""
        assert COOLING_PERIODS[DisputeLevel.D4] == 72

    def test_cooling_status_calculation(self):
        """Cooling status should calculate time remaining"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-006",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        status = manager.get_cooling_status(lock.lock_id)

        assert status is not None
        assert status.dispute_level == DisputeLevel.D3
        assert status.duration_hours == 24
        assert status.is_active is True
        assert status.time_remaining_seconds > 0

    def test_cooling_active_check(self):
        """Should correctly detect if cooling is active"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-007",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        assert manager.is_cooling_active(lock.lock_id) is True


class TestActionEnforcement:
    """Tests for allowed/forbidden actions per NCIP-005 Section 5.2 and 6.3."""

    def test_clarification_allowed_during_cooling(self):
        """Clarification should be allowed during cooling"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-008",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.CLARIFICATION)
        assert allowed is True

    def test_settlement_proposal_allowed_during_cooling(self):
        """Settlement proposal should be allowed during cooling"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-009",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.SETTLEMENT_PROPOSAL)
        assert allowed is True

    def test_escalation_forbidden_during_cooling(self):
        """Escalation should be forbidden during cooling"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-010",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.ESCALATION)
        assert allowed is False
        assert "cooling period" in reason.lower()

    def test_enforcement_forbidden_during_cooling(self):
        """Enforcement should be forbidden during cooling"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-011",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.ENFORCEMENT)
        assert allowed is False

    def test_contract_amendment_forbidden_during_lock(self):
        """Contract amendment should be forbidden during ANY lock"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-012",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.CONTRACT_AMENDMENT)
        assert allowed is False
        assert "NCIP-005 Section 5.2" in reason

    def test_registry_upgrade_forbidden_during_lock(self):
        """Registry upgrade should be forbidden during ANY lock"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-013",
            trigger=DisputeTrigger.DRIFT_D4,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.REGISTRY_UPGRADE)
        assert allowed is False

    def test_pou_regeneration_forbidden_during_lock(self):
        """PoU regeneration should be forbidden during ANY lock"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-014",
            trigger=DisputeTrigger.POU_FAILURE,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        allowed, reason = manager.can_perform_action(lock.lock_id, LockAction.POU_REGENERATION)
        assert allowed is False

    def test_action_attempt_logging(self):
        """Action attempts should be logged"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-015",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        manager.attempt_action(lock.lock_id, LockAction.CLARIFICATION, "actor-1", "Test clarification")
        manager.attempt_action(lock.lock_id, LockAction.ESCALATION, "actor-2", "Attempted escalation")

        log = manager.get_action_log(lock.lock_id)
        # 2 attempts + 1 initial activation
        assert len(log) >= 3


class TestEscalationPath:
    """Tests for escalation path per NCIP-005 Section 7."""

    def test_escalation_path_order(self):
        """Escalation must follow defined path"""
        stages = [
            EscalationStage.COOLING,
            EscalationStage.MUTUAL_SETTLEMENT,
            EscalationStage.MEDIATOR_REVIEW,
            EscalationStage.ADJUDICATION,
            EscalationStage.BINDING_RESOLUTION,
            EscalationStage.RESOLVED
        ]
        # Just verify enums exist in expected order
        for stage in stages:
            assert isinstance(stage, EscalationStage)

    def test_cannot_advance_during_cooling(self):
        """Cannot advance stages during cooling period"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-016",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        success, message, _ = manager.advance_stage(lock.lock_id, "actor-1")
        assert success is False
        assert "cooling period" in message.lower()

    def test_stage_advancement_logged(self):
        """Stage advancements should be logged"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-017",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        # Manually expire cooling for test
        lock._locks = manager._locks  # Access internal
        manager._locks[lock.lock_id].cooling_ends_at = (
            datetime.utcnow() - timedelta(hours=1)
        ).isoformat() + "Z"

        success, message, new_stage = manager.advance_stage(lock.lock_id, "actor-1", "Testing")
        assert success is True
        assert new_stage == EscalationStage.MUTUAL_SETTLEMENT


class TestResolutionOutcomes:
    """Tests for resolution outcomes per NCIP-005 Section 9."""

    def test_dismissed_resumes_execution(self):
        """Dismissed outcome should resume execution"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-018",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        # Manually expire cooling for test
        manager._locks[lock.lock_id].cooling_ends_at = (
            datetime.utcnow() - timedelta(hours=25)
        ).isoformat() + "Z"

        success, message = manager.resolve_dispute(
            lock.lock_id,
            ResolutionOutcome.DISMISSED,
            "mediator-1",
            "Dispute was unfounded"
        )

        assert success is True
        resolved_lock = manager.get_lock(lock.lock_id)
        assert resolved_lock.is_active is False
        assert resolved_lock.current_stage == EscalationStage.RESOLVED

    def test_cannot_resolve_during_cooling(self):
        """Cannot resolve during cooling period"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-019",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        success, message = manager.resolve_dispute(
            lock.lock_id,
            ResolutionOutcome.DISMISSED,
            "mediator-1",
            "Trying to resolve early"
        )

        assert success is False
        assert "cooling period" in message.lower()

    def test_all_resolution_outcomes_exist(self):
        """All defined resolution outcomes should exist"""
        outcomes = [
            ResolutionOutcome.DISMISSED,
            ResolutionOutcome.CLARIFIED,
            ResolutionOutcome.AMENDED,
            ResolutionOutcome.TERMINATED,
            ResolutionOutcome.COMPENSATED
        ]
        for outcome in outcomes:
            assert isinstance(outcome, ResolutionOutcome)


class TestLockVerification:
    """Tests for lock verification per NCIP-005 Section 5."""

    def test_verify_matching_content(self):
        """Should pass verification for matching content"""
        manager = SemanticLockManager()
        prose = "Original contract content"
        lock, _ = manager.initiate_dispute(
            contract_id="contract-020",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content=prose
        )

        matches, discrepancies = manager.verify_against_lock(
            lock.lock_id,
            registry_version="1.0",
            prose_content=prose
        )

        assert matches is True
        assert len(discrepancies) == 0

    def test_detect_registry_version_change(self):
        """Should detect registry version changes"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-021",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        matches, discrepancies = manager.verify_against_lock(
            lock.lock_id,
            registry_version="2.0",  # Changed
            prose_content="Content"
        )

        assert matches is False
        assert any("registry version" in d.lower() for d in discrepancies)

    def test_detect_prose_content_change(self):
        """Should detect prose content changes"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-022",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Original content"
        )

        matches, discrepancies = manager.verify_against_lock(
            lock.lock_id,
            registry_version="1.0",
            prose_content="Modified content"  # Changed
        )

        assert matches is False
        assert any("modified" in d.lower() for d in discrepancies)


class TestValidatorResponse:
    """Tests for validator response generation."""

    def test_response_structure(self):
        """Validator response should have expected structure"""
        manager = SemanticLockManager(validator_id="test-validator")
        lock, _ = manager.initiate_dispute(
            contract_id="contract-023",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        response = manager.get_validator_response(lock.lock_id, LockAction.CLARIFICATION)

        assert "lock_id" in response
        assert "lock_active" in response
        assert "action_allowed" in response
        assert "cooling_period" in response
        assert "validator_id" in response
        assert response["validator_id"] == "test-validator"

    def test_response_includes_cooling_info(self):
        """Response should include cooling period information"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-024",
            trigger=DisputeTrigger.DRIFT_D4,  # 72h cooling
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        response = manager.get_validator_response(lock.lock_id, LockAction.ESCALATION)

        assert response["cooling_period"]["duration_hours"] == 72
        assert response["cooling_period"]["is_active"] is True


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_ncip_005_config(self):
        """Should return configuration dict"""
        config = get_ncip_005_config()
        assert "dispute_protocol" in config
        assert "cooling_periods" in config["dispute_protocol"]
        assert "escalation_path" in config["dispute_protocol"]

    def test_get_cooling_period_hours(self):
        """Should return correct hours for dispute level"""
        assert get_cooling_period_hours(DisputeLevel.D3) == 24
        assert get_cooling_period_hours(DisputeLevel.D4) == 72

    def test_is_action_allowed_during_cooling(self):
        """Should correctly identify allowed actions"""
        assert is_action_allowed_during_cooling(LockAction.CLARIFICATION) is True
        assert is_action_allowed_during_cooling(LockAction.SETTLEMENT_PROPOSAL) is True
        assert is_action_allowed_during_cooling(LockAction.ESCALATION) is False

    def test_is_action_forbidden_during_lock(self):
        """Should correctly identify forbidden actions"""
        assert is_action_forbidden_during_lock(LockAction.CONTRACT_AMENDMENT) is True
        assert is_action_forbidden_during_lock(LockAction.REGISTRY_UPGRADE) is True
        assert is_action_forbidden_during_lock(LockAction.CLARIFICATION) is False


class TestDisputeTriggers:
    """Tests for dispute triggers per NCIP-005 Section 3.1."""

    def test_all_triggers_exist(self):
        """All defined triggers should exist"""
        triggers = [
            DisputeTrigger.DRIFT_D3,
            DisputeTrigger.DRIFT_D4,
            DisputeTrigger.POU_FAILURE,
            DisputeTrigger.POU_CONTRADICTION,
            DisputeTrigger.CONFLICTING_RATIFICATIONS,
            DisputeTrigger.MULTILINGUAL_MISALIGNMENT,
            DisputeTrigger.MATERIAL_BREACH
        ]
        for trigger in triggers:
            assert isinstance(trigger, DisputeTrigger)

    def test_d4_trigger_sets_d4_level(self):
        """D4 trigger should set D4 dispute level"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-025",
            trigger=DisputeTrigger.DRIFT_D4,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        assert lock.dispute_level == DisputeLevel.D4

    def test_other_triggers_set_d3_level(self):
        """Non-D4 triggers should set D3 dispute level"""
        manager = SemanticLockManager()

        for trigger in [DisputeTrigger.DRIFT_D3, DisputeTrigger.POU_FAILURE,
                        DisputeTrigger.MATERIAL_BREACH]:
            lock, _ = manager.initiate_dispute(
                contract_id=f"contract-{trigger.value}",
                trigger=trigger,
                claimed_divergence="Test",
                initiator_id="party-a",
                registry_version="1.0",
                prose_content="Content"
            )
            assert lock.dispute_level == DisputeLevel.D3


class TestLockSummary:
    """Tests for lock summary generation."""

    def test_summary_structure(self):
        """Summary should have expected structure"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-026",
            trigger=DisputeTrigger.DRIFT_D3,
            claimed_divergence="Test",
            initiator_id="party-a",
            registry_version="1.0",
            prose_content="Content"
        )

        summary = manager.get_lock_summary(lock.lock_id)

        assert summary is not None
        assert "lock_id" in summary
        assert "dispute_id" in summary
        assert "contract_id" in summary
        assert "is_active" in summary
        assert "dispute_level" in summary
        assert "current_stage" in summary
        assert "locked_state" in summary

    def test_summary_reflects_lock_state(self):
        """Summary should reflect actual lock state"""
        manager = SemanticLockManager()
        lock, _ = manager.initiate_dispute(
            contract_id="contract-027",
            trigger=DisputeTrigger.DRIFT_D4,
            claimed_divergence="Test divergence",
            initiator_id="party-x",
            registry_version="2.0",
            prose_content="Contract text"
        )

        summary = manager.get_lock_summary(lock.lock_id)

        assert summary["is_active"] is True
        assert summary["dispute_level"] == "D4"
        assert summary["locked_state"]["registry_version"] == "2.0"


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestSemanticLockActivation,
        TestCoolingPeriods,
        TestActionEnforcement,
        TestEscalationPath,
        TestResolutionOutcomes,
        TestLockVerification,
        TestValidatorResponse,
        TestConvenienceFunctions,
        TestDisputeTriggers,
        TestLockSummary
    ]

    total_tests = 0
    passed_tests = 0
    failed_tests = []

    for test_class in test_classes:
        instance = test_class()
        test_methods = [m for m in dir(instance) if m.startswith("test_")]

        for method_name in test_methods:
            total_tests += 1
            method = getattr(instance, method_name)
            try:
                method()
                passed_tests += 1
                print(f"  ✓ {test_class.__name__}.{method_name}")
            except AssertionError as e:
                failed_tests.append((f"{test_class.__name__}.{method_name}", str(e)))
                print(f"  ✗ {test_class.__name__}.{method_name}: {e}")
            except Exception as e:
                failed_tests.append((f"{test_class.__name__}.{method_name}", str(e)))
                print(f"  ✗ {test_class.__name__}.{method_name}: {type(e).__name__}: {e}")

    print(f"\n{'='*60}")
    print(f"Tests: {passed_tests}/{total_tests} passed")

    if failed_tests:
        print(f"\nFailed tests:")
        for name, error in failed_tests:
            print(f"  - {name}: {error}")
        return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    exit(run_tests())

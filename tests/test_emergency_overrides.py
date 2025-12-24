"""
Tests for NCIP-013: Emergency Overrides, Force Majeure & Semantic Fallbacks

Tests cover:
- Emergency declaration lifecycle
- Force majeure classification
- Semantic fallback management
- Oracle evidence handling
- Dispute handling
- Timeout and expiry enforcement
- Abuse prevention
- Validator behavior
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from emergency_overrides import (
    EmergencyManager,
    EmergencyDeclaration,
    EmergencyStatus,
    EmergencyScope,
    ForceMajeureClass,
    ExecutionEffect,
    ProhibitedEffect,
    SemanticFallback,
    OracleEvidence,
    OracleType,
    EmergencyDispute,
)


class TestEmergencyDeclaration:
    """Tests for emergency declaration lifecycle."""

    def test_declare_emergency_success(self):
        """Test successful emergency declaration."""
        manager = EmergencyManager()
        emergency, errors = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake destroyed data center",
            affected_refs=["CONTRACT-001"]
        )

        assert emergency is not None
        assert len(errors) == 0
        assert emergency.emergency_id.startswith("EMG-")
        assert emergency.status == EmergencyStatus.DECLARED
        assert emergency.declared_by == "party_a"
        assert emergency.force_majeure_class == ForceMajeureClass.NATURAL_DISASTER

    def test_declare_emergency_missing_fields(self):
        """Test emergency declaration fails with missing required fields."""
        manager = EmergencyManager()

        # Missing declared_by
        emergency, errors = manager.declare_emergency(
            declared_by="",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )
        assert emergency is None
        assert "declared_by is required" in errors

        # Missing affected_refs
        emergency, errors = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=[]
        )
        assert emergency is None
        assert "affected_refs is required (at least one reference)" in errors

    def test_all_force_majeure_classes(self):
        """Test all 6 force majeure classes are supported."""
        manager = EmergencyManager()

        classes = [
            ForceMajeureClass.NATURAL_DISASTER,
            ForceMajeureClass.GOVERNMENT_ACTION,
            ForceMajeureClass.ARMED_CONFLICT,
            ForceMajeureClass.INFRASTRUCTURE_FAILURE,
            ForceMajeureClass.MEDICAL_INCAPACITY,
            ForceMajeureClass.SYSTEMIC_PROTOCOL_FAILURE,
        ]

        for fm_class in classes:
            emergency, errors = manager.declare_emergency(
                declared_by="party_a",
                scope=EmergencyScope.CONTRACT,
                force_majeure_class=fm_class,
                declared_reason=f"Test {fm_class.value}",
                affected_refs=["CONTRACT-001"]
            )
            assert emergency is not None
            assert emergency.force_majeure_class == fm_class

    def test_emergency_scope_types(self):
        """Test all scope types are supported."""
        manager = EmergencyManager()

        for scope in [EmergencyScope.CONTRACT, EmergencyScope.JURISDICTION, EmergencyScope.SYSTEM]:
            emergency, errors = manager.declare_emergency(
                declared_by="party_a",
                scope=scope,
                force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
                declared_reason="Test",
                affected_refs=["REF-001"]
            )
            assert emergency is not None
            assert emergency.scope == scope


class TestEmergencyValidation:
    """Tests for emergency validation."""

    def test_validate_emergency_success(self):
        """Test successful emergency validation."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake destroyed data center",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.validate_emergency(emergency.emergency_id)
        assert result["status"] in ["validated", "under_review"]
        assert "declaration is signal, not truth" in result["message"].lower()

    def test_validate_emergency_not_found(self):
        """Test validation of non-existent emergency."""
        manager = EmergencyManager()
        result = manager.validate_emergency("EMG-NONEXISTENT")
        assert result["status"] == "error"
        assert "not found" in result["message"]

    def test_validate_emergency_system_scope_warning(self):
        """Test system-wide scope requires additional verification."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.SYSTEM,
            force_majeure_class=ForceMajeureClass.SYSTEMIC_PROTOCOL_FAILURE,
            declared_reason="Chain halt",
            affected_refs=["SYSTEM"]
        )

        result = manager.validate_emergency(emergency.emergency_id)
        assert any("system-wide scope" in issue.lower() for issue in result["issues"])


class TestExecutionEffects:
    """Tests for execution effects."""

    def test_apply_allowed_effects(self):
        """Test applying allowed execution effects."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        # Validate first to allow applying effects
        manager.validate_emergency(emergency.emergency_id)

        for effect in ExecutionEffect:
            result = manager.apply_execution_effect(emergency.emergency_id, effect)
            assert result["status"] == "applied"
            assert effect.value in result["applied_effects"]

    def test_prohibited_effects_blocked(self):
        """Test prohibited effects are detected."""
        manager = EmergencyManager()

        # Test prohibited effects
        for prohibited in ProhibitedEffect:
            result = manager.check_prohibited_effect(prohibited.value)
            assert result["prohibited"] is True
            assert "NEVER allowed" in result["message"]

    def test_allowed_effects_detected(self):
        """Test allowed effects are properly detected."""
        manager = EmergencyManager()

        for allowed in ExecutionEffect:
            result = manager.check_prohibited_effect(allowed.value)
            assert result["prohibited"] is False
            assert result["allowed"] is True

    def test_cannot_apply_effects_before_validation(self):
        """Test effects cannot be applied to non-validated emergencies."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        # Try to apply effect without validation
        result = manager.apply_execution_effect(emergency.emergency_id, ExecutionEffect.PAUSE_EXECUTION)
        assert result["status"] == "error"
        assert "cannot apply effects" in result["message"].lower()


class TestSemanticFallbacks:
    """Tests for semantic fallback management."""

    def test_declare_fallback_success(self):
        """Test successful fallback declaration."""
        manager = EmergencyManager()
        fallback, errors = manager.declare_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="If earthquake destroys primary infrastructure",
            fallback_action="Transfer obligations to backup provider"
        )

        assert fallback is not None
        assert len(errors) == 0
        assert fallback.is_original is True
        assert fallback.contract_id == "CONTRACT-001"

    def test_fallback_missing_fields(self):
        """Test fallback declaration fails with missing fields."""
        manager = EmergencyManager()

        fallback, errors = manager.declare_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="",
            fallback_action="Transfer obligations"
        )
        assert fallback is None
        assert "trigger_condition is required" in errors

    def test_validate_fallback(self):
        """Test fallback validation."""
        manager = EmergencyManager()
        fallback, _ = manager.declare_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="Emergency condition",
            fallback_action="Fallback action"
        )

        result = manager.validate_fallback(fallback.fallback_id, "CONTRACT-001")
        assert result["valid"] is True
        assert result["semantically_validated"] is True

    def test_reject_posthoc_fallback(self):
        """Test post-hoc fallbacks are rejected per NCIP-013 Section 7."""
        manager = EmergencyManager()

        result = manager.reject_posthoc_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="Made up condition",
            fallback_action="Made up action"
        )

        assert result["status"] == "rejected"
        assert "post-hoc" in result["reason"].lower()
        assert "NCIP-013 Section 7" in result["reason"]

    def test_trigger_fallback_requires_validation(self):
        """Test fallback must be validated before triggering."""
        manager = EmergencyManager()

        # Create emergency
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )
        manager.validate_emergency(emergency.emergency_id)

        # Create unvalidated fallback
        fallback, _ = manager.declare_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="Emergency",
            fallback_action="Action"
        )

        # Try to trigger without validation
        result = manager.trigger_fallback(
            emergency.emergency_id,
            fallback.fallback_id,
            "CONTRACT-001"
        )
        assert result["status"] == "error"
        assert "validated" in result["message"].lower()


class TestOracleEvidence:
    """Tests for oracle evidence handling."""

    def test_add_oracle_evidence(self):
        """Test adding oracle evidence."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.add_oracle_evidence(
            emergency_id=emergency.emergency_id,
            oracle_id="USGS-FEED",
            oracle_type=OracleType.DISASTER_FEED,
            evidence_data="7.2 magnitude earthquake detected",
            confidence_score=0.95
        )

        assert result["status"] == "added"
        assert result["confidence_score"] == 0.95
        assert "evidence, not authority" in result["note"]

    def test_oracle_never_authoritative(self):
        """Test oracle outputs are never authoritative per NCIP-013 Section 5."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        manager.add_oracle_evidence(
            emergency_id=emergency.emergency_id,
            oracle_id="USGS-FEED",
            oracle_type=OracleType.DISASTER_FEED,
            evidence_data="Earthquake data",
            confidence_score=1.0  # Even with max confidence
        )

        # Verify oracle is not authoritative
        updated_emergency = manager.get_emergency(emergency.emergency_id)
        for evidence in updated_emergency.oracle_evidence:
            assert evidence.is_authoritative is False

    def test_all_oracle_types_supported(self):
        """Test all oracle types are supported."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Test",
            affected_refs=["CONTRACT-001"]
        )

        for oracle_type in OracleType:
            result = manager.add_oracle_evidence(
                emergency_id=emergency.emergency_id,
                oracle_id=f"ORACLE-{oracle_type.value}",
                oracle_type=oracle_type,
                evidence_data="Test data",
                confidence_score=0.8
            )
            assert result["status"] == "added"


class TestEmergencyDisputes:
    """Tests for emergency dispute handling."""

    def test_dispute_emergency(self):
        """Test disputing an emergency declaration."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        dispute, errors = manager.dispute_emergency(
            emergency_id=emergency.emergency_id,
            disputed_by="party_b",
            dispute_reason="No earthquake occurred in the area"
        )

        assert dispute is not None
        assert len(errors) == 0
        assert dispute.burden_of_proof == "declarer"
        assert dispute.semantic_lock_id is not None

    def test_dispute_triggers_semantic_lock(self):
        """Test dispute triggers semantic lock immediately."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        dispute, _ = manager.dispute_emergency(
            emergency_id=emergency.emergency_id,
            disputed_by="party_b",
            dispute_reason="Dispute reason"
        )

        updated_emergency = manager.get_emergency(emergency.emergency_id)
        assert updated_emergency.status == EmergencyStatus.DISPUTED
        assert updated_emergency.semantic_lock_id is not None

    def test_resolve_dispute_upheld(self):
        """Test resolving dispute in favor of declarer."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        dispute, _ = manager.dispute_emergency(
            emergency_id=emergency.emergency_id,
            disputed_by="party_b",
            dispute_reason="Challenge"
        )

        result = manager.resolve_emergency_dispute(
            dispute_id=dispute.dispute_id,
            upheld=True,
            resolution_notes="Evidence confirms earthquake"
        )

        assert result["upheld"] is True
        updated_emergency = manager.get_emergency(emergency.emergency_id)
        assert updated_emergency.status == EmergencyStatus.ACTIVE

    def test_resolve_dispute_rejected_marks_frivolous(self):
        """Test rejected dispute marks emergency as frivolous."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Fake earthquake",
            affected_refs=["CONTRACT-001"]
        )

        dispute, _ = manager.dispute_emergency(
            emergency_id=emergency.emergency_id,
            disputed_by="party_b",
            dispute_reason="No earthquake occurred"
        )

        result = manager.resolve_emergency_dispute(
            dispute_id=dispute.dispute_id,
            upheld=False,
            resolution_notes="No evidence of earthquake"
        )

        assert result["upheld"] is False
        assert result["harassment_penalty"] > 0
        updated_emergency = manager.get_emergency(emergency.emergency_id)
        assert updated_emergency.status == EmergencyStatus.REJECTED
        assert updated_emergency.frivolous is True


class TestTimeoutAndExpiry:
    """Tests for timeout and expiry handling."""

    def test_emergency_has_deadlines(self):
        """Test emergency has review and expiry deadlines."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"],
            review_after_days=30,
            max_duration_days=180
        )

        assert emergency.review_deadline is not None
        assert emergency.expiry_deadline is not None
        assert emergency.review_deadline < emergency.expiry_deadline

    def test_check_expiry(self):
        """Test checking emergency expiry status."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.check_expiry(emergency.emergency_id)
        assert result["is_expired"] is False
        assert "silent_continuation_forbidden" not in result or result.get("silent_continuation_forbidden") is not True

    def test_process_expiry_resume_execution(self):
        """Test processing expiry by resuming execution."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.process_expiry(emergency.emergency_id, "resume_execution")
        assert result["status"] == "resolved"
        assert result["action"] == "resume_execution"

    def test_process_expiry_terminate_fallback(self):
        """Test processing expiry by terminating with fallback."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.process_expiry(emergency.emergency_id, "terminate_fallback")
        assert result["status"] == "resolved"
        assert result["action"] == "terminate_fallback"

    def test_process_expiry_ratify_amendment(self):
        """Test processing expiry by ratifying amendment."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.process_expiry(
            emergency.emergency_id,
            "ratify_amendment",
            ratification_id="RATIFY-001"
        )
        assert result["status"] == "resolved"
        assert result["action"] == "ratify_amendment"
        assert result["ratification_id"] == "RATIFY-001"


class TestEscalation:
    """Tests for escalation handling."""

    def test_check_escalation_needed(self):
        """Test checking if escalation is needed."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.check_escalation_needed(emergency.emergency_id)
        assert result["threshold_days"] == 30
        # New emergency should not need escalation
        assert result["needs_escalation"] is False


class TestAbusePrevention:
    """Tests for abuse prevention."""

    def test_repeat_declarations_tracked(self):
        """Test repeat declarations by same party are tracked."""
        manager = EmergencyManager()

        # First declaration
        emergency1, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake 1",
            affected_refs=["CONTRACT-001"]
        )

        # Second declaration
        emergency2, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake 2",
            affected_refs=["CONTRACT-002"]
        )

        assert len(manager.declarer_history["party_a"]) == 2

    def test_harassment_penalty_escalates(self):
        """Test harassment penalty escalates for repeat frivolous declarations."""
        manager = EmergencyManager()

        # First frivolous declaration
        e1, _ = manager.declare_emergency(
            declared_by="bad_actor",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Fake 1",
            affected_refs=["CONTRACT-001"]
        )
        d1, _ = manager.dispute_emergency(e1.emergency_id, "victim", "Fake")
        result1 = manager.resolve_emergency_dispute(d1.dispute_id, False, "Rejected")
        penalty1 = result1["harassment_penalty"]

        # Second frivolous declaration
        e2, _ = manager.declare_emergency(
            declared_by="bad_actor",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Fake 2",
            affected_refs=["CONTRACT-002"]
        )
        d2, _ = manager.dispute_emergency(e2.emergency_id, "victim", "Fake")
        result2 = manager.resolve_emergency_dispute(d2.dispute_id, False, "Rejected")
        penalty2 = result2["harassment_penalty"]

        assert penalty2 > penalty1  # Penalty escalates


class TestValidatorBehavior:
    """Tests for validator behavior per NCIP-013 Section 11."""

    def test_validator_check_complete_emergency(self):
        """Test validator check on complete emergency."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.validator_check(emergency.emergency_id)
        assert result["checks"]["has_explicit_scope"] is True
        assert result["checks"]["has_explicit_duration"] is True
        assert result["checks"]["semantic_integrity_preserved"] is True
        assert "execution — never meaning" in result["principle"].lower()

    def test_validator_treats_claims_skeptically(self):
        """Test validators treat claims as signal, not truth."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        result = manager.validate_emergency(emergency.emergency_id)
        assert "signal" in result["message"].lower()
        assert "not truth" in result["message"].lower()


class TestMachineReadablePolicy:
    """Tests for machine-readable policy."""

    def test_generate_emergency_policy(self):
        """Test generating machine-readable emergency policy."""
        manager = EmergencyManager()
        policy = manager.generate_emergency_policy()

        assert policy["emergency_policy"]["version"] == "1.0"
        assert policy["emergency_policy"]["allow_execution_pause"] is True
        assert policy["emergency_policy"]["allow_semantic_change"] is False
        assert "scope" in policy["emergency_policy"]["required_fields"]
        assert policy["emergency_policy"]["oracle_support"]["authoritative"] is False
        assert policy["emergency_policy"]["dispute_handling"]["burden_of_proof"] == "declarer"


class TestStatusReporting:
    """Tests for status and reporting."""

    def test_get_active_emergencies(self):
        """Test getting active emergencies."""
        manager = EmergencyManager()

        # Create and activate an emergency
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )
        manager.validate_emergency(emergency.emergency_id)
        manager.apply_execution_effect(emergency.emergency_id, ExecutionEffect.PAUSE_EXECUTION)

        active = manager.get_active_emergencies()
        assert len(active) >= 1

    def test_get_status_summary(self):
        """Test getting status summary."""
        manager = EmergencyManager()
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )

        summary = manager.get_status_summary()
        assert summary["total_emergencies"] >= 1
        assert "principle" in summary
        assert "execution" in summary["principle"].lower()


class TestCorePrinciple:
    """Tests for core principle: Emergencies may suspend execution — never meaning."""

    def test_execution_effects_dont_alter_meaning(self):
        """Test that execution effects don't alter semantic meaning."""
        manager = EmergencyManager()

        # All execution effects should preserve meaning
        for effect in ExecutionEffect:
            result = manager.check_prohibited_effect(effect.value)
            assert result["prohibited"] is False

    def test_semantic_changes_always_prohibited(self):
        """Test that semantic changes are always prohibited."""
        manager = EmergencyManager()

        for prohibited in ProhibitedEffect:
            result = manager.check_prohibited_effect(prohibited.value)
            assert result["prohibited"] is True


class TestFallbackIntegration:
    """Tests for fallback and emergency integration."""

    def test_trigger_validated_fallback(self):
        """Test triggering a validated fallback during emergency."""
        manager = EmergencyManager()

        # Create emergency
        emergency, _ = manager.declare_emergency(
            declared_by="party_a",
            scope=EmergencyScope.CONTRACT,
            force_majeure_class=ForceMajeureClass.NATURAL_DISASTER,
            declared_reason="Earthquake",
            affected_refs=["CONTRACT-001"]
        )
        manager.validate_emergency(emergency.emergency_id)

        # Create and validate fallback
        fallback, _ = manager.declare_fallback(
            contract_id="CONTRACT-001",
            trigger_condition="Earthquake destroys infrastructure",
            fallback_action="Transfer to backup provider"
        )
        manager.validate_fallback(fallback.fallback_id, "CONTRACT-001")

        # Trigger fallback
        result = manager.trigger_fallback(
            emergency.emergency_id,
            fallback.fallback_id,
            "CONTRACT-001"
        )

        assert result["status"] == "triggered"
        assert result["trigger_condition"] == "Earthquake destroys infrastructure"
        assert result["fallback_action"] == "Transfer to backup provider"

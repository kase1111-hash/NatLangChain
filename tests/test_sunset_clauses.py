"""
Tests for NCIP-015: Sunset Clauses, Archival Finality & Historical Semantics

Tests cover:
- Sunset clause declaration and validation
- State machine transitions
- Archival finality
- Historical semantics preservation
- Temporal context binding
- Validator behavior
- Mediator constraints
- Emergency integration
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from sunset_clauses import (
    SunsetManager,
    SunsetClause,
    SunsetTriggerType,
    EntryState,
    EntryType,
    ManagedEntry,
    ArchivedEntry,
    TemporalContext,
    VALID_TRANSITIONS,
    DEFAULT_SUNSET_YEARS,
)


class TestSunsetTriggerTypes:
    """Test all 6 sunset trigger types per NCIP-015 Section 3.2."""

    def test_all_trigger_types_exist(self):
        """Test all 6 trigger types are defined."""
        assert SunsetTriggerType.TIME_BASED.value == "time_based"
        assert SunsetTriggerType.EVENT_BASED.value == "event_based"
        assert SunsetTriggerType.CONDITION_FULFILLED.value == "condition_fulfilled"
        assert SunsetTriggerType.EXHAUSTION.value == "exhaustion"
        assert SunsetTriggerType.REVOCATION.value == "revocation"
        assert SunsetTriggerType.CONSTITUTIONAL.value == "constitutional"

    def test_time_based_trigger(self):
        """Test time-based sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract")

        sunset_date = datetime.utcnow() + timedelta(days=30)
        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.TIME_BASED,
            trigger_datetime=sunset_date
        )

        assert clause is not None
        assert len(errors) == 0
        assert clause.is_explicit() is True

    def test_event_based_trigger(self):
        """Test event-based sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.LICENSE, "Test license")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.EVENT_BASED,
            trigger_event="Acquisition of Company X"
        )

        assert clause is not None
        assert clause.trigger_event == "Acquisition of Company X"

    def test_condition_fulfilled_trigger(self):
        """Test condition-fulfilled sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.CONDITION_FULFILLED,
            trigger_condition="All deliverables accepted"
        )

        assert clause is not None
        assert clause.trigger_condition == "All deliverables accepted"

    def test_exhaustion_trigger(self):
        """Test exhaustion (finite-use) sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.LICENSE, "Test license")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.EXHAUSTION,
            max_uses=100
        )

        assert clause is not None
        assert clause.max_uses == 100

    def test_revocation_trigger(self):
        """Test revocation sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.DELEGATION, "Test delegation")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.REVOCATION,
            revocation_terms="May be revoked with 30 days notice"
        )

        assert clause is not None
        assert clause.revocation_terms is not None

    def test_constitutional_trigger(self):
        """Test constitutional amendment sunset trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.CONSTITUTIONAL,
            amendment_id="AMEND-2025-001"
        )

        assert clause is not None
        assert clause.amendment_id == "AMEND-2025-001"


class TestSunsetClauseExplicitness:
    """Test that sunset clauses must be explicit per NCIP-015 Section 3.3."""

    def test_implicit_sunset_rejected(self):
        """Test implicit sunsets are invalid."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract")

        # Try to create time-based without datetime
        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.TIME_BASED
            # Missing trigger_datetime
        )

        assert clause is None
        assert any("explicit" in e.lower() for e in errors)

    def test_explicit_sunset_required_message(self):
        """Test error message mentions explicitness requirement."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        clause, errors = manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.EXHAUSTION
            # Missing max_uses
        )

        assert clause is None
        assert len(errors) > 0


class TestStateMachine:
    """Test state machine per NCIP-015 Section 4."""

    def test_initial_state_is_draft(self):
        """Test entries start in DRAFT state."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")
        assert entry.state == EntryState.DRAFT

    def test_valid_forward_transitions(self):
        """Test all valid forward transitions."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        # Create temporal context for ratification
        context = TemporalContext(
            registry_version="1.0",
            language_variant="en",
            jurisdiction_context="US"
        )

        # DRAFT → RATIFIED
        success, _ = manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning")
        assert success is True
        assert entry.state == EntryState.RATIFIED

        # RATIFIED → ACTIVE
        success, _ = manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        assert success is True
        assert entry.state == EntryState.ACTIVE

        # ACTIVE → SUNSET_PENDING
        success, _ = manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        assert success is True
        assert entry.state == EntryState.SUNSET_PENDING

        # SUNSET_PENDING → SUNSET
        success, _ = manager.transition_state(entry.entry_id, EntryState.SUNSET)
        assert success is True
        assert entry.state == EntryState.SUNSET

        # SUNSET → ARCHIVED
        success, _ = manager.transition_state(entry.entry_id, EntryState.ARCHIVED)
        assert success is True
        assert entry.state == EntryState.ARCHIVED

    def test_backward_transitions_blocked(self):
        """Test no backward transitions are permitted."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        # Try backward transition ACTIVE → DRAFT
        success, msg = manager.transition_state(entry.entry_id, EntryState.DRAFT)
        assert success is False
        assert "invalid transition" in msg.lower()

    def test_skip_state_blocked(self):
        """Test skipping states is not permitted."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        # Try DRAFT → ACTIVE (skipping RATIFIED)
        success, msg = manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        assert success is False

    def test_archived_is_terminal(self):
        """Test ARCHIVED is terminal state with no further transitions."""
        assert VALID_TRANSITIONS[EntryState.ARCHIVED] == []


class TestDefaultSunsetPolicy:
    """Test default sunset policies per NCIP-015 Section 14."""

    def test_contract_default_20_years(self):
        """Test contracts default to 20 years."""
        assert DEFAULT_SUNSET_YEARS[EntryType.CONTRACT] == 20

    def test_license_default_10_years(self):
        """Test licenses default to 10 years."""
        assert DEFAULT_SUNSET_YEARS[EntryType.LICENSE] == 10

    def test_delegation_default_2_years(self):
        """Test delegations default to 2 years."""
        assert DEFAULT_SUNSET_YEARS[EntryType.DELEGATION] == 2

    def test_standing_intent_default_1_year(self):
        """Test standing intents default to 1 year."""
        assert DEFAULT_SUNSET_YEARS[EntryType.STANDING_INTENT] == 1

    def test_settlement_immediate_archive(self):
        """Test settlements default to immediate archive."""
        assert DEFAULT_SUNSET_YEARS[EntryType.SETTLEMENT] == 0

    def test_default_sunset_applied_on_ratification(self):
        """Test default sunset is applied when no explicit sunset declared."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)

        assert entry.sunset_clause is not None
        assert entry.sunset_clause.trigger_type == SunsetTriggerType.TIME_BASED
        # Should be approximately 20 years from now
        assert entry.sunset_clause.trigger_datetime is not None


class TestArchivalFinality:
    """Test archival finality per NCIP-015 Section 5."""

    def test_archived_entry_created(self):
        """Test archived entry is created on archive transition."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test contract content")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning")
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive is not None
        assert archive.prose_content == "Test contract content"
        assert archive.original_meaning == "Original meaning"

    def test_archived_not_enforceable(self):
        """Test archived entries are not enforceable."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive.enforceable is False
        assert archive.negotiable is False
        assert archive.referential_only is True

    def test_drift_detection_disabled_on_archive(self):
        """Test drift detection is disabled for archived entries."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive.drift_detection_disabled is True

    def test_archive_integrity_verification(self):
        """Test archive integrity can be verified."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive.verify_integrity() is True


class TestTemporalContextBinding:
    """Test temporal context binding per NCIP-015 Section 7."""

    def test_temporal_context_bound_at_ratification(self):
        """Test temporal context is bound at ratification."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext(
            registry_version="1.2.3",
            language_variant="en-US",
            jurisdiction_context="US-CA",
            proof_of_understanding_ids=["POU-001", "POU-002"]
        )

        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)

        assert entry.temporal_context is not None
        assert entry.temporal_context.registry_version == "1.2.3"
        assert entry.temporal_context.language_variant == "en-US"
        assert entry.temporal_context.jurisdiction_context == "US-CA"

    def test_temporal_context_preserved_in_archive(self):
        """Test temporal context is preserved in archive."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext(
            registry_version="1.0",
            language_variant="en",
            jurisdiction_context="US"
        )

        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive.temporal_context.registry_version == "1.0"

    def test_temporal_context_generates_hash(self):
        """Test temporal context generates immutable hash."""
        context = TemporalContext(
            registry_version="1.0",
            language_variant="en",
            jurisdiction_context="US"
        )

        hash1 = context.to_hash()
        hash2 = context.to_hash()

        assert hash1 == hash2
        assert len(hash1) == 16


class TestHistoricalSemantics:
    """Test historical semantics per NCIP-015 Section 6."""

    def test_validate_historical_reference(self):
        """Test historical reference validation."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning at T₀")
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.validate_historical_reference(entry.entry_id, "Some interpretation")

        assert result["valid"] is True
        assert result["original_meaning"] == "Original meaning at T₀"
        assert result["reinterpretation_rejected"] is True
        assert "referential only" in result["warning"].lower()

    def test_reject_retroactive_application(self):
        """Test retroactive application is rejected."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.reject_retroactive_application(entry.entry_id, "Apply new regulation")

        assert result["rejected"] is True
        assert "retroactively" in result["reason"].lower()


class TestValidatorBehavior:
    """Test validator behavior per NCIP-015 Section 8."""

    def test_validator_check_active_entry(self):
        """Test validator check on active entry."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        result = manager.validator_check(entry.entry_id)

        assert result["state"] == "active"
        assert result["enforceable"] is True
        assert result["drift_detection_enabled"] is True

    def test_validator_check_archived_entry(self):
        """Test validator check on archived entry."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.validator_check(entry.entry_id)

        assert result["state"] == "archived"
        assert result["enforceable"] is False
        assert result["drift_detection_enabled"] is False
        assert result["referential_only"] is True
        assert "reject" in result["validator_action"].lower()

    def test_validator_check_includes_principle(self):
        """Test validator check includes core principle."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        result = manager.validator_check(entry.entry_id)
        assert "meaning may expire" in result["principle"].lower()
        assert "history must not" in result["principle"].lower()


class TestMediatorConstraints:
    """Test mediator constraints per NCIP-015 Section 9."""

    def test_mediator_can_cite_archived_as_context(self):
        """Test mediators can cite archived entries as context."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.mediator_can_cite(entry.entry_id)

        assert result["can_cite"] is True
        assert result["as_context_only"] is True
        assert result["can_propose_action"] is False

    def test_mediator_cannot_propose_action_on_archived(self):
        """Test mediators cannot propose actions based on archived entries."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.mediator_can_cite(entry.entry_id)
        assert result["can_propose_action"] is False

    def test_mediator_restatement_required(self):
        """Test mediators must restate historical semantics to reactivate."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning")
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.mediator_restatement_required(entry.entry_id, "Proposed reactivation")

        assert result["restatement_required"] is True
        assert result["original_meaning"] == "Original meaning"
        assert "inform" in result["guidance"].lower()
        assert "cannot compel" in result["guidance"].lower()


class TestSunsetTriggering:
    """Test sunset triggering mechanisms."""

    def test_time_based_trigger_check(self):
        """Test time-based trigger check."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        # Set sunset to past
        past_date = datetime.utcnow() - timedelta(days=1)
        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.TIME_BASED,
            trigger_datetime=past_date
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        triggered = manager.check_sunset_triggers()
        assert len(triggered) >= 1
        assert triggered[0]["entry_id"] == entry.entry_id

    def test_exhaustion_trigger(self):
        """Test exhaustion trigger after max uses."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.LICENSE, "Test")

        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.EXHAUSTION,
            max_uses=3
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        # Record uses
        manager.record_use(entry.entry_id)
        manager.record_use(entry.entry_id)
        result = manager.record_use(entry.entry_id)

        assert result["sunset_triggered"] is True
        assert entry.state == EntryState.SUNSET_PENDING

    def test_event_trigger(self):
        """Test event-based trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.LICENSE, "Test")

        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.EVENT_BASED,
            trigger_event="Company acquisition"
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        success, msg = manager.record_event_trigger(entry.entry_id, "Company X acquired")
        assert success is True
        assert entry.state == EntryState.SUNSET_PENDING

    def test_revocation_trigger(self):
        """Test revocation trigger."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.DELEGATION, "Test")

        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.REVOCATION,
            revocation_terms="May be revoked with notice"
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        success, msg = manager.process_revocation(entry.entry_id, "admin", "No longer needed")
        assert success is True
        assert entry.state == EntryState.SUNSET_PENDING


class TestEmergencyIntegration:
    """Test emergency integration per NCIP-015 Section 11."""

    def test_pause_sunset_timer(self):
        """Test sunset timer pauses during emergency."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        success, msg = manager.pause_sunset_timer(entry.entry_id, "EMG-001")

        assert success is True
        assert entry.emergency_paused is True
        assert entry.emergency_id == "EMG-001"

    def test_cannot_transition_during_emergency(self):
        """Test cannot transition to sunset states during emergency."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        manager.pause_sunset_timer(entry.entry_id, "EMG-001")

        success, msg = manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        assert success is False
        assert "emergency" in msg.lower()

    def test_resume_sunset_timer(self):
        """Test sunset timer resumes after emergency."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        manager.pause_sunset_timer(entry.entry_id, "EMG-001")
        success, msg = manager.resume_sunset_timer(entry.entry_id)

        assert success is True
        assert entry.emergency_paused is False


class TestMachineReadableSchema:
    """Test machine-readable schema per NCIP-015 Section 10."""

    def test_generate_schema_for_active_entry(self):
        """Test schema generation for active entry."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        sunset_date = datetime.utcnow() + timedelta(days=365)
        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.TIME_BASED,
            trigger_datetime=sunset_date
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        schema = manager.generate_sunset_schema(entry.entry_id)

        assert schema["sunset_and_archive"]["version"] == "1.0"
        assert schema["sunset_and_archive"]["state"] == "active"
        assert schema["sunset_and_archive"]["sunset"]["type"] == "time_based"

    def test_generate_schema_for_archived_entry(self):
        """Test schema generation for archived entry."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        schema = manager.generate_sunset_schema(entry.entry_id)

        assert schema["sunset_and_archive"]["state"] == "archived"
        assert schema["sunset_and_archive"]["post_sunset_state"]["enforceable"] is False
        assert schema["sunset_and_archive"]["validator_rules"]["disable_drift_detection"] is True


class TestStatusReporting:
    """Test status and reporting functions."""

    def test_get_entries_by_state(self):
        """Test getting entries by state."""
        manager = SunsetManager()

        entry1 = manager.create_entry(EntryType.CONTRACT, "Test 1")
        entry2 = manager.create_entry(EntryType.CONTRACT, "Test 2")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry1.entry_id, EntryState.RATIFIED, context)

        draft_entries = manager.get_entries_by_state(EntryState.DRAFT)
        ratified_entries = manager.get_entries_by_state(EntryState.RATIFIED)

        assert len(draft_entries) == 1
        assert len(ratified_entries) == 1

    def test_get_expiring_entries(self):
        """Test getting entries expiring soon."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        # Set sunset to 10 days from now
        sunset_date = datetime.utcnow() + timedelta(days=10)
        manager.declare_sunset(
            entry.entry_id,
            SunsetTriggerType.TIME_BASED,
            trigger_datetime=sunset_date
        )

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        expiring = manager.get_expiring_entries(days_ahead=30)
        assert len(expiring) >= 1
        assert expiring[0]["entry_id"] == entry.entry_id

    def test_get_status_summary(self):
        """Test getting status summary."""
        manager = SunsetManager()

        manager.create_entry(EntryType.CONTRACT, "Test 1")
        manager.create_entry(EntryType.LICENSE, "Test 2")

        summary = manager.get_status_summary()

        assert summary["total_entries"] == 2
        assert "principle" in summary
        assert "meaning may expire" in summary["principle"].lower()


class TestCorePrinciple:
    """Test core principle: Meaning may expire. History must not."""

    def test_sunset_does_not_mean_deletion(self):
        """Test sunset does not delete records."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Original content")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning")
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        # Entry still exists in archive
        archive = manager.get_archive(entry.entry_id)
        assert archive is not None
        assert archive.prose_content == "Original content"

    def test_expiration_does_not_mean_reinterpretation(self):
        """Test expiration does not enable reinterpretation."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context, "Original meaning")
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        result = manager.validate_historical_reference(entry.entry_id, "New interpretation")
        assert result["reinterpretation_rejected"] is True

    def test_archival_does_not_mean_semantic_drift(self):
        """Test archival disables drift detection."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)
        manager.transition_state(entry.entry_id, EntryState.SUNSET_PENDING)
        manager.transition_state(entry.entry_id, EntryState.SUNSET)
        manager.transition_state(entry.entry_id, EntryState.ARCHIVED)

        archive = manager.get_archive(entry.entry_id)
        assert archive.drift_detection_disabled is True


class TestStateHistory:
    """Test state history tracking."""

    def test_state_history_recorded(self):
        """Test state transitions are recorded in history."""
        manager = SunsetManager()
        entry = manager.create_entry(EntryType.CONTRACT, "Test")

        context = TemporalContext("1.0", "en", "US")
        manager.transition_state(entry.entry_id, EntryState.RATIFIED, context)
        manager.transition_state(entry.entry_id, EntryState.ACTIVE)

        assert len(entry.state_history) >= 3  # DRAFT + RATIFIED + ACTIVE
        states = [s[0] for s in entry.state_history]
        assert EntryState.DRAFT in states
        assert EntryState.RATIFIED in states
        assert EntryState.ACTIVE in states

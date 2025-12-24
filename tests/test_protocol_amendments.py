"""
Tests for NCIP-014: Protocol Amendments & Constitutional Change
"""

import pytest
from datetime import datetime, timedelta
from src.protocol_amendments import (
    AmendmentManager,
    AmendmentClass,
    AmendmentStatus,
    RatificationStage,
    ConstitutionalArtifact,
    ProhibitedAction,
    Amendment,
    EmergencyAmendment,
    VoteRecord,
    PoUStatement,
    SemanticCompatibilityResult,
    ConstitutionVersion,
)


class TestAmendmentClasses:
    """Tests for amendment class thresholds."""

    def test_threshold_values(self):
        """Test that thresholds are correct per NCIP-014."""
        manager = AmendmentManager()

        assert manager.THRESHOLDS[AmendmentClass.A] == 0.50  # Simple majority
        assert manager.THRESHOLDS[AmendmentClass.B] == 0.67  # Supermajority
        assert manager.THRESHOLDS[AmendmentClass.C] == 0.75  # Constitutional quorum
        assert manager.THRESHOLDS[AmendmentClass.D] == 0.90  # Near-unanimous
        assert manager.THRESHOLDS[AmendmentClass.E] == 1.00  # Fork-only

    def test_class_e_requires_fork(self):
        """Test that Class E amendments require fork."""
        manager = AmendmentManager()

        amendment, errors = manager.create_amendment(
            amendment_id="NCIP-014-E-2025-001",
            amendment_class=AmendmentClass.E,
            title="Core Principle Change",
            rationale="This is a significant rationale explaining the core principle change "
                     "that requires careful consideration by all participants.",
            scope_of_impact="Affects all protocol participants and future entries",
            affected_artifacts=[ConstitutionalArtifact.CORE_DOCTRINES],
            proposed_changes="Proposed modification to core refusal doctrine with detailed explanation "
                           "of how this will affect all participants going forward.",
            migration_guidance="Complete protocol migration required with 6-month transition period."
        )

        assert amendment is not None
        assert amendment.fork_required is True

    def test_deliberation_windows(self):
        """Test deliberation window durations by class."""
        manager = AmendmentManager()

        assert manager.DELIBERATION_WINDOWS[AmendmentClass.A] == timedelta(days=7)
        assert manager.DELIBERATION_WINDOWS[AmendmentClass.B] == timedelta(days=14)
        assert manager.DELIBERATION_WINDOWS[AmendmentClass.C] == timedelta(days=21)
        assert manager.DELIBERATION_WINDOWS[AmendmentClass.D] == timedelta(days=30)
        assert manager.DELIBERATION_WINDOWS[AmendmentClass.E] == timedelta(days=60)


class TestAmendmentCreation:
    """Tests for creating amendments."""

    def test_create_valid_amendment(self):
        """Test creating a valid amendment."""
        manager = AmendmentManager()

        amendment, errors = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-001",
            amendment_class=AmendmentClass.A,
            title="Clarify Term Definition",
            rationale="The current wording of term X is ambiguous and needs clarification "
                     "to prevent misinterpretation by validators.",
            scope_of_impact="Affects validator interpretation of term X",
            affected_artifacts=[ConstitutionalArtifact.CANONICAL_TERM_REGISTRY],
            proposed_changes="Change definition from Y to Z with explicit boundary conditions "
                           "that prevent the ambiguity that currently exists."
        )

        assert amendment is not None
        assert len(errors) == 0
        assert amendment.status == AmendmentStatus.DRAFT
        assert amendment.retroactive is False

    def test_reject_retroactive_amendment(self):
        """Test that retroactive amendments are rejected."""
        with pytest.raises(ValueError, match="MUST NOT be retroactive"):
            Amendment(
                amendment_id="NCIP-014-A-2025-002",
                amendment_class=AmendmentClass.A,
                title="Invalid Amendment",
                rationale="Test rationale that is at least 50 characters for validation",
                scope_of_impact="Test scope of impact for validation",
                affected_artifacts=[ConstitutionalArtifact.NCIP_001],
                proposed_changes="Test proposed changes that are at least 50 characters for validation",
                retroactive=True  # PROHIBITED
            )

    def test_require_rationale(self):
        """Test that rationale is required."""
        manager = AmendmentManager()

        amendment, errors = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-003",
            amendment_class=AmendmentClass.A,
            title="Missing Rationale",
            rationale="Short",  # Too short
            scope_of_impact="Affects interpretation of existing terms",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Detailed proposed changes that explain what will be modified "
                           "in the protocol documentation."
        )

        assert amendment is None
        assert any("Rationale" in e for e in errors)

    def test_class_d_requires_migration(self):
        """Test that Class D amendments require migration guidance."""
        manager = AmendmentManager()

        amendment, errors = manager.create_amendment(
            amendment_id="NCIP-014-D-2025-001",
            amendment_class=AmendmentClass.D,
            title="Structural Change",
            rationale="Major structural change to governance model requiring careful consideration "
                     "and detailed transition planning.",
            scope_of_impact="Affects all governance participants",
            affected_artifacts=[ConstitutionalArtifact.CORE_DOCTRINES],
            proposed_changes="Complete restructuring of authority boundaries with new delegation model "
                           "that changes how validators and mediators interact.",
            migration_guidance=None  # Required but missing
        )

        assert amendment is None
        assert any("migration guidance" in e for e in errors)

    def test_generate_amendment_id(self):
        """Test amendment ID generation."""
        manager = AmendmentManager()

        id1 = manager.generate_amendment_id(AmendmentClass.B, 2025)
        assert id1 == "NCIP-014-B-2025-001"

        # Create an amendment
        manager.create_amendment(
            amendment_id="NCIP-014-B-2025-001",
            amendment_class=AmendmentClass.B,
            title="First Amendment",
            rationale="Test rationale that meets the minimum length requirement of fifty characters",
            scope_of_impact="Test scope that meets the minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_002],
            proposed_changes="Test changes that meet the minimum length requirement of fifty characters"
        )

        id2 = manager.generate_amendment_id(AmendmentClass.B, 2025)
        assert id2 == "NCIP-014-B-2025-002"


class TestRatificationProcess:
    """Tests for the ratification process stages."""

    def create_test_amendment(self, manager: AmendmentManager) -> Amendment:
        """Helper to create a test amendment."""
        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-TEST",
            amendment_class=AmendmentClass.A,
            title="Test Amendment",
            rationale="This is a test rationale that explains the purpose of the amendment "
                     "in sufficient detail for review.",
            scope_of_impact="This affects test scope with limited impact",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="These are the proposed changes that detail exactly what will be modified "
                           "in the protocol.",
            effective_date=datetime.utcnow() + timedelta(days=30)
        )
        return amendment

    def test_proposal_posting(self):
        """Test Stage 1: Proposal posting."""
        manager = AmendmentManager()
        amendment = self.create_test_amendment(manager)

        assert amendment.current_stage == RatificationStage.PROPOSAL_POSTING

        success, msg = manager.propose_amendment(amendment.amendment_id)

        assert success
        assert amendment.status == AmendmentStatus.PROPOSED
        assert amendment.current_stage == RatificationStage.COOLING_PERIOD
        assert amendment.cooling_ends_at is not None

    def test_cooling_period_enforcement(self):
        """Test Stage 2: Cooling period cannot be skipped."""
        manager = AmendmentManager()
        amendment = self.create_test_amendment(manager)

        manager.propose_amendment(amendment.amendment_id)

        # Try to start deliberation immediately
        success, msg = manager.start_deliberation(amendment.amendment_id)

        assert not success
        assert "not complete" in msg.lower()

    def test_deliberation_start(self):
        """Test Stage 3: Deliberation starts after cooling."""
        manager = AmendmentManager()
        amendment = self.create_test_amendment(manager)

        manager.propose_amendment(amendment.amendment_id)

        # Simulate cooling period completion
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)

        success, msg = manager.start_deliberation(amendment.amendment_id)

        assert success
        assert amendment.status == AmendmentStatus.DELIBERATION
        assert amendment.current_stage == RatificationStage.DELIBERATION_WINDOW

    def test_voting_requires_compatibility_check(self):
        """Test that voting requires semantic compatibility check."""
        manager = AmendmentManager()
        amendment = self.create_test_amendment(manager)

        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)

        # Try to start voting without compatibility check
        success, msg = manager.start_voting(amendment.amendment_id)

        assert not success
        assert "compatibility" in msg.lower()

    def test_full_ratification_flow(self):
        """Test complete ratification from proposal to activation."""
        manager = AmendmentManager()
        amendment = self.create_test_amendment(manager)

        # Stage 1: Propose
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)

        # Stage 2-3: Start deliberation
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)

        # Run compatibility check
        manager.check_semantic_compatibility(amendment.amendment_id, {"test": 0.1})

        # Stage 4: Start voting
        manager.start_voting(amendment.amendment_id)

        # Cast votes with PoU
        pou = PoUStatement(
            voter_id="voter1",
            what_changes="Term definition X changes to include condition Y",
            what_unchanged="All other term definitions remain the same",
            who_affected="Validators interpreting term X",
            rationale="This clarifies ambiguity that has caused issues"
        )

        for i in range(10):
            manager.cast_vote(
                amendment.amendment_id,
                voter_id=f"voter_{i}",
                vote="approve",
                pou=pou
            )

        # Stage 5: Finalize ratification
        success, msg = manager.finalize_ratification(amendment.amendment_id)
        assert success
        assert amendment.status == AmendmentStatus.RATIFIED

        # Stage 6: Activate
        amendment.effective_date = datetime.utcnow() - timedelta(days=1)
        success, msg = manager.activate_amendment(amendment.amendment_id)

        assert success
        assert amendment.status == AmendmentStatus.ACTIVATED


class TestVoting:
    """Tests for voting mechanics."""

    def test_vote_requires_pou(self):
        """Test that votes require valid PoU."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-VOTE",
            amendment_class=AmendmentClass.A,
            title="Vote Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        # Try to vote with incomplete PoU
        incomplete_pou = PoUStatement(
            voter_id="voter1",
            what_changes="",  # Missing
            what_unchanged="Everything else",
            who_affected="Everyone",
            rationale="I agree"
        )

        success, msg = manager.cast_vote(
            amendment.amendment_id,
            voter_id="voter1",
            vote="approve",
            pou=incomplete_pou
        )

        assert not success
        assert "what changes" in msg.lower()

    def test_vote_weight_calculation(self):
        """Test that vote weights incorporate trust scores."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-WEIGHT",
            amendment_class=AmendmentClass.A,
            title="Weight Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        # Fast-forward to voting
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="voter1",
            what_changes="Term definition changes from X to Y",
            what_unchanged="All other definitions remain unchanged",
            who_affected="Validators and mediators",
            rationale="This improvement clarifies ambiguity"
        )

        # Vote with trust score
        success, msg = manager.cast_vote(
            amendment.amendment_id,
            voter_id="voter1",
            vote="approve",
            pou=pou,
            weight=1.0,
            validator_trust_score=0.9
        )

        assert success
        assert amendment.votes[0].weight == 0.9  # 1.0 * 0.9

    def test_tally_votes(self):
        """Test vote tallying."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-B-2025-TALLY",
            amendment_class=AmendmentClass.B,
            title="Tally Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_002],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        # Fast-forward to voting
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="test",
            what_changes="Procedure X changes to procedure Y",
            what_unchanged="All semantic definitions unchanged",
            who_affected="Validators implementing procedure X",
            rationale="Procedure improvement for efficiency"
        )

        # Cast votes: 7 approve, 3 reject
        for i in range(7):
            manager.cast_vote(amendment.amendment_id, f"voter_{i}", "approve", pou)
        for i in range(7, 10):
            manager.cast_vote(amendment.amendment_id, f"voter_{i}", "reject", pou)

        tally = manager.tally_votes(amendment.amendment_id)

        assert tally["approve"] == 7
        assert tally["reject"] == 3
        assert tally["approval_ratio"] == 0.7
        assert tally["threshold"] == 0.67  # Class B supermajority
        assert tally["meets_threshold"] is True

    def test_class_e_fork_on_failure(self):
        """Test that Class E creates fork when consensus fails."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-E-2025-FORK",
            amendment_class=AmendmentClass.E,
            title="Existential Change",
            rationale="Fundamental change to core protocol principles requiring unanimous consent "
                     "or constitutional fork.",
            scope_of_impact="Affects fundamental protocol operation",
            affected_artifacts=[ConstitutionalArtifact.CORE_DOCTRINES],
            proposed_changes="Complete restructuring of refusal doctrine with new approach to automation "
                           "boundaries.",
            migration_guidance="Full protocol migration with 12-month transition."
        )

        # Fast-forward to voting
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="test",
            what_changes="Core refusal doctrine restructured",
            what_unchanged="Historical entries unaffected",
            who_affected="All protocol participants",
            rationale="Evolution of protocol principles"
        )

        # Cast votes: 9 approve, 1 reject (not unanimous)
        for i in range(9):
            manager.cast_vote(amendment.amendment_id, f"voter_{i}", "approve", pou)
        manager.cast_vote(amendment.amendment_id, "voter_9", "reject", pou)

        success, msg = manager.finalize_ratification(amendment.amendment_id)

        assert success
        assert "Fork created" in msg
        assert len(manager.get_forks()) == 1


class TestSemanticCompatibility:
    """Tests for semantic compatibility checks."""

    def test_drift_threshold(self):
        """Test that D3+ drift requires migration."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-C-2025-DRIFT",
            amendment_class=AmendmentClass.C,
            title="Semantic Change",
            rationale="Semantic change to term definition requiring careful compatibility analysis "
                     "for existing entries.",
            scope_of_impact="Affects interpretation of term definitions",
            affected_artifacts=[ConstitutionalArtifact.CANONICAL_TERM_REGISTRY],
            proposed_changes="Change canonical definition of term X with new semantic scope that extends "
                           "beyond current boundaries.",
            migration_guidance=None  # Missing
        )

        result = manager.check_semantic_compatibility(
            amendment.amendment_id,
            drift_scores={"ncip_001": 0.50}  # D3 drift
        )

        assert not result.is_compatible
        assert result.requires_migration
        assert any("migration" in v.lower() for v in result.violations)

    def test_compatibility_with_migration(self):
        """Test that D3+ drift passes with migration guidance."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-C-2025-MIGRATE",
            amendment_class=AmendmentClass.C,
            title="Semantic Change with Migration",
            rationale="Semantic change with proper migration guidance for smooth transition "
                     "of existing entries.",
            scope_of_impact="Affects interpretation of term definitions",
            affected_artifacts=[ConstitutionalArtifact.CANONICAL_TERM_REGISTRY],
            proposed_changes="Change canonical definition of term X with new semantic scope that extends "
                           "beyond current boundaries.",
            migration_guidance="Three-phase migration: 1) Announce, 2) Dual-mode, 3) Cutover"
        )

        result = manager.check_semantic_compatibility(
            amendment.amendment_id,
            drift_scores={"ncip_001": 0.50}
        )

        assert result.is_compatible
        assert result.requires_migration
        assert result.migration_guidance is not None


class TestEmergencyAmendments:
    """Tests for emergency amendments."""

    def test_create_emergency_amendment(self):
        """Test creating an emergency amendment."""
        manager = AmendmentManager()

        emergency, errors = manager.create_emergency_amendment(
            amendment_id="NCIP-014-EMERGENCY-001",
            reason="validator_halt",
            proposed_changes="Temporarily halt validators for security review"
        )

        assert emergency is not None
        assert len(errors) == 0
        assert emergency.is_active
        assert not emergency.is_semantic

    def test_emergency_rejects_semantic_changes(self):
        """Test that emergency amendments cannot alter semantics."""
        manager = AmendmentManager()

        emergency, errors = manager.create_emergency_amendment(
            amendment_id="NCIP-014-EMERGENCY-002",
            reason="exploit_mitigation",
            proposed_changes="Change the semantic definition of terms"  # Contains "semantic"
        )

        assert emergency is None
        assert any("semantic" in e.lower() for e in errors)

    def test_emergency_auto_expiry(self):
        """Test that unratified emergency amendments expire."""
        manager = AmendmentManager()

        emergency, _ = manager.create_emergency_amendment(
            amendment_id="NCIP-014-EMERGENCY-003",
            reason="network_safety_pause",
            proposed_changes="Pause network operations",
            max_duration_days=1
        )

        # Simulate expiry
        emergency.expires_at = datetime.utcnow() - timedelta(hours=1)
        emergency.check_expiry()

        assert emergency.expired
        assert not emergency.is_active

    def test_emergency_ratification_prevents_expiry(self):
        """Test that ratified emergency amendments don't expire."""
        manager = AmendmentManager()

        emergency, _ = manager.create_emergency_amendment(
            amendment_id="NCIP-014-EMERGENCY-004",
            reason="validator_halt",
            proposed_changes="Halt validators"
        )

        success, msg = manager.ratify_emergency_amendment(emergency.amendment_id)

        assert success
        assert emergency.ratified

        # Simulate expiry check
        emergency.expires_at = datetime.utcnow() - timedelta(hours=1)
        emergency.check_expiry()

        assert not emergency.expired  # Ratified, so not expired


class TestConstitutionVersioning:
    """Tests for constitution versioning."""

    def test_initial_version(self):
        """Test initial constitution version."""
        manager = AmendmentManager()

        assert manager.get_constitution_version() == "3.0"

    def test_version_increment(self):
        """Test version increments after activation."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-VERSION",
            amendment_class=AmendmentClass.A,
            title="Version Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        # Fast-forward through ratification
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="test",
            what_changes="Editorial changes only",
            what_unchanged="All substance unchanged",
            who_affected="Documentation readers",
            rationale="Clarity improvement"
        )

        for i in range(10):
            manager.cast_vote(amendment.amendment_id, f"voter_{i}", "approve", pou)

        manager.finalize_ratification(amendment.amendment_id)
        amendment.effective_date = datetime.utcnow() - timedelta(days=1)
        manager.activate_amendment(amendment.amendment_id)

        assert manager.get_constitution_version() == "3.1"
        assert amendment.constitution_version_after == "3.1"

    def test_entry_version_binding(self):
        """Test entries get correct constitution version."""
        manager = AmendmentManager()

        # Entry created now
        now_version = manager.get_entry_constitution_version(datetime.utcnow())
        assert now_version == "3.0"

        # Entry from past would use version at that time
        past = datetime.utcnow() - timedelta(days=30)
        past_version = manager.get_entry_constitution_version(past)
        assert past_version == "3.0"


class TestProhibitedActions:
    """Tests for prohibited constitutional actions."""

    def test_detect_retroactive_reinterpretation(self):
        """Test detection of retroactive reinterpretation."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-RETRO",
            amendment_class=AmendmentClass.A,
            title="Bad Amendment",
            rationale="This amendment would retroactive reinterpret prior agreements "
                     "which is constitutionally prohibited.",
            scope_of_impact="Would affect historical entries",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Reinterpret prior entries using new definition which changes "
                           "the meaning of historical records."
        )

        valid, errors = manager.validate_amendment_proposal(amendment)

        assert not valid
        assert any("prohibited" in e.lower() for e in errors)

    def test_void_violating_amendment(self):
        """Test voiding amendments with constitutional violations."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-VOID",
            amendment_class=AmendmentClass.A,
            title="Test Amendment",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        success, msg = manager.void_amendment(
            amendment.amendment_id,
            "Contains prohibited retroactive provisions"
        )

        assert success
        assert amendment.status == AmendmentStatus.VOID


class TestQueryMethods:
    """Tests for query and status methods."""

    def test_get_amendments_by_status(self):
        """Test filtering amendments by status."""
        manager = AmendmentManager()

        for i in range(3):
            manager.create_amendment(
                amendment_id=f"NCIP-014-A-2025-Q{i}",
                amendment_class=AmendmentClass.A,
                title=f"Query Test {i}",
                rationale="Test rationale meeting minimum length requirement for validation purposes",
                scope_of_impact="Test scope meeting minimum length requirement",
                affected_artifacts=[ConstitutionalArtifact.NCIP_001],
                proposed_changes="Test changes meeting minimum length requirement for validation"
            )

        drafts = manager.get_amendments_by_status(AmendmentStatus.DRAFT)
        assert len(drafts) == 3

    def test_status_summary(self):
        """Test status summary generation."""
        manager = AmendmentManager()

        manager.create_amendment(
            amendment_id="NCIP-014-A-2025-SUM",
            amendment_class=AmendmentClass.A,
            title="Summary Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        summary = manager.get_status_summary()

        assert summary["constitution_version"] == "3.0"
        assert summary["total_amendments"] == 1
        assert "by_status" in summary
        assert "by_class" in summary
        assert "thresholds" in summary


class TestPoUStatement:
    """Tests for PoU statement validation."""

    def test_pou_to_statement(self):
        """Test PoU statement generation."""
        pou = PoUStatement(
            voter_id="voter1",
            what_changes="Term X changes to include condition Y",
            what_unchanged="All other terms remain the same",
            who_affected="Validators and mediators",
            rationale="This clarifies existing ambiguity"
        )

        statement = pou.to_statement()

        assert "WHAT CHANGES:" in statement
        assert "WHAT UNCHANGED:" in statement
        assert "WHO AFFECTED:" in statement
        assert "RATIONALE:" in statement
        assert "Term X" in statement

    def test_pou_hash(self):
        """Test PoU hash computation."""
        pou = PoUStatement(
            voter_id="voter1",
            what_changes="Term X changes",
            what_unchanged="Everything else",
            who_affected="Everyone",
            rationale="Because"
        )

        hash1 = pou.compute_hash()
        hash2 = pou.compute_hash()

        assert hash1 == hash2
        assert len(hash1) == 64  # SHA-256 hex


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_cannot_skip_stages(self):
        """Test that ratification stages cannot be skipped."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-SKIP",
            amendment_class=AmendmentClass.A,
            title="Skip Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        # Try to start voting directly
        success, msg = manager.start_voting(amendment.amendment_id)
        assert not success

    def test_cannot_activate_before_effective_date(self):
        """Test that activation respects effective date."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-DATE",
            amendment_class=AmendmentClass.A,
            title="Date Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation",
            effective_date=datetime.utcnow() + timedelta(days=30)
        )

        # Fast-forward to ratified
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="test",
            what_changes="Test changes",
            what_unchanged="Everything else",
            who_affected="Test users",
            rationale="Test reason"
        )

        for i in range(10):
            manager.cast_vote(amendment.amendment_id, f"voter_{i}", "approve", pou)

        manager.finalize_ratification(amendment.amendment_id)

        # Try to activate before effective date
        success, msg = manager.activate_amendment(amendment.amendment_id)
        assert not success
        assert "effective date" in msg.lower()

    def test_no_duplicate_votes(self):
        """Test that voters cannot vote twice."""
        manager = AmendmentManager()

        amendment, _ = manager.create_amendment(
            amendment_id="NCIP-014-A-2025-DUP",
            amendment_class=AmendmentClass.A,
            title="Duplicate Test",
            rationale="Test rationale meeting minimum length requirement for validation purposes",
            scope_of_impact="Test scope meeting minimum length requirement",
            affected_artifacts=[ConstitutionalArtifact.NCIP_001],
            proposed_changes="Test changes meeting minimum length requirement for validation"
        )

        # Fast-forward to voting
        manager.propose_amendment(amendment.amendment_id)
        amendment.cooling_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.start_deliberation(amendment.amendment_id)
        amendment.deliberation_ends_at = datetime.utcnow() - timedelta(hours=1)
        manager.check_semantic_compatibility(amendment.amendment_id)
        manager.start_voting(amendment.amendment_id)

        pou = PoUStatement(
            voter_id="voter1",
            what_changes="Test changes apply",
            what_unchanged="Everything else unchanged",
            who_affected="Test users affected",
            rationale="Reason for vote"
        )

        manager.cast_vote(amendment.amendment_id, "voter1", "approve", pou)

        # Try to vote again
        success, msg = manager.cast_vote(amendment.amendment_id, "voter1", "reject", pou)
        assert not success
        assert "already" in msg.lower()

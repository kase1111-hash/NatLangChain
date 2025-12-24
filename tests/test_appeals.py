"""
Tests for NCIP-008: Semantic Appeals, Precedent & Case Law Encoding

Tests cover:
- Appeal creation and lifecycle
- Appealable vs non-appealable items
- Review panel composition
- Semantic Case Record generation
- Precedent weight decay
- Abuse prevention (cooldowns, escalating fees)
- SCR index generation
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from appeals import (
    AppealsManager,
    Appeal,
    AppealableItem,
    NonAppealableItem,
    AppealStatus,
    AppealOutcome,
    DriftLevel,
    PrecedentWeight,
    SemanticCaseRecord,
    ReviewPanel,
    ReviewPanelMember,
    AppealReference,
    PrecedentEntry,
)


class TestAppealableItems:
    """Test appealable vs non-appealable item classification."""

    def test_validator_rejection_is_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("validator_rejection")
        assert is_appealable is True

    def test_drift_classification_is_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("drift_classification")
        assert is_appealable is True

    def test_pou_mismatch_is_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("pou_mismatch")
        assert is_appealable is True

    def test_mediator_interpretation_is_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("mediator_interpretation")
        assert is_appealable is True

    def test_term_registry_mapping_not_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("term_registry_mapping")
        assert is_appealable is False
        assert "not appealable" in msg

    def test_settlement_outcome_not_appealable(self):
        manager = AppealsManager()
        is_appealable, msg = manager.is_appealable("settlement_outcome")
        assert is_appealable is False


class TestAppealCreation:
    """Test appeal creation and validation."""

    def test_create_valid_appeal(self):
        manager = AppealsManager()

        appeal, warnings = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-8831",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime", "commercially_reasonable"],
            appeal_rationale="Validator over-weighted industry-default uptime"
        )

        assert appeal is not None
        assert appeal.appeal_id.startswith("APPEAL-")
        assert appeal.status == AppealStatus.DECLARED
        assert len(appeal.disputed_terms) == 2

    def test_appeal_requires_references(self):
        manager = AppealsManager()

        # Missing entry ID
        appeal, errors = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime"],
            appeal_rationale="Test"
        )

        assert appeal is None
        assert any("entry ID" in e for e in errors)

    def test_appeal_requires_disputed_terms(self):
        manager = AppealsManager()

        appeal, errors = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=[],  # Empty
            appeal_rationale="Test"
        )

        assert appeal is None
        assert any("disputed term" in e for e in errors)

    def test_appeal_burn_fee_charged(self):
        manager = AppealsManager()

        appeal, warnings = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.VALIDATOR_REJECTION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D2,
            disputed_terms=["term1"],
            appeal_rationale="Test"
        )

        assert appeal.burn_fee_paid == manager.BASE_BURN_FEE
        assert any("Burn fee" in w for w in warnings)


class TestReviewPanel:
    """Test review panel composition per NCIP-008 Section 4.1."""

    def test_panel_requires_minimum_3_members(self):
        panel = ReviewPanel()
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid")
        ]
        assert panel.is_valid is False

    def test_panel_requires_distinct_implementations(self):
        panel = ReviewPanel()
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "llm"),
            ReviewPanelMember("v3", "llm")
        ]
        assert panel.is_valid is False

    def test_panel_rejects_original_validators(self):
        panel = ReviewPanel(original_validator_ids={"v1", "v2"})
        panel.members = [
            ReviewPanelMember("v3", "llm"),
            ReviewPanelMember("v4", "hybrid"),
            ReviewPanelMember("v5", "symbolic")
        ]
        assert panel.is_valid is True

        # Try to add original validator
        success, msg = panel.add_member(ReviewPanelMember("v1", "human"))
        assert success is False
        assert "overlap" in msg.lower()

    def test_valid_panel(self):
        panel = ReviewPanel(original_validator_ids={"orig1"})
        panel.members = [
            ReviewPanelMember("v1", "llm", 0.8),
            ReviewPanelMember("v2", "hybrid", 0.9),
            ReviewPanelMember("v3", "human", 0.95)
        ]
        assert panel.is_valid is True


class TestSemanticLock:
    """Test scoped semantic lock during appeals."""

    def test_apply_scoped_lock(self):
        manager = AppealsManager()

        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime", "sla"],
            appeal_rationale="Test"
        )

        result = manager.apply_scoped_lock(appeal, "LOCK-001")

        assert result["lock_id"] == "LOCK-001"
        assert appeal.status == AppealStatus.SEMANTIC_LOCK_APPLIED
        assert "uptime" in appeal.locked_terms
        assert "sla" in appeal.locked_terms

    def test_lock_released_on_resolution(self):
        manager = AppealsManager()

        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["term1"],
            appeal_rationale="Test"
        )

        manager.apply_scoped_lock(appeal, "LOCK-001")

        # Setup panel and begin review
        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        # Resolve
        scr, errors = manager.resolve_appeal(
            appeal,
            AppealOutcome.OVERTURNED,
            DriftLevel.D1,
            "Classification revised",
            "ratifier-001"
        )

        assert appeal.semantic_lock_id is None
        assert len(appeal.locked_terms) == 0


class TestSemanticCaseRecord:
    """Test Semantic Case Record generation per NCIP-008 Section 5."""

    def test_scr_generation(self):
        manager = AppealsManager()

        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-8831",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime", "commercially_reasonable"],
            appeal_rationale="Validator over-weighted industry-default"
        )

        # Setup and complete review
        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        scr, errors = manager.resolve_appeal(
            appeal,
            AppealOutcome.OVERTURNED,
            DriftLevel.D1,
            "Validator over-weighted industry-default uptime rather than contract-scoped definition.",
            "ratifier-001",
            prior_cases=["SCR-2024-0091", "SCR-2025-0033"]
        )

        assert scr is not None
        assert scr.case_id.startswith("SCR-")
        assert scr.originating_entry == "ENTRY-8831"
        assert scr.appeal_reason == AppealableItem.DRIFT_CLASSIFICATION
        assert scr.upheld is False
        assert scr.revised_classification == DriftLevel.D1
        assert scr.human_ratification is True
        assert len(scr.prior_cases) == 2

    def test_scr_to_yaml_dict(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0142",
            originating_entry="ENTRY-8831",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["uptime", "commercially_reasonable"],
            outcome=AppealOutcome.OVERTURNED,
            upheld=False,
            revised_classification=DriftLevel.D1,
            rationale_summary="Validator over-weighted industry-default uptime",
            canonical_terms_version="1.2",
            prior_cases=["SCR-2024-0091"],
            human_ratification=True
        )

        yaml_dict = scr.to_yaml_dict()

        assert "semantic_case_record" in yaml_dict
        record = yaml_dict["semantic_case_record"]
        assert record["case_id"] == "SCR-2025-0142"
        assert record["outcome"]["upheld"] is False
        assert record["outcome"]["revised_classification"] == "D1"

    def test_scr_integrity_verification(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0001",
            originating_entry="ENTRY-001",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["term1"],
            outcome=AppealOutcome.UPHELD,
            upheld=True,
            rationale_summary="Original classification correct"
        )

        assert scr.verify_integrity() is True


class TestPrecedentWeightDecay:
    """Test precedent weight decay per NCIP-008 Section 6.2."""

    def test_high_weight_under_3_months(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0001",
            originating_entry="ENTRY-001",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["term1"],
            outcome=AppealOutcome.OVERTURNED,
            upheld=False,
            canonical_terms_version="1.0",
            resolution_timestamp=datetime.utcnow() - timedelta(days=30)  # 1 month ago
        )

        entry = PrecedentEntry(scr=scr, weight=PrecedentWeight.HIGH)
        weight = entry.compute_weight("1.0")

        assert weight == PrecedentWeight.HIGH

    def test_medium_weight_3_to_12_months(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0001",
            originating_entry="ENTRY-001",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["term1"],
            outcome=AppealOutcome.OVERTURNED,
            upheld=False,
            canonical_terms_version="1.0",
            resolution_timestamp=datetime.utcnow() - timedelta(days=180)  # 6 months ago
        )

        entry = PrecedentEntry(scr=scr, weight=PrecedentWeight.HIGH)
        weight = entry.compute_weight("1.0")

        assert weight == PrecedentWeight.MEDIUM

    def test_low_weight_over_12_months(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0001",
            originating_entry="ENTRY-001",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["term1"],
            outcome=AppealOutcome.OVERTURNED,
            upheld=False,
            canonical_terms_version="1.0",
            resolution_timestamp=datetime.utcnow() - timedelta(days=400)  # 13+ months ago
        )

        entry = PrecedentEntry(scr=scr, weight=PrecedentWeight.HIGH)
        weight = entry.compute_weight("1.0")

        assert weight == PrecedentWeight.LOW

    def test_zero_weight_superseded_registry(self):
        scr = SemanticCaseRecord(
            case_id="SCR-2025-0001",
            originating_entry="ENTRY-001",
            appeal_reason=AppealableItem.DRIFT_CLASSIFICATION,
            disputed_terms=["term1"],
            outcome=AppealOutcome.OVERTURNED,
            upheld=False,
            canonical_terms_version="1.0",  # Old version
            resolution_timestamp=datetime.utcnow() - timedelta(days=30)
        )

        entry = PrecedentEntry(scr=scr, weight=PrecedentWeight.HIGH)
        weight = entry.compute_weight("2.0")  # Newer registry version

        assert weight == PrecedentWeight.ZERO


class TestPrecedentQuerying:
    """Test precedent indexing and querying."""

    def test_query_by_term(self):
        manager = AppealsManager()

        # Create and resolve an appeal
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime"],
            appeal_rationale="Test"
        )

        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        manager.resolve_appeal(
            appeal, AppealOutcome.OVERTURNED, DriftLevel.D1,
            "Classification revised", "ratifier-001"
        )

        # Query
        results = manager.query_precedents(canonical_term_id="uptime")
        assert len(results) == 1
        assert results[0].scr.disputed_terms == ["uptime"]

    def test_precedent_signal_advisory_only(self):
        manager = AppealsManager()

        signal = manager.get_precedent_signal("unknown_term", DriftLevel.D2)

        assert signal["advisory_only"] is True
        assert signal["binding"] is False
        assert signal["precedent_available"] is False

    def test_precedent_signal_with_prior_cases(self):
        manager = AppealsManager()

        # Create resolved case
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime"],
            appeal_rationale="Test"
        )

        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        manager.resolve_appeal(
            appeal, AppealOutcome.OVERTURNED, DriftLevel.D1,
            "Classification revised", "ratifier-001"
        )

        signal = manager.get_precedent_signal("uptime", DriftLevel.D3)

        assert signal["precedent_available"] is True
        assert signal["precedent_count"] >= 1
        assert "warning" in signal
        assert "advisory" in signal["warning"].lower()


class TestAbusePreention:
    """Test appeal abuse prevention per NCIP-008 Section 8."""

    def test_cooldown_after_failed_appeal(self):
        manager = AppealsManager()

        # Create and fail an appeal
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["term1"],
            appeal_rationale="Test"
        )

        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        # Resolve as upheld (appeal fails)
        manager.resolve_appeal(
            appeal, AppealOutcome.UPHELD, None,
            "Original classification correct", "ratifier-001"
        )

        # Try to appeal again - should be in cooldown
        appeal2, errors = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",  # Same entry
            validator_decision_id="VAL-DEC-002",
            drift_classification=DriftLevel.D3,
            disputed_terms=["term1"],
            appeal_rationale="Try again"
        )

        assert appeal2 is None
        assert any("cooldown" in e.lower() for e in errors)

    def test_escalating_fees(self):
        manager = AppealsManager()

        # Manually set up cooldown with failed appeals
        cooldown_key = "user-001:ENTRY-001"
        from appeals import AppealCooldown
        cooldown = AppealCooldown(appellant_id="user-001", entry_id="ENTRY-001")
        cooldown.failed_appeals = 2
        cooldown.cooldown_until = datetime.utcnow() - timedelta(days=1)  # Expired
        manager.cooldowns[cooldown_key] = cooldown

        # Calculate fee
        fee = manager._calculate_burn_fee("user-001", "ENTRY-001")

        expected = manager.BASE_BURN_FEE * (manager.ESCALATING_FEE_MULTIPLIER ** 2)
        assert fee == expected

    def test_rejection_triggers_cooldown(self):
        manager = AppealsManager()

        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["term1"],
            appeal_rationale="Test"
        )

        manager.reject_appeal(appeal, "Frivolous appeal")

        cooldown_key = "user-001:ENTRY-001"
        assert cooldown_key in manager.cooldowns
        assert manager.cooldowns[cooldown_key].failed_appeals == 1


class TestAppealLifecycle:
    """Test complete appeal lifecycle."""

    def test_full_appeal_lifecycle(self):
        manager = AppealsManager()

        # 1. Create appeal
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-8831",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime", "commercially_reasonable"],
            appeal_rationale="Validator over-weighted industry-default uptime"
        )
        assert appeal.status == AppealStatus.DECLARED

        # 2. Apply semantic lock
        manager.apply_scoped_lock(appeal, "LOCK-001")
        assert appeal.status == AppealStatus.SEMANTIC_LOCK_APPLIED

        # 3. Create review panel
        panel = manager.create_review_panel(appeal, ["orig-val-1"])
        panel.add_member(ReviewPanelMember("v1", "llm", 0.8))
        panel.add_member(ReviewPanelMember("v2", "hybrid", 0.9))
        panel.add_member(ReviewPanelMember("v3", "human", 0.95))

        # 4. Begin review
        success, msg = manager.begin_review(appeal)
        assert success is True
        assert appeal.status == AppealStatus.UNDER_REVIEW

        # 5. Record votes
        manager.record_vote(appeal, "v1", AppealOutcome.OVERTURNED, DriftLevel.D1, "Agree")
        manager.record_vote(appeal, "v2", AppealOutcome.OVERTURNED, DriftLevel.D1, "Concur")
        manager.record_vote(appeal, "v3", AppealOutcome.OVERTURNED, DriftLevel.D1, "Confirmed")

        assert appeal.status == AppealStatus.AWAITING_RATIFICATION

        # 6. Resolve with human ratification
        scr, errors = manager.resolve_appeal(
            appeal,
            AppealOutcome.OVERTURNED,
            DriftLevel.D1,
            "Validator over-weighted industry-default uptime rather than contract-scoped definition.",
            "ratifier-001",
            prior_cases=["SCR-2024-0091"]
        )

        assert appeal.status == AppealStatus.RESOLVED
        assert scr is not None
        assert scr.human_ratification is True
        assert len(scr.panel_votes) == 3

        # 7. Verify SCR is indexed
        assert scr.case_id in manager.scrs
        results = manager.query_precedents(canonical_term_id="uptime")
        assert len(results) >= 1


class TestSCRIndex:
    """Test SCR index generation per NCIP-008 Section 11."""

    def test_generate_scr_index(self):
        manager = AppealsManager()
        manager.current_registry_version = "1.2"

        index = manager.generate_scr_index()

        assert "semantic_precedent_index" in index
        idx = index["semantic_precedent_index"]

        assert idx["version"] == "1.0"
        assert "canonical_term_id" in idx["lookup_fields"]
        assert "drift_class" in idx["lookup_fields"]
        assert "jurisdiction_context" in idx["lookup_fields"]
        assert "date_range" in idx["lookup_fields"]
        assert idx["advisory_only"] is True
        assert idx["binding"] is False


class TestValidatorBehavior:
    """Test validator behavior requirements per NCIP-008 Section 7."""

    def test_precedent_divergence_warning(self):
        manager = AppealsManager()

        # Create resolved case with D1 classification
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime"],
            appeal_rationale="Test"
        )

        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        manager.resolve_appeal(
            appeal, AppealOutcome.OVERTURNED, DriftLevel.D1,
            "Classification revised", "ratifier-001"
        )

        # Check for divergence warning
        warning = manager.check_precedent_divergence("uptime", DriftLevel.D3)

        assert warning is not None
        assert "diverges" in warning.lower()
        assert "explicit prose takes priority" in warning.lower()

    def test_no_warning_when_matching(self):
        manager = AppealsManager()

        # Create resolved case
        appeal, _ = manager.create_appeal(
            appellant_id="user-001",
            appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
            original_entry_id="ENTRY-001",
            validator_decision_id="VAL-DEC-001",
            drift_classification=DriftLevel.D3,
            disputed_terms=["uptime"],
            appeal_rationale="Test"
        )

        panel = manager.create_review_panel(appeal, ["orig1"])
        panel.members = [
            ReviewPanelMember("v1", "llm"),
            ReviewPanelMember("v2", "hybrid"),
            ReviewPanelMember("v3", "human")
        ]
        manager.begin_review(appeal)

        manager.resolve_appeal(
            appeal, AppealOutcome.OVERTURNED, DriftLevel.D1,
            "Classification revised", "ratifier-001"
        )

        # Check for divergence - should be None when matching
        warning = manager.check_precedent_divergence("uptime", DriftLevel.D1)

        assert warning is None


class TestStatusSummary:
    """Test status summary generation."""

    def test_empty_status(self):
        manager = AppealsManager()
        summary = manager.get_status_summary()

        assert summary["total_appeals"] == 0
        assert summary["total_scrs"] == 0
        assert "principle" in summary

    def test_status_with_appeals(self):
        manager = AppealsManager()

        # Create some appeals
        for i in range(3):
            manager.create_appeal(
                appellant_id=f"user-{i}",
                appeal_type=AppealableItem.DRIFT_CLASSIFICATION,
                original_entry_id=f"ENTRY-{i}",
                validator_decision_id=f"VAL-DEC-{i}",
                drift_classification=DriftLevel.D3,
                disputed_terms=[f"term{i}"],
                appeal_rationale="Test"
            )

        summary = manager.get_status_summary()

        assert summary["total_appeals"] == 3
        assert "declared" in summary["appeal_status_counts"]

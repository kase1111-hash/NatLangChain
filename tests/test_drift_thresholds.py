"""
Tests for NCIP-002: Semantic Drift Thresholds & Validator Responses

Tests cover:
- Drift level classification (D0-D4)
- Mandatory validator actions per level
- Drift aggregation rules
- Human override constraints
- Temporal Fixity context
- Logging behavior
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from drift_thresholds import (
    DriftLevel,
    ValidatorAction,
    DriftThreshold,
    DriftClassification,
    SemanticDriftClassifier,
    TemporalFixityContext,
    HumanOverrideRecord,
    DRIFT_THRESHOLDS,
    DRIFT_MESSAGES,
    classify_drift_score,
    get_mandatory_response,
    get_drift_config
)


class TestDriftLevelClassification:
    """Tests for drift score classification into D0-D4 levels."""

    def test_d0_stable_lower_bound(self):
        """D0 should classify scores at 0.00"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.00)
        assert result.level == DriftLevel.D0
        assert result.classification == "stable"

    def test_d0_stable_upper_bound(self):
        """D0 should classify scores just under 0.10"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.09)
        assert result.level == DriftLevel.D0

    def test_d1_soft_drift_lower_bound(self):
        """D1 should classify scores at 0.10"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.10)
        assert result.level == DriftLevel.D1
        assert result.classification == "soft_drift"

    def test_d1_soft_drift_upper_bound(self):
        """D1 should classify scores just under 0.25"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.24)
        assert result.level == DriftLevel.D1

    def test_d2_ambiguous_drift_lower_bound(self):
        """D2 should classify scores at 0.25"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.25)
        assert result.level == DriftLevel.D2
        assert result.classification == "ambiguous_drift"

    def test_d2_ambiguous_drift_upper_bound(self):
        """D2 should classify scores just under 0.45"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.44)
        assert result.level == DriftLevel.D2

    def test_d3_hard_drift_lower_bound(self):
        """D3 should classify scores at 0.45"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.45)
        assert result.level == DriftLevel.D3
        assert result.classification == "hard_drift"

    def test_d3_hard_drift_upper_bound(self):
        """D3 should classify scores just under 0.70"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.69)
        assert result.level == DriftLevel.D3

    def test_d4_semantic_break_lower_bound(self):
        """D4 should classify scores at 0.70"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.70)
        assert result.level == DriftLevel.D4
        assert result.classification == "semantic_break"

    def test_d4_semantic_break_upper_bound(self):
        """D4 should classify scores at 1.00"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(1.00)
        assert result.level == DriftLevel.D4

    def test_invalid_score_below_zero(self):
        """Should reject scores below 0.0"""
        classifier = SemanticDriftClassifier()
        try:
            classifier.classify(-0.1)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be between 0.0 and 1.0" in str(e)

    def test_invalid_score_above_one(self):
        """Should reject scores above 1.0"""
        classifier = SemanticDriftClassifier()
        try:
            classifier.classify(1.5)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "must be between 0.0 and 1.0" in str(e)


class TestMandatoryValidatorActions:
    """Tests for mandatory validator actions per drift level."""

    def test_d0_actions_proceed_only(self):
        """D0 should only PROCEED"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.05)
        assert classifier.should_proceed(result) is True
        assert classifier.should_warn(result) is False
        assert classifier.should_pause(result) is False
        assert classifier.should_reject(result) is False
        assert classifier.should_escalate(result) is False

    def test_d1_actions_proceed_and_warn(self):
        """D1 should PROCEED and WARN"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.15)
        assert classifier.should_proceed(result) is True
        assert classifier.should_warn(result) is True
        assert classifier.should_pause(result) is False
        assert classifier.should_reject(result) is False

    def test_d2_actions_pause_and_warn(self):
        """D2 should PAUSE and WARN (no proceed)"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.35)
        assert classifier.should_proceed(result) is False
        assert classifier.should_warn(result) is True
        assert classifier.should_pause(result) is True
        assert classifier.should_reject(result) is False

    def test_d3_actions_reject_and_require_ratification(self):
        """D3 should REJECT and REQUIRE_RATIFICATION"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.55)
        assert classifier.should_proceed(result) is False
        assert classifier.should_reject(result) is True
        assert classifier.should_require_ratification(result) is True
        assert classifier.should_escalate(result) is False

    def test_d4_actions_reject_and_escalate(self):
        """D4 should REJECT and ESCALATE_DISPUTE"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.85)
        assert classifier.should_proceed(result) is False
        assert classifier.should_reject(result) is True
        assert classifier.should_escalate(result) is True

    def test_d3_requires_human(self):
        """D3 should require human intervention"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.55)
        assert result.requires_human is True

    def test_d4_requires_human(self):
        """D4 should require human intervention"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.85)
        assert result.requires_human is True

    def test_d0_no_human_required(self):
        """D0 should not require human intervention"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.05)
        assert result.requires_human is False


class TestDriftAggregation:
    """Tests for drift aggregation rules (max score governs)."""

    def test_empty_components_returns_d0(self):
        """Empty component dict should return D0"""
        classifier = SemanticDriftClassifier()
        result = classifier.aggregate_drift({})
        assert result.max_score == 0.0
        assert result.max_level == DriftLevel.D0

    def test_single_component(self):
        """Single component should be the governing component"""
        classifier = SemanticDriftClassifier()
        result = classifier.aggregate_drift({"term_a": 0.35})
        assert result.max_score == 0.35
        assert result.governing_component == "term_a"
        assert result.max_level == DriftLevel.D2

    def test_multiple_components_max_governs(self):
        """Maximum score should govern the response"""
        classifier = SemanticDriftClassifier()
        result = classifier.aggregate_drift({
            "term_a": 0.15,
            "term_b": 0.55,
            "term_c": 0.25
        })
        assert result.max_score == 0.55
        assert result.governing_component == "term_b"
        assert result.max_level == DriftLevel.D3

    def test_aggregated_classification_matches_max(self):
        """Aggregated classification should match max score classification"""
        classifier = SemanticDriftClassifier()
        result = classifier.aggregate_drift({
            "low": 0.05,
            "high": 0.75
        })
        assert result.classification.level == DriftLevel.D4
        assert result.classification.classification == "semantic_break"


class TestLoggingBehavior:
    """Tests for drift logging per NCIP-002 Section 9."""

    def test_d0_no_logging_required(self):
        """D0 should not require logging"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.05)
        assert result.requires_logging is False

    def test_d1_logging_required(self):
        """D1 should require logging"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.15)
        assert result.requires_logging is True

    def test_d2_logging_required(self):
        """D2 should require logging"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.35)
        assert result.requires_logging is True

    def test_d3_logging_required(self):
        """D3 should require logging"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.55)
        assert result.requires_logging is True

    def test_d4_logging_required(self):
        """D4 should require logging"""
        classifier = SemanticDriftClassifier()
        result = classifier.classify(0.85)
        assert result.requires_logging is True

    def test_log_entry_created_for_d2(self):
        """Logging D2 should create a log entry"""
        classifier = SemanticDriftClassifier(validator_id="test_validator")
        classification = classifier.classify(0.35)
        entry = classifier.log_drift_event(
            classification=classification,
            affected_terms=["Intent", "Agreement"],
            source_of_divergence="Test divergence"
        )
        assert entry is not None
        assert entry.drift_level == "D2"
        assert entry.validator_id == "test_validator"
        assert "Intent" in entry.affected_terms

    def test_log_entry_not_created_for_d0(self):
        """Logging D0 should not create a log entry"""
        classifier = SemanticDriftClassifier()
        classification = classifier.classify(0.05)
        entry = classifier.log_drift_event(
            classification=classification,
            affected_terms=["Intent"],
            source_of_divergence="Test"
        )
        assert entry is None

    def test_drift_log_retrieval(self):
        """Should be able to retrieve logged events"""
        classifier = SemanticDriftClassifier()
        classification = classifier.classify(0.55)
        classifier.log_drift_event(
            classification=classification,
            affected_terms=["Ratification"],
            source_of_divergence="Test hard drift"
        )
        log = classifier.get_drift_log()
        assert len(log) == 1
        assert log[0].drift_level == "D3"

    def test_drift_log_clear(self):
        """Should be able to clear the drift log"""
        classifier = SemanticDriftClassifier()
        classification = classifier.classify(0.55)
        classifier.log_drift_event(
            classification=classification,
            affected_terms=["Test"],
            source_of_divergence="Test"
        )
        classifier.clear_drift_log()
        assert len(classifier.get_drift_log()) == 0


class TestTemporalFixityContext:
    """Tests for Temporal Fixity (T0) context handling."""

    def test_context_creation(self):
        """Should create temporal context with proper fields"""
        context = TemporalFixityContext(
            ratification_time="2025-12-24T00:00:00Z",
            registry_version="1.0",
            specification_version="3.0"
        )
        assert context.ratification_time == "2025-12-24T00:00:00Z"
        assert context.registry_version == "1.0"
        assert context.is_locked is False

    def test_context_locking(self):
        """Should be able to lock context"""
        context = TemporalFixityContext(
            ratification_time="2025-12-24T00:00:00Z",
            registry_version="1.0",
            specification_version="3.0"
        )
        context.lock()
        assert context.is_locked is True

    def test_context_to_dict(self):
        """Should serialize to dictionary"""
        context = TemporalFixityContext(
            ratification_time="2025-12-24T00:00:00Z",
            registry_version="1.0",
            specification_version="3.0"
        )
        d = context.to_dict()
        assert d["t0_ratification_time"] == "2025-12-24T00:00:00Z"
        assert d["registry_version"] == "1.0"
        assert d["locked"] is False

    def test_context_from_dict(self):
        """Should deserialize from dictionary"""
        data = {
            "t0_ratification_time": "2025-12-24T00:00:00Z",
            "registry_version": "1.0",
            "specification_version": "3.0",
            "locked": True
        }
        context = TemporalFixityContext.from_dict(data)
        assert context.ratification_time == "2025-12-24T00:00:00Z"
        assert context.is_locked is True


class TestHumanOverrideConstraints:
    """Tests for human override constraints per NCIP-002 Section 8."""

    def test_d2_can_be_overridden(self):
        """D2 (Ambiguous Drift) can be overridden by humans"""
        override = HumanOverrideRecord(
            original_level=DriftLevel.D2,
            override_decision="accept",
            human_id="human_123",
            rationale="Context makes meaning clear"
        )
        assert override.original_level == DriftLevel.D2
        assert override.binds_future is True

    def test_d3_can_be_overridden(self):
        """D3 (Hard Drift) can be overridden by humans"""
        override = HumanOverrideRecord(
            original_level=DriftLevel.D3,
            override_decision="reject",
            human_id="human_123",
            rationale="Deviation too significant"
        )
        assert override.original_level == DriftLevel.D3

    def test_d4_cannot_be_overridden(self):
        """D4 (Semantic Break) cannot be overridden without dispute"""
        try:
            HumanOverrideRecord(
                original_level=DriftLevel.D4,
                override_decision="accept",
                human_id="human_123",
                rationale="Trying to override semantic break"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "formal dispute" in str(e).lower()

    def test_d0_cannot_be_overridden(self):
        """D0 does not need override (no drift)"""
        try:
            HumanOverrideRecord(
                original_level=DriftLevel.D0,
                override_decision="accept",
                human_id="human_123",
                rationale="No reason to override"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "D2 and D3" in str(e)

    def test_d1_cannot_be_overridden(self):
        """D1 does not need override (auto-proceed with warning)"""
        try:
            HumanOverrideRecord(
                original_level=DriftLevel.D1,
                override_decision="accept",
                human_id="human_123",
                rationale="No reason to override"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "D2 and D3" in str(e)

    def test_override_to_dict(self):
        """Should serialize override record"""
        override = HumanOverrideRecord(
            original_level=DriftLevel.D2,
            override_decision="accept",
            human_id="human_123",
            rationale="Meaning preserved in context"
        )
        d = override.to_dict()
        assert d["original_level"] == "D2"
        assert d["human_id"] == "human_123"
        assert d["binds_future_interpretations"] is True


class TestValidatorResponse:
    """Tests for complete validator response generation."""

    def test_response_structure(self):
        """Validator response should have expected structure"""
        classifier = SemanticDriftClassifier()
        response = classifier.get_validator_response(0.35)
        assert "drift_score" in response
        assert "drift_level" in response
        assert "classification" in response
        assert "actions" in response
        assert "requires_human" in response
        assert "logged" in response

    def test_response_includes_affected_terms(self):
        """Response should include affected terms if provided"""
        classifier = SemanticDriftClassifier()
        response = classifier.get_validator_response(
            0.35,
            affected_terms=["Intent", "Agreement"]
        )
        assert "affected_terms" in response
        assert "Intent" in response["affected_terms"]

    def test_response_actions_dict(self):
        """Response actions should be a dict with boolean values"""
        classifier = SemanticDriftClassifier()
        response = classifier.get_validator_response(0.55)
        actions = response["actions"]
        assert isinstance(actions["proceed"], bool)
        assert isinstance(actions["reject"], bool)
        assert actions["proceed"] is False
        assert actions["reject"] is True


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_classify_drift_score(self):
        """classify_drift_score should return classification"""
        result = classify_drift_score(0.35)
        assert result.level == DriftLevel.D2
        assert result.classification == "ambiguous_drift"

    def test_get_mandatory_response(self):
        """get_mandatory_response should return validator response"""
        response = get_mandatory_response(0.55)
        assert response["drift_level"] == "D3"
        assert response["actions"]["reject"] is True

    def test_get_drift_config(self):
        """get_drift_config should return NCIP-002 config"""
        config = get_drift_config()
        assert "semantic_drift" in config
        assert "thresholds" in config["semantic_drift"]
        thresholds = config["semantic_drift"]["thresholds"]
        assert "D0" in thresholds
        assert "D4" in thresholds


class TestDriftMessages:
    """Tests for drift level messages."""

    def test_all_levels_have_messages(self):
        """All drift levels should have defined messages"""
        for level in DriftLevel:
            assert level in DRIFT_MESSAGES
            assert len(DRIFT_MESSAGES[level]) > 0

    def test_classification_includes_message(self):
        """Classification result should include message"""
        classifier = SemanticDriftClassifier()
        for score, expected_level in [(0.05, DriftLevel.D0), (0.15, DriftLevel.D1),
                                       (0.35, DriftLevel.D2), (0.55, DriftLevel.D3),
                                       (0.85, DriftLevel.D4)]:
            result = classifier.classify(score)
            assert result.message == DRIFT_MESSAGES[expected_level]


class TestDriftThresholdDefinitions:
    """Tests for threshold definitions per NCIP-002."""

    def test_thresholds_are_contiguous(self):
        """Threshold ranges should be contiguous with no gaps"""
        levels = [DriftLevel.D0, DriftLevel.D1, DriftLevel.D2, DriftLevel.D3, DriftLevel.D4]
        for i in range(len(levels) - 1):
            current = DRIFT_THRESHOLDS[levels[i]]
            next_level = DRIFT_THRESHOLDS[levels[i + 1]]
            assert current.max_score == next_level.min_score, \
                f"Gap between {current.level} and {next_level.level}"

    def test_thresholds_start_at_zero(self):
        """D0 threshold should start at 0.0"""
        assert DRIFT_THRESHOLDS[DriftLevel.D0].min_score == 0.0

    def test_thresholds_end_at_one(self):
        """D4 threshold should end at 1.0"""
        assert DRIFT_THRESHOLDS[DriftLevel.D4].max_score == 1.0


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestDriftLevelClassification,
        TestMandatoryValidatorActions,
        TestDriftAggregation,
        TestLoggingBehavior,
        TestTemporalFixityContext,
        TestHumanOverrideConstraints,
        TestValidatorResponse,
        TestConvenienceFunctions,
        TestDriftMessages,
        TestDriftThresholdDefinitions
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

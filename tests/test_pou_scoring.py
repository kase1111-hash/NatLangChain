"""
Tests for NCIP-004: Proof of Understanding Scoring

Tests cover:
- PoU status classification (Verified/Marginal/Insufficient/Failed)
- Dimension scoring (Coverage, Fidelity, Consistency, Completeness)
- Semantic fingerprint generation
- PoU structure validation
- Binding effect constraints
- Validator responses
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from pou_scoring import (
    POU_MESSAGES,
    POU_THRESHOLDS,
    BindingPoURecord,
    PoUDimension,
    PoUScorer,
    PoUScoreResult,
    PoUStatus,
    classify_pou_score,
    get_pou_config,
    score_pou,
)

# Sample PoU data for testing
VALID_POU_DATA = {
    "contract_id": "test-contract-001",
    "signer": {
        "id": "did:natlang:alice123",
        "role": "provider"
    },
    "language": "en",
    "anchor_language": "en",
    "sections": {
        "summary": {
            "text": "I understand that I am providing 5TB of storage with a minimum sustained read speed of 100MB/s for a monthly fee, and that availability affects payout."
        },
        "obligations": [
            "Provide 5TB usable storage",
            "Maintain ≥100MB/s sustained read throughput",
            "Respond to retrieval proofs"
        ],
        "rights": [
            "Receive monthly payment",
            "Earn performance multiplier if uptime targets met"
        ],
        "consequences": [
            "Reduced multiplier for downtime",
            "Contract termination if sustained breach occurs"
        ],
        "acceptance": {
            "statement": "I confirm that this reflects my understanding and I agree to these terms.",
            "timestamp": "2025-12-24T18:40:00Z"
        }
    }
}

SAMPLE_CONTRACT = """
Storage Provider Agreement:
The provider agrees to supply 5TB of usable storage capacity.
Read speed must be maintained at 100MB/s or higher.
Monthly payment will be issued upon successful retrieval proofs.
Performance multipliers apply for exceeding uptime targets.
Downtime will result in reduced compensation.
Sustained breach may lead to contract termination.
"""


class TestPoUStatusClassification:
    """Tests for PoU score classification into status levels."""

    def test_verified_at_threshold(self):
        """Score of 0.90 should be Verified"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.90)
        assert status == PoUStatus.VERIFIED

    def test_verified_high_score(self):
        """Score of 1.0 should be Verified"""
        scorer = PoUScorer()
        status = scorer.classify_score(1.0)
        assert status == PoUStatus.VERIFIED

    def test_marginal_at_lower_threshold(self):
        """Score of 0.75 should be Marginal"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.75)
        assert status == PoUStatus.MARGINAL

    def test_marginal_mid_range(self):
        """Score of 0.85 should be Marginal"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.85)
        assert status == PoUStatus.MARGINAL

    def test_marginal_just_below_verified(self):
        """Score of 0.89 should be Marginal"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.89)
        assert status == PoUStatus.MARGINAL

    def test_insufficient_at_lower_threshold(self):
        """Score of 0.50 should be Insufficient"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.50)
        assert status == PoUStatus.INSUFFICIENT

    def test_insufficient_mid_range(self):
        """Score of 0.65 should be Insufficient"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.65)
        assert status == PoUStatus.INSUFFICIENT

    def test_insufficient_just_below_marginal(self):
        """Score of 0.74 should be Insufficient"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.74)
        assert status == PoUStatus.INSUFFICIENT

    def test_failed_at_zero(self):
        """Score of 0.0 should be Failed"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.0)
        assert status == PoUStatus.FAILED

    def test_failed_just_below_insufficient(self):
        """Score of 0.49 should be Failed"""
        scorer = PoUScorer()
        status = scorer.classify_score(0.49)
        assert status == PoUStatus.FAILED


class TestFinalScoreCalculation:
    """Tests for final score calculation (minimum governs)."""

    def test_minimum_governs(self):
        """Final score should be the minimum of all dimensions"""
        scorer = PoUScorer()
        final, status = scorer.calculate_final_score(
            coverage=0.95,
            fidelity=0.92,
            consistency=0.88,
            completeness=0.91
        )
        assert final == 0.88
        assert status == PoUStatus.MARGINAL

    def test_all_verified(self):
        """All high scores should result in Verified"""
        scorer = PoUScorer()
        final, status = scorer.calculate_final_score(
            coverage=0.95,
            fidelity=0.92,
            consistency=0.98,
            completeness=0.91
        )
        assert final == 0.91
        assert status == PoUStatus.VERIFIED

    def test_one_low_dimension_fails(self):
        """One low dimension should cause overall failure"""
        scorer = PoUScorer()
        final, status = scorer.calculate_final_score(
            coverage=0.45,
            fidelity=0.92,
            consistency=0.98,
            completeness=0.91
        )
        assert final == 0.45
        assert status == PoUStatus.FAILED


class TestPoUStructureValidation:
    """Tests for PoU structure validation per NCIP-004 Section 4."""

    def test_valid_structure(self):
        """Valid PoU structure should pass"""
        scorer = PoUScorer()
        is_valid, issues = scorer.validate_pou_structure(VALID_POU_DATA)
        assert is_valid is True
        assert len(issues) == 0

    def test_missing_summary(self):
        """Missing summary should fail validation"""
        scorer = PoUScorer()
        invalid_pou = {
            "sections": {
                "obligations": ["Test obligation"],
                "rights": ["Test right"],
                "consequences": ["Test consequence"],
                "acceptance": {"statement": "I accept"}
            }
        }
        is_valid, issues = scorer.validate_pou_structure(invalid_pou)
        assert is_valid is False
        assert any("summary" in issue.lower() for issue in issues)

    def test_missing_obligations(self):
        """Missing obligations should fail validation"""
        scorer = PoUScorer()
        invalid_pou = {
            "sections": {
                "summary": {"text": "I understand the contract terms"},
                "rights": ["Test right"],
                "consequences": ["Test consequence"],
                "acceptance": {"statement": "I accept"}
            }
        }
        is_valid, issues = scorer.validate_pou_structure(invalid_pou)
        assert is_valid is False
        assert any("obligations" in issue.lower() for issue in issues)

    def test_empty_obligations(self):
        """Empty obligations list should fail validation"""
        scorer = PoUScorer()
        invalid_pou = {
            "sections": {
                "summary": {"text": "I understand the contract terms"},
                "obligations": [],
                "rights": ["Test right"],
                "consequences": ["Test consequence"],
                "acceptance": {"statement": "I accept"}
            }
        }
        is_valid, issues = scorer.validate_pou_structure(invalid_pou)
        assert is_valid is False
        assert any("empty" in issue.lower() for issue in issues)

    def test_missing_acceptance(self):
        """Missing acceptance statement should fail validation"""
        scorer = PoUScorer()
        invalid_pou = {
            "sections": {
                "summary": {"text": "I understand the contract terms"},
                "obligations": ["Test obligation"],
                "rights": ["Test right"],
                "consequences": ["Test consequence"]
            }
        }
        is_valid, issues = scorer.validate_pou_structure(invalid_pou)
        assert is_valid is False
        assert any("acceptance" in issue.lower() for issue in issues)

    def test_short_summary_warning(self):
        """Very short summary should generate warning"""
        scorer = PoUScorer()
        short_pou = {
            "sections": {
                "summary": {"text": "OK"},
                "obligations": ["Test obligation"],
                "rights": ["Test right"],
                "consequences": ["Test consequence"],
                "acceptance": {"statement": "I accept"}
            }
        }
        is_valid, issues = scorer.validate_pou_structure(short_pou)
        assert is_valid is False
        assert any("short" in issue.lower() for issue in issues)


class TestSemanticFingerprint:
    """Tests for semantic fingerprint generation."""

    def test_fingerprint_generation(self):
        """Should generate valid fingerprint"""
        scorer = PoUScorer(registry_version="1.0")
        fingerprint = scorer.generate_fingerprint(
            pou_content="Test PoU content",
            contract_content="Test contract content"
        )
        assert fingerprint.method == "sha256-semantic-v1"
        assert fingerprint.hash.startswith("0x")
        assert fingerprint.content_hash.startswith("0x")
        assert fingerprint.registry_version == "1.0"
        assert fingerprint.timestamp.endswith("Z")

    def test_fingerprint_deterministic(self):
        """Same content should produce same hash"""
        scorer = PoUScorer()
        fp1 = scorer.generate_fingerprint("content", "contract")
        fp2 = scorer.generate_fingerprint("content", "contract")
        assert fp1.hash == fp2.hash
        assert fp1.content_hash == fp2.content_hash

    def test_fingerprint_different_for_different_content(self):
        """Different content should produce different hash"""
        scorer = PoUScorer()
        fp1 = scorer.generate_fingerprint("content1", "contract")
        fp2 = scorer.generate_fingerprint("content2", "contract")
        assert fp1.hash != fp2.hash


class TestDimensionScoring:
    """Tests for individual dimension scoring."""

    def test_coverage_full(self):
        """Full coverage of clauses should score high"""
        scorer = PoUScorer()
        sections = VALID_POU_DATA["sections"]
        clauses = ["storage", "100MB/s", "payment", "multiplier"]
        result = scorer.score_coverage(sections, clauses)
        assert result.score > 0.5
        assert result.dimension == PoUDimension.COVERAGE

    def test_coverage_empty_clauses(self):
        """Empty clause list should score 1.0"""
        scorer = PoUScorer()
        result = scorer.score_coverage(VALID_POU_DATA["sections"], [])
        assert result.score == 1.0

    def test_consistency_no_contradictions(self):
        """PoU without contradictions should score high"""
        scorer = PoUScorer()
        result = scorer.score_consistency(VALID_POU_DATA["sections"])
        assert result.score >= 0.8
        assert result.dimension == PoUDimension.CONSISTENCY

    def test_consistency_with_contradictions(self):
        """PoU with potential contradictions should score lower"""
        scorer = PoUScorer()
        contradicting_sections = {
            "summary": {"text": "I must always provide service but I must not provide service"},
            "obligations": ["Always maintain service", "Never provide service on weekends"],
            "rights": [],
            "consequences": [],
            "acceptance": {"statement": "I accept"}
        }
        result = scorer.score_consistency(contradicting_sections)
        assert result.score < 1.0
        assert len(result.issues) > 0

    def test_completeness_all_sections(self):
        """Complete PoU should score high on completeness"""
        scorer = PoUScorer()
        result = scorer.score_completeness(VALID_POU_DATA["sections"])
        assert result.score >= 0.8
        assert result.dimension == PoUDimension.COMPLETENESS

    def test_completeness_missing_sections(self):
        """Incomplete PoU should score lower"""
        scorer = PoUScorer()
        incomplete = {
            "summary": {"text": "Brief"},
            "obligations": [],
            "rights": [],
            "consequences": [],
            "acceptance": {}
        }
        result = scorer.score_completeness(incomplete)
        assert result.score < 0.5
        assert len(result.issues) > 0


class TestPoUScoring:
    """Tests for complete PoU scoring."""

    def test_score_valid_pou(self):
        """Valid PoU should score well"""
        scorer = PoUScorer()
        result = scorer.score_pou(VALID_POU_DATA, SAMPLE_CONTRACT)
        assert result.status != PoUStatus.INVALID
        assert result.final_score > 0.0

    def test_score_invalid_structure_returns_invalid(self):
        """Invalid structure should return INVALID status"""
        scorer = PoUScorer()
        invalid = {"sections": {}}
        result = scorer.score_pou(invalid, SAMPLE_CONTRACT)
        assert result.status == PoUStatus.INVALID
        assert result.binding_effect is False

    def test_verified_has_binding_effect(self):
        """Verified PoU should have binding effect"""
        scorer = PoUScorer()
        # Create a PoU that should score very high
        result = scorer.score_pou(VALID_POU_DATA, SAMPLE_CONTRACT)
        # If verified, binding should be true
        if result.status == PoUStatus.VERIFIED:
            assert result.binding_effect is True

    def test_non_verified_no_binding(self):
        """Non-verified PoU should not have binding effect"""
        scorer = PoUScorer()
        # Create minimal PoU that won't be verified
        minimal = {
            "sections": {
                "summary": {"text": "I accept the terms as stated in the contract"},
                "obligations": ["Fulfill my obligations"],
                "rights": ["Receive my rights"],
                "consequences": ["Accept consequences"],
                "acceptance": {"statement": "I accept"}
            }
        }
        result = scorer.score_pou(minimal, SAMPLE_CONTRACT)
        if result.status != PoUStatus.VERIFIED:
            assert result.binding_effect is False


class TestValidatorResponse:
    """Tests for complete validator response."""

    def test_response_structure(self):
        """Validator response should have expected structure"""
        scorer = PoUScorer()
        response = scorer.get_validator_response(
            VALID_POU_DATA,
            SAMPLE_CONTRACT
        )
        assert "status" in response
        assert "final_score" in response
        assert "dimension_scores" in response
        assert "actions" in response
        assert "message" in response

    def test_response_includes_dimensions(self):
        """Response should include all dimension scores"""
        scorer = PoUScorer()
        response = scorer.get_validator_response(
            VALID_POU_DATA,
            SAMPLE_CONTRACT
        )
        dimensions = response["dimension_scores"]
        assert "coverage" in dimensions
        assert "fidelity" in dimensions
        assert "consistency" in dimensions
        assert "completeness" in dimensions

    def test_verified_response_actions(self):
        """Verified response should have correct actions"""
        scorer = PoUScorer()
        # Manually create verified score result to test actions
        actions = scorer._get_actions(PoUStatus.VERIFIED)
        assert actions["accept"] is True
        assert actions["bind_interpretation"] is True
        assert actions["reject"] is False

    def test_failed_response_actions(self):
        """Failed response should have correct actions"""
        scorer = PoUScorer()
        actions = scorer._get_actions(PoUStatus.FAILED)
        assert actions["accept"] is False
        assert actions["reject"] is True
        assert actions["escalate"] is True
        assert actions["require_mediator"] is True

    def test_marginal_response_actions(self):
        """Marginal response should allow resubmission"""
        scorer = PoUScorer()
        actions = scorer._get_actions(PoUStatus.MARGINAL)
        assert actions["accept_temporary"] is True
        assert actions["flag_for_review"] is True
        assert actions["recommend_clarification"] is True


class TestBindingPoURecord:
    """Tests for binding PoU records per NCIP-004 Section 9."""

    def test_create_binding_record(self):
        """Should create binding record for verified PoU"""
        scorer = PoUScorer()
        scores = PoUScoreResult(
            coverage_score=0.95,
            fidelity_score=0.92,
            consistency_score=0.98,
            completeness_score=0.91,
            final_score=0.91,
            status=PoUStatus.VERIFIED,
            dimension_details={},
            message="Verified",
            binding_effect=True
        )
        fingerprint = scorer.generate_fingerprint("content", "contract")

        record = BindingPoURecord(
            contract_id="test-001",
            signer_id="alice",
            pou_data=VALID_POU_DATA,
            scores=scores,
            fingerprint=fingerprint,
            bound_at="2025-12-24T00:00:00Z"
        )
        assert record.waives_misunderstanding is True
        assert record.admissible_in_dispute is True

    def test_cannot_bind_non_verified(self):
        """Should not create binding record for non-verified PoU"""
        scorer = PoUScorer()
        scores = PoUScoreResult(
            coverage_score=0.75,
            fidelity_score=0.72,
            consistency_score=0.78,
            completeness_score=0.71,
            final_score=0.71,
            status=PoUStatus.INSUFFICIENT,
            dimension_details={},
            message="Insufficient",
            binding_effect=False
        )
        fingerprint = scorer.generate_fingerprint("content", "contract")

        try:
            BindingPoURecord(
                contract_id="test-001",
                signer_id="alice",
                pou_data=VALID_POU_DATA,
                scores=scores,
                fingerprint=fingerprint,
                bound_at="2025-12-24T00:00:00Z"
            )
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "non-verified" in str(e).lower()

    def test_binding_record_to_dict(self):
        """Binding record should serialize correctly"""
        scorer = PoUScorer()
        scores = PoUScoreResult(
            coverage_score=0.95,
            fidelity_score=0.92,
            consistency_score=0.98,
            completeness_score=0.91,
            final_score=0.91,
            status=PoUStatus.VERIFIED,
            dimension_details={},
            message="Verified",
            binding_effect=True
        )
        fingerprint = scorer.generate_fingerprint("content", "contract")

        record = BindingPoURecord(
            contract_id="test-001",
            signer_id="alice",
            pou_data=VALID_POU_DATA,
            scores=scores,
            fingerprint=fingerprint,
            bound_at="2025-12-24T00:00:00Z"
        )

        d = record.to_dict()
        assert d["contract_id"] == "test-001"
        assert d["signer_id"] == "alice"
        assert d["waives_misunderstanding"] is True
        assert "fingerprint" in d
        assert "binding_effect" in d


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_score_pou_function(self):
        """score_pou should return validator response"""
        response = score_pou(VALID_POU_DATA, SAMPLE_CONTRACT)
        assert "status" in response
        assert "final_score" in response

    def test_classify_pou_score_function(self):
        """classify_pou_score should return status"""
        status = classify_pou_score(0.85)
        assert status == PoUStatus.MARGINAL

    def test_get_pou_config_function(self):
        """get_pou_config should return configuration"""
        config = get_pou_config()
        assert "proof_of_understanding" in config
        assert "thresholds" in config["proof_of_understanding"]
        assert "dimensions" in config["proof_of_understanding"]


class TestPoUMessages:
    """Tests for PoU status messages."""

    def test_all_statuses_have_messages(self):
        """All PoU statuses should have defined messages"""
        for status in [PoUStatus.VERIFIED, PoUStatus.MARGINAL,
                       PoUStatus.INSUFFICIENT, PoUStatus.FAILED,
                       PoUStatus.INVALID, PoUStatus.ERROR]:
            assert status in POU_MESSAGES
            assert len(POU_MESSAGES[status]) > 0


class TestPoUThresholds:
    """Tests for threshold definitions per NCIP-004."""

    def test_thresholds_are_contiguous(self):
        """Threshold ranges should be contiguous"""
        statuses = [PoUStatus.FAILED, PoUStatus.INSUFFICIENT,
                    PoUStatus.MARGINAL, PoUStatus.VERIFIED]
        for i in range(len(statuses) - 1):
            current = POU_THRESHOLDS[statuses[i]]
            next_level = POU_THRESHOLDS[statuses[i + 1]]
            assert current[1] == next_level[0], \
                f"Gap between {statuses[i]} and {statuses[i + 1]}"

    def test_thresholds_start_at_zero(self):
        """Failed threshold should start at 0.0"""
        assert POU_THRESHOLDS[PoUStatus.FAILED][0] == 0.0

    def test_thresholds_end_at_one(self):
        """Verified threshold should end at 1.0"""
        assert POU_THRESHOLDS[PoUStatus.VERIFIED][1] == 1.0


def run_tests():
    """Run all tests and report results."""
    test_classes = [
        TestPoUStatusClassification,
        TestFinalScoreCalculation,
        TestPoUStructureValidation,
        TestSemanticFingerprint,
        TestDimensionScoring,
        TestPoUScoring,
        TestValidatorResponse,
        TestBindingPoURecord,
        TestConvenienceFunctions,
        TestPoUMessages,
        TestPoUThresholds
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
        print("\nFailed tests:")
        for name, error in failed_tests:
            print(f"  - {name}: {error}")
        return 1

    print("All tests passed!")
    return 0


if __name__ == "__main__":
    exit(run_tests())

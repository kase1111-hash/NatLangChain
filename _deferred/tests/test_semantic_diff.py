"""
Tests for NatLangChain Semantic Drift Detection module.

Tests:
- SemanticDriftDetector initialization
- check_alignment() method
- check_entry_execution_alignment() method
- set_threshold() method
- check_alignment_ncip_002() method
- aggregate_component_drift() method
- get_drift_level() method
- get_drift_log() method
- NCIP-002 integration
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestSemanticDriftDetectorInit:
    """Tests for SemanticDriftDetector initialization."""

    def test_init_requires_api_key(self):
        """Test initialization requires API key."""
        from semantic_diff import SemanticDriftDetector

        with pytest.raises(ValueError) as exc_info:
            SemanticDriftDetector(api_key=None)
        assert "API_KEY" in str(exc_info.value).upper()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("semantic_diff.Anthropic")
    def test_init_with_env_api_key(self, mock_anthropic):
        """Test initialization with environment API key."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector()
        assert detector.api_key == "test-key"

    @patch("semantic_diff.Anthropic")
    def test_init_default_threshold(self, mock_anthropic):
        """Test default threshold is set."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        assert detector.threshold == 0.7

    @patch("semantic_diff.Anthropic")
    def test_init_default_validator_id(self, mock_anthropic):
        """Test default validator ID."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        assert detector.validator_id == "default"

    @patch("semantic_diff.Anthropic")
    def test_init_custom_validator_id(self, mock_anthropic):
        """Test custom validator ID."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", validator_id="custom-validator")
        assert detector.validator_id == "custom-validator"


class TestSetThreshold:
    """Tests for set_threshold() method."""

    @patch("semantic_diff.Anthropic")
    def test_set_valid_threshold(self, mock_anthropic):
        """Test setting valid threshold."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        detector.set_threshold(0.5)
        assert detector.threshold == 0.5

    @patch("semantic_diff.Anthropic")
    def test_set_threshold_zero(self, mock_anthropic):
        """Test setting threshold to zero."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        detector.set_threshold(0.0)
        assert detector.threshold == 0.0

    @patch("semantic_diff.Anthropic")
    def test_set_threshold_one(self, mock_anthropic):
        """Test setting threshold to one."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        detector.set_threshold(1.0)
        assert detector.threshold == 1.0

    @patch("semantic_diff.Anthropic")
    def test_set_threshold_invalid_low(self, mock_anthropic):
        """Test setting threshold below 0 raises error."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        with pytest.raises(ValueError):
            detector.set_threshold(-0.1)

    @patch("semantic_diff.Anthropic")
    def test_set_threshold_invalid_high(self, mock_anthropic):
        """Test setting threshold above 1 raises error."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key")
        with pytest.raises(ValueError):
            detector.set_threshold(1.1)


class TestCheckAlignment:
    """Tests for check_alignment() method."""

    @patch("semantic_diff.Anthropic")
    def test_check_alignment_success(self, mock_anthropic):
        """Test successful alignment check."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 0.1, "is_violating": false, "reason": "Actions match intent", "recommended_action": "ALLOW"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment(
            on_chain_intent="Execute payment for $100",
            execution_log="Processed payment of $100 to vendor",
        )

        assert result["status"] == "success"
        assert result["drift_analysis"]["score"] == 0.1
        assert result["drift_analysis"]["is_violating"] is False
        assert result["alert"] is False

    @patch("semantic_diff.Anthropic")
    def test_check_alignment_drift_detected(self, mock_anthropic):
        """Test alignment check detects drift."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 0.85, "is_violating": true, "reason": "Actions diverge from intent", "recommended_action": "BLOCK"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment(
            on_chain_intent="Execute payment for $100",
            execution_log="Transferred $10000 to unknown account",
        )

        assert result["status"] == "success"
        assert result["drift_analysis"]["score"] == 0.85
        assert result["drift_analysis"]["is_violating"] is True
        assert result["alert"] is True

    @patch("semantic_diff.Anthropic")
    def test_check_alignment_handles_markdown_json(self, mock_anthropic):
        """Test check_alignment handles JSON in markdown code block."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='```json\n{"score": 0.2, "is_violating": false, "reason": "OK", "recommended_action": "ALLOW"}\n```'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment("Intent", "Action")

        assert result["status"] == "success"
        assert result["drift_analysis"]["score"] == 0.2

    @patch("semantic_diff.Anthropic")
    def test_check_alignment_handles_api_error(self, mock_anthropic):
        """Test check_alignment handles API errors gracefully."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment("Intent", "Action")

        assert result["status"] == "error"
        assert "error" in result

    @patch("semantic_diff.Anthropic")
    def test_check_alignment_handles_json_parse_error(self, mock_anthropic):
        """Test check_alignment handles invalid JSON response."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Not valid JSON")]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment("Intent", "Action")

        assert result["status"] == "error"


class TestCheckEntryExecutionAlignment:
    """Tests for check_entry_execution_alignment() method."""

    @patch("semantic_diff.Anthropic")
    def test_check_entry_execution_alignment(self, mock_anthropic):
        """Test entry-execution alignment combines content and intent."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 0.15, "is_violating": false, "reason": "Match", "recommended_action": "ALLOW"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_entry_execution_alignment(
            entry_content="Payment transaction details",
            entry_intent="Execute payment",
            execution_log="Payment processed successfully",
        )

        assert result["status"] == "success"

        # Verify the combined canonical was used (check the API call)
        call_args = mock_client.messages.create.call_args
        prompt = call_args[1]["messages"][0]["content"]
        assert "Intent:" in prompt
        assert "Content:" in prompt


class TestGetDriftLevel:
    """Tests for get_drift_level() method."""

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_d0(self, mock_anthropic):
        """Test D0 (Stable) classification."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        assert detector.get_drift_level(0.05) == "D0"

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_d1(self, mock_anthropic):
        """Test D1 (Soft Drift) classification."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        assert detector.get_drift_level(0.15) == "D1"

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_d2(self, mock_anthropic):
        """Test D2 (Ambiguous Drift) classification."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        assert detector.get_drift_level(0.35) == "D2"

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_d3(self, mock_anthropic):
        """Test D3 (Hard Drift) classification."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        assert detector.get_drift_level(0.55) == "D3"

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_d4(self, mock_anthropic):
        """Test D4 (Semantic Break) classification."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        assert detector.get_drift_level(0.85) == "D4"

    @patch("semantic_diff.Anthropic")
    def test_get_drift_level_boundary_d0_d1(self, mock_anthropic):
        """Test boundary between D0 and D1."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        # At exactly 0.10, should be D1
        assert detector.get_drift_level(0.10) == "D1"
        # Just below should be D0
        assert detector.get_drift_level(0.09) == "D0"


class TestAggregateComponentDrift:
    """Tests for aggregate_component_drift() method."""

    @patch("semantic_diff.Anthropic")
    def test_aggregate_empty_components(self, mock_anthropic):
        """Test aggregation with empty components."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        result = detector.aggregate_component_drift({})
        assert result["max_score"] == 0.0

    @patch("semantic_diff.Anthropic")
    def test_aggregate_single_component(self, mock_anthropic):
        """Test aggregation with single component."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        result = detector.aggregate_component_drift({"term_a": 0.3})
        assert result["max_score"] == 0.3
        assert result["governing_component"] == "term_a"

    @patch("semantic_diff.Anthropic")
    def test_aggregate_multiple_components(self, mock_anthropic):
        """Test aggregation uses max score."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        result = detector.aggregate_component_drift(
            {"term_a": 0.2, "clause_b": 0.5, "condition_c": 0.1}
        )
        assert result["max_score"] == 0.5
        assert result["governing_component"] == "clause_b"


class TestGetDriftLog:
    """Tests for get_drift_log() method."""

    @patch("semantic_diff.Anthropic")
    def test_get_drift_log_without_ncip(self, mock_anthropic):
        """Test get_drift_log returns empty when NCIP-002 disabled."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        log = detector.get_drift_log()
        assert log == []


class TestCheckAlignmentNCIP002:
    """Tests for check_alignment_ncip_002() method."""

    @patch("semantic_diff.Anthropic")
    def test_ncip_002_alignment_success(self, mock_anthropic):
        """Test NCIP-002 compliant alignment check."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 0.2, "is_violating": false, "reason": "OK", "recommended_action": "ALLOW"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        result = detector.check_alignment_ncip_002(
            on_chain_intent="Intent",
            execution_log="Action",
            affected_terms=["term1"],
            entry_id="entry-123",
        )

        assert result["status"] == "success"

    @patch("semantic_diff.Anthropic")
    def test_ncip_002_passes_error_through(self, mock_anthropic):
        """Test NCIP-002 check passes through errors."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=False)
        result = detector.check_alignment_ncip_002("Intent", "Action")

        assert result["status"] == "error"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("semantic_diff.Anthropic")
    def test_empty_intent(self, mock_anthropic):
        """Test handling of empty intent."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"score": 0.5, "is_violating": false, "reason": "", "recommended_action": "WARN"}')
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment("", "Some action")

        # Should not crash
        assert result is not None

    @patch("semantic_diff.Anthropic")
    def test_very_long_content(self, mock_anthropic):
        """Test handling of very long content."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"score": 0.3, "is_violating": false, "reason": "", "recommended_action": "ALLOW"}')
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")

        long_content = "Lorem ipsum " * 1000
        result = detector.check_alignment(long_content, long_content)

        assert result is not None

    @patch("semantic_diff.Anthropic")
    def test_special_characters_in_content(self, mock_anthropic):
        """Test handling of special characters."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"score": 0.1, "is_violating": false, "reason": "", "recommended_action": "ALLOW"}')
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment(
            "Intent with 'quotes' and \"double quotes\" and <brackets>",
            "Action with \n newlines \t and tabs",
        )

        assert result is not None

    @patch("semantic_diff.Anthropic")
    def test_unicode_content(self, mock_anthropic):
        """Test handling of unicode content."""
        from semantic_diff import SemanticDriftDetector

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"score": 0.1, "is_violating": false, "reason": "", "recommended_action": "ALLOW"}')
        ]
        mock_client.messages.create.return_value = mock_message

        detector = SemanticDriftDetector(api_key="test-key")
        result = detector.check_alignment(
            "Intent: 支付 €100 für Dienstleistungen",
            "Action: Processed 支付 €100 payment",
        )

        assert result is not None

    @patch("semantic_diff.Anthropic")
    def test_classifier_lazy_initialization(self, mock_anthropic):
        """Test classifier is lazily initialized."""
        from semantic_diff import SemanticDriftDetector

        detector = SemanticDriftDetector(api_key="test-key", enable_ncip_002=True)

        # Classifier should be None until accessed
        assert detector._classifier is None

        # After accessing classifier property, it should be initialized
        # (if NCIP-002 module is available)
        _ = detector.classifier

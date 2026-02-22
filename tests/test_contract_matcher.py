"""
Tests for NatLangChain Contract Matcher module.

Tests:
- ContractMatcher initialization
- find_matches() method
- _get_open_contracts() method
- _compute_match() method
- _extract_json_from_response() method
- _generate_proposal() method
- mediate_negotiation() method
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))


class TestContractMatcherInit:
    """Tests for ContractMatcher initialization."""

    def test_init_requires_api_key(self):
        """Test initialization requires API key."""
        from contract_matcher import ContractMatcher

        with pytest.raises(ValueError) as exc_info:
            ContractMatcher(api_key=None)
        assert "API_KEY" in str(exc_info.value).upper()

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
    @patch("contract_matcher.Anthropic")
    def test_init_with_env_api_key(self, mock_anthropic):
        """Test initialization with environment API key."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher()
        assert matcher.api_key == "test-key"

    @patch("contract_matcher.Anthropic")
    def test_init_with_explicit_api_key(self, mock_anthropic):
        """Test initialization with explicit API key."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="explicit-key")
        assert matcher.api_key == "explicit-key"

    @patch("contract_matcher.Anthropic")
    def test_init_default_threshold(self, mock_anthropic):
        """Test default match threshold."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        assert matcher.match_threshold == 80

    @patch("contract_matcher.Anthropic")
    def test_init_custom_threshold(self, mock_anthropic):
        """Test custom match threshold."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key", match_threshold=70)
        assert matcher.match_threshold == 70

    @patch("contract_matcher.Anthropic")
    def test_init_creates_parser(self, mock_anthropic):
        """Test initialization creates ContractParser."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        assert matcher.parser is not None


class TestGetOpenContracts:
    """Tests for _get_open_contracts() method."""

    @patch("contract_matcher.Anthropic")
    def test_get_open_contracts_empty_chain(self, mock_anthropic):
        """Test getting open contracts from empty chain."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        # Mock blockchain with empty chain
        mock_blockchain = MagicMock()
        mock_blockchain.chain = []

        result = matcher._get_open_contracts(mock_blockchain)
        assert result == []

    @patch("contract_matcher.Anthropic")
    def test_get_open_contracts_no_contracts(self, mock_anthropic):
        """Test getting open contracts when no contracts exist."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        # Mock block with non-contract entries
        mock_entry = MagicMock()
        mock_entry.metadata = {"is_contract": False}
        mock_entry.content = "Regular entry"

        mock_block = MagicMock()
        mock_block.entries = [mock_entry]

        mock_blockchain = MagicMock()
        mock_blockchain.chain = [mock_block]

        result = matcher._get_open_contracts(mock_blockchain)
        assert result == []

    @patch("contract_matcher.Anthropic")
    def test_get_open_contracts_closed_contracts(self, mock_anthropic):
        """Test that closed contracts are not returned."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        mock_entry = MagicMock()
        mock_entry.metadata = {"is_contract": True, "status": "closed"}
        mock_entry.content = "Closed contract"

        mock_block = MagicMock()
        mock_block.entries = [mock_entry]

        mock_blockchain = MagicMock()
        mock_blockchain.chain = [mock_block]

        result = matcher._get_open_contracts(mock_blockchain)
        assert result == []

    @patch("contract_matcher.Anthropic")
    def test_get_open_contracts_returns_open(self, mock_anthropic):
        """Test that open contracts are returned."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        mock_entry = MagicMock()
        mock_entry.metadata = {"is_contract": True, "status": "open"}
        mock_entry.content = "Open contract"
        mock_entry.author = "author1"
        mock_entry.intent = "offer services"
        mock_entry.timestamp = 1234567890

        mock_block = MagicMock()
        mock_block.entries = [mock_entry]
        mock_block.index = 1
        mock_block.hash = "abc123"

        mock_blockchain = MagicMock()
        mock_blockchain.chain = [mock_block]

        result = matcher._get_open_contracts(mock_blockchain)
        assert len(result) == 1
        assert result[0]["content"] == "Open contract"
        assert result[0]["author"] == "author1"


class TestExtractJsonFromResponse:
    """Tests for _extract_json_from_response() method."""

    @patch("contract_matcher.Anthropic")
    def test_extract_plain_json(self, mock_anthropic):
        """Test extracting plain JSON."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        response = '{"score": 85, "recommendation": "MATCH"}'
        result = matcher._extract_json_from_response(response)
        assert '"score": 85' in result

    @patch("contract_matcher.Anthropic")
    def test_extract_json_from_markdown(self, mock_anthropic):
        """Test extracting JSON from markdown code block."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        response = '''Result:
```json
{"score": 85}
```
'''
        result = matcher._extract_json_from_response(response)
        assert '"score": 85' in result

    @patch("contract_matcher.Anthropic")
    def test_extract_empty_raises(self, mock_anthropic):
        """Test empty response raises ValueError."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        with pytest.raises(ValueError):
            matcher._extract_json_from_response("")

    @patch("contract_matcher.Anthropic")
    def test_extract_unclosed_block_raises(self, mock_anthropic):
        """Test unclosed code block raises ValueError."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")
        with pytest.raises(ValueError):
            matcher._extract_json_from_response('```json\n{"score": 85}')


class TestComputeMatch:
    """Tests for _compute_match() method."""

    @patch("contract_matcher.Anthropic")
    def test_compute_match_success(self, mock_anthropic):
        """Test successful match computation."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 85, "compatibility": "Good match", "conflicts": [], "recommendation": "MATCH", "reasoning": "Terms align"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")
        result = matcher._compute_match(
            content1="I offer web development",
            intent1="offer services",
            terms1={"fee": "1000"},
            content2="Seeking web developer",
            intent2="seek developer",
            terms2={"budget": "1500"},
        )

        assert result["score"] == 85
        assert result["recommendation"] == "MATCH"

    @patch("contract_matcher.Anthropic")
    def test_compute_match_handles_api_error(self, mock_anthropic):
        """Test match computation handles API errors gracefully."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API Error")

        matcher = ContractMatcher(api_key="test-key")
        result = matcher._compute_match(
            content1="Content 1",
            intent1="Intent 1",
            terms1={},
            content2="Content 2",
            intent2="Intent 2",
            terms2={},
        )

        assert result["score"] == 0
        assert result["recommendation"] == "NO_MATCH"

    @patch("contract_matcher.Anthropic")
    def test_compute_match_handles_empty_response(self, mock_anthropic):
        """Test match computation handles empty API response."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = []
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")
        result = matcher._compute_match(
            content1="Content 1",
            intent1="Intent 1",
            terms1={},
            content2="Content 2",
            intent2="Intent 2",
            terms2={},
        )

        assert result["score"] == 0
        assert result["recommendation"] == "NO_MATCH"


class TestFindMatches:
    """Tests for find_matches() method."""

    @patch("contract_matcher.Anthropic")
    def test_find_matches_empty_pending(self, mock_anthropic):
        """Test finding matches with no pending entries."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        mock_blockchain = MagicMock()
        mock_blockchain.chain = []

        result = matcher.find_matches(mock_blockchain, [], "miner1")
        assert result == []

    @patch("contract_matcher.Anthropic")
    def test_find_matches_skips_non_contracts(self, mock_anthropic):
        """Test that non-contract entries are skipped."""
        from contract_matcher import ContractMatcher

        matcher = ContractMatcher(api_key="test-key")

        mock_blockchain = MagicMock()
        mock_blockchain.chain = []

        # Non-contract entry
        mock_entry = MagicMock()
        mock_entry.metadata = {"is_contract": False}

        result = matcher.find_matches(mock_blockchain, [mock_entry], "miner1")
        assert result == []

    @patch("contract_matcher.Anthropic")
    def test_find_matches_skips_same_type(self, mock_anthropic):
        """Test that same types don't match (offer with offer)."""
        from contract_matcher import ContractMatcher
        from contract_parser import ContractParser

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        matcher = ContractMatcher(api_key="test-key")

        # Both are offers - should not match
        mock_pending = MagicMock()
        mock_pending.metadata = {
            "is_contract": True,
            "contract_type": ContractParser.TYPE_OFFER,
            "terms": {},
        }
        mock_pending.content = "Offer 1"
        mock_pending.intent = "offer"

        mock_existing_entry = MagicMock()
        mock_existing_entry.metadata = {
            "is_contract": True,
            "contract_type": ContractParser.TYPE_OFFER,
            "status": "open",
            "terms": {},
        }
        mock_existing_entry.content = "Offer 2"
        mock_existing_entry.author = "author"
        mock_existing_entry.intent = "offer"
        mock_existing_entry.timestamp = 123

        mock_block = MagicMock()
        mock_block.entries = [mock_existing_entry]
        mock_block.index = 1
        mock_block.hash = "abc"

        mock_blockchain = MagicMock()
        mock_blockchain.chain = [mock_block]

        result = matcher.find_matches(mock_blockchain, [mock_pending], "miner1")
        # No matches because both are offers
        assert len(result) == 0


class TestGenerateProposal:
    """Tests for _generate_proposal() method."""

    @patch("contract_matcher.Anthropic")
    def test_generate_proposal_success(self, mock_anthropic):
        """Test successful proposal generation."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text="Merged proposal text")]
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")

        mock_pending = MagicMock()
        mock_pending.content = "Pending content"
        mock_pending.author = "author1"
        mock_pending.metadata = {"terms": {"fee": "100"}}

        existing = {
            "content": "Existing content",
            "author": "author2",
            "metadata": {"terms": {"budget": "150"}},
        }

        match_result = {"score": 85, "compatibility": "Good match"}

        proposal = matcher._generate_proposal(mock_pending, existing, match_result, "miner1")

        assert proposal is not None
        assert "PROPOSAL" in proposal.content or proposal.metadata.get("contract_type") == "proposal"

    @patch("contract_matcher.Anthropic")
    def test_generate_proposal_handles_error(self, mock_anthropic):
        """Test proposal generation handles errors gracefully."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API Error")

        matcher = ContractMatcher(api_key="test-key")

        mock_pending = MagicMock()
        mock_pending.content = "Pending"
        mock_pending.author = "author1"
        mock_pending.metadata = {"terms": {}}

        existing = {"content": "Existing", "author": "author2", "metadata": {"terms": {}}}
        match_result = {"score": 85}

        # Should return a basic proposal even on error
        proposal = matcher._generate_proposal(mock_pending, existing, match_result, "miner1")
        assert proposal is not None


class TestMediateNegotiation:
    """Tests for mediate_negotiation() method."""

    @patch("contract_matcher.Anthropic")
    def test_mediate_negotiation_success(self, mock_anthropic):
        """Test successful negotiation mediation."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"points_of_agreement": ["fee"], "differences": ["timeline"], "suggested_compromise": "Split the difference", "recommended_action": "CONTINUE", "reasoning": "Close to agreement", "revised_terms": {"fee": "1250"}}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")

        result = matcher.mediate_negotiation(
            original_proposal="Original proposal",
            original_terms={"fee": "1000"},
            counter_response="Counter offer",
            counter_terms={"fee": "1500"},
            round_number=1,
        )

        assert "points_of_agreement" in result
        assert "differences" in result
        assert result["recommended_action"] == "CONTINUE"

    @patch("contract_matcher.Anthropic")
    def test_mediate_negotiation_handles_error(self, mock_anthropic):
        """Test mediation handles API errors gracefully."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client
        mock_client.messages.create.side_effect = RuntimeError("API Error")

        matcher = ContractMatcher(api_key="test-key")

        result = matcher.mediate_negotiation(
            original_proposal="Original",
            original_terms={},
            counter_response="Counter",
            counter_terms={},
            round_number=1,
        )

        assert result["recommended_action"] == "TERMINATE"

    @patch("contract_matcher.Anthropic")
    def test_mediate_negotiation_empty_response(self, mock_anthropic):
        """Test mediation handles empty API response."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = []
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")

        result = matcher.mediate_negotiation(
            original_proposal="Original",
            original_terms={},
            counter_response="Counter",
            counter_terms={},
            round_number=1,
        )

        assert result["recommended_action"] == "TERMINATE"


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    @patch("contract_matcher.Anthropic")
    def test_match_with_empty_terms(self, mock_anthropic):
        """Test matching contracts with empty terms."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(
                text='{"score": 50, "compatibility": "Partial", "conflicts": [], "recommendation": "PARTIAL", "reasoning": "No terms to compare"}'
            )
        ]
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")
        result = matcher._compute_match(
            content1="Offer",
            intent1="offer",
            terms1={},
            content2="Seek",
            intent2="seek",
            terms2={},
        )

        assert result["score"] == 50

    @patch("contract_matcher.Anthropic")
    def test_very_long_content(self, mock_anthropic):
        """Test handling very long contract content."""
        from contract_matcher import ContractMatcher

        mock_client = MagicMock()
        mock_anthropic.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [
            MagicMock(text='{"score": 75, "recommendation": "MATCH", "compatibility": "", "conflicts": [], "reasoning": ""}')
        ]
        mock_client.messages.create.return_value = mock_message

        matcher = ContractMatcher(api_key="test-key")

        long_content = "Lorem ipsum " * 1000

        result = matcher._compute_match(
            content1=long_content,
            intent1="offer",
            terms1={},
            content2=long_content,
            intent2="seek",
            terms2={},
        )

        # Should not crash and return some result
        assert "score" in result

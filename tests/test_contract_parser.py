"""
Tests for NatLangChain Contract Parser module.

Tests:
- ContractParser.is_contract() detection
- ContractParser.parse_contract() parsing
- _parse_tagged_format() tagged format parsing
- _llm_extract_terms() LLM-based extraction (mocked)
- _extract_json_from_response() JSON extraction
- validate_contract_clarity() validation
- format_contract() formatting
"""

import os
import sys
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from contract_parser import ContractParser


class TestContractParserInit:
    """Tests for ContractParser initialization."""

    def test_init_without_api_key(self):
        """Test initialization without API key."""
        parser = ContractParser(api_key=None)
        assert parser.client is None

    @patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key-123"})
    def test_init_with_env_api_key(self):
        """Test initialization reads API key from environment."""
        with patch("contract_parser.Anthropic") as mock_anthropic:
            parser = ContractParser()
            assert parser.api_key == "test-key-123"

    def test_model_default(self):
        """Test default model is set."""
        parser = ContractParser(api_key=None)
        assert "claude" in parser.model.lower()


class TestContractTypes:
    """Tests for contract type and status constants used in parsing/formatting."""

    def test_all_six_contract_types_defined(self):
        """Parser exposes six contract types used in tagged format."""
        types = {
            ContractParser.TYPE_OFFER,
            ContractParser.TYPE_SEEK,
            ContractParser.TYPE_PROPOSAL,
            ContractParser.TYPE_RESPONSE,
            ContractParser.TYPE_CLOSURE,
            ContractParser.TYPE_PAYOUT,
        }
        assert len(types) == 6
        # All should be lowercase strings matching tagged format expectations
        for t in types:
            assert t == t.lower()
            assert isinstance(t, str)

    def test_all_five_contract_statuses_defined(self):
        """Parser exposes five lifecycle statuses."""
        statuses = {
            ContractParser.STATUS_OPEN,
            ContractParser.STATUS_MATCHED,
            ContractParser.STATUS_NEGOTIATING,
            ContractParser.STATUS_CLOSED,
            ContractParser.STATUS_CANCELLED,
        }
        assert len(statuses) == 5
        for s in statuses:
            assert s == s.lower()
            assert isinstance(s, str)


class TestIsContract:
    """Tests for is_contract() method."""

    @pytest.fixture
    def parser(self):
        """Create parser without API key for testing."""
        return ContractParser(api_key=None)

    def test_explicit_contract_tag(self, parser):
        """Test detection with explicit CONTRACT tag."""
        content = "[CONTRACT: OFFER] I offer services for $100"
        assert parser.is_contract(content) is True

    def test_explicit_contract_tag_lowercase(self, parser):
        """Test detection with lowercase CONTRACT tag."""
        content = "[contract: seek] Looking for a developer"
        assert parser.is_contract(content) is True

    def test_offer_keyword(self, parser):
        """Test detection with 'offer' keyword."""
        content = "I offer my consulting services for this project"
        assert parser.is_contract(content) is True

    def test_seeking_keyword(self, parser):
        """Test detection with 'seeking' keyword."""
        content = "Seeking a qualified developer for web work"
        assert parser.is_contract(content) is True

    def test_contract_for_keyword(self, parser):
        """Test detection with 'contract for' keyword."""
        content = "This is a contract for software development"
        assert parser.is_contract(content) is True

    def test_proposal_keyword(self, parser):
        """Test detection with 'proposal' keyword."""
        content = "This proposal outlines the terms of engagement"
        assert parser.is_contract(content) is True

    def test_terms_keyword(self, parser):
        """Test detection with 'terms:' keyword."""
        content = "The terms: payment upon completion"
        assert parser.is_contract(content) is True

    def test_fee_keyword(self, parser):
        """Test detection with 'fee:' keyword."""
        content = "The fee: $500 per hour"
        assert parser.is_contract(content) is True

    def test_escrow_keyword(self, parser):
        """Test detection with 'escrow:' keyword."""
        content = "Escrow: funds held by trusted third party"
        assert parser.is_contract(content) is True

    def test_not_contract_regular_text(self, parser):
        """Test non-contract regular text."""
        content = "This is just a regular message about the weather"
        assert parser.is_contract(content) is False

    def test_not_contract_technical_content(self, parser):
        """Test non-contract technical content."""
        content = "The function returns a list of integers"
        assert parser.is_contract(content) is False


class TestParseTaggedFormat:
    """Tests for _parse_tagged_format() method."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_parse_contract_type_offer(self, parser):
        """Test parsing OFFER type."""
        content = "[CONTRACT: OFFER] Services available"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") == "offer"

    def test_parse_contract_type_seek(self, parser):
        """Test parsing SEEK type."""
        content = "[CONTRACT: SEEK] Looking for help"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") == "seek"

    def test_parse_contract_type_proposal(self, parser):
        """Test parsing PROPOSAL type."""
        content = "[CONTRACT: PROPOSAL] Here's my proposal"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") == "proposal"

    def test_parse_terms_single(self, parser):
        """Test parsing single term."""
        content = "[CONTRACT: OFFER] Service [TERMS: fee=100]"
        result = parser._parse_tagged_format(content)
        assert result.get("terms", {}).get("fee") == "100"

    def test_parse_terms_multiple(self, parser):
        """Test parsing multiple terms."""
        content = "[CONTRACT: OFFER] Service [TERMS: fee=100, deadline=2024-01-01, escrow=yes]"
        result = parser._parse_tagged_format(content)
        terms = result.get("terms", {})
        assert terms.get("fee") == "100"
        assert terms.get("deadline") == "2024-01-01"
        assert terms.get("escrow") == "yes"

    def test_parse_terms_with_spaces(self, parser):
        """Test parsing terms with spaces around equals."""
        content = "[CONTRACT: OFFER] Service [TERMS: fee = 100 , deadline = tomorrow]"
        result = parser._parse_tagged_format(content)
        terms = result.get("terms", {})
        assert "fee" in terms or "fee " in terms

    def test_parse_links(self, parser):
        """Test parsing LINKS tag."""
        content = "[CONTRACT: PROPOSAL] [LINKS: abc123, def456]"
        result = parser._parse_tagged_format(content)
        assert "abc123" in result.get("links", [])
        assert "def456" in result.get("links", [])

    def test_parse_response_to(self, parser):
        """Test parsing RESPONSE TO tag."""
        content = "[RESPONSE TO: abc123def456] I accept your offer"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") == "response"
        assert "abc123def456" in result.get("links", [])

    def test_parse_match_score(self, parser):
        """Test parsing PROPOSAL with match score."""
        content = "[PROPOSAL: Match 85%] These contracts are compatible"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") == "proposal"
        assert result.get("match_score") == 85

    def test_parse_invalid_type_ignored(self, parser):
        """Test that invalid contract types are ignored."""
        content = "[CONTRACT: INVALID_TYPE] Some content"
        result = parser._parse_tagged_format(content)
        assert result.get("contract_type") is None


class TestParseContract:
    """Tests for parse_contract() method."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_parse_non_contract(self, parser):
        """Test parsing non-contract content."""
        content = "Just a regular message"
        result = parser.parse_contract(content, use_llm=False)
        assert result["is_contract"] is False
        assert result["contract_type"] is None

    def test_parse_tagged_contract(self, parser):
        """Test parsing tagged contract."""
        content = "[CONTRACT: OFFER] Web development services [TERMS: fee=1000, timeline=2weeks]"
        result = parser.parse_contract(content, use_llm=False)
        assert result["is_contract"] is True
        assert result["contract_type"] == "offer"
        assert result["terms"]["fee"] == "1000"

    def test_parse_contract_default_values(self, parser):
        """Test parse_contract sets default values."""
        content = "[CONTRACT: SEEK] Need a developer"
        result = parser.parse_contract(content, use_llm=False)
        assert result["status"] == ContractParser.STATUS_OPEN
        assert result["links"] == []
        assert result["match_score"] is None
        assert result["negotiation_round"] == 0


class TestExtractJsonFromResponse:
    """Tests for _extract_json_from_response() method."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_extract_plain_json(self, parser):
        """Test extracting plain JSON."""
        response = '{"fee": "100", "deadline": "tomorrow"}'
        result = parser._extract_json_from_response(response)
        assert result == '{"fee": "100", "deadline": "tomorrow"}'

    def test_extract_json_from_markdown_block(self, parser):
        """Test extracting JSON from markdown code block."""
        response = '''Here's the result:
```json
{"fee": "100", "deadline": "tomorrow"}
```
'''
        result = parser._extract_json_from_response(response)
        assert '"fee": "100"' in result

    def test_extract_json_from_generic_code_block(self, parser):
        """Test extracting JSON from generic code block."""
        response = '''Result:
```
{"fee": "100"}
```
'''
        result = parser._extract_json_from_response(response)
        assert '"fee": "100"' in result

    def test_extract_empty_response_raises(self, parser):
        """Test empty response raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser._extract_json_from_response("")
        assert "empty" in str(exc_info.value).lower()

    def test_extract_whitespace_only_raises(self, parser):
        """Test whitespace-only response raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            parser._extract_json_from_response("   \n   ")
        assert "empty" in str(exc_info.value).lower()

    def test_unclosed_json_block_raises(self, parser):
        """Test unclosed JSON code block raises ValueError."""
        response = '```json\n{"fee": "100"}'  # Missing closing ```
        with pytest.raises(ValueError) as exc_info:
            parser._extract_json_from_response(response)
        assert "unclosed" in str(exc_info.value).lower()

    def test_unclosed_code_block_raises(self, parser):
        """Test unclosed generic code block raises ValueError."""
        response = '```\n{"fee": "100"}'  # Missing closing ```
        with pytest.raises(ValueError) as exc_info:
            parser._extract_json_from_response(response)
        assert "unclosed" in str(exc_info.value).lower()


class TestValidateContractClarity:
    """Tests for validate_contract_clarity() method."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_validate_too_short(self, parser):
        """Test validation fails for too short content."""
        content = "Short"  # Less than 20 characters
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "too short" in reason.lower()

    def test_validate_vague_maybe(self, parser):
        """Test validation detects 'maybe' as vague."""
        content = "I will maybe complete the work by next week"
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "maybe" in reason.lower()

    def test_validate_vague_soon(self, parser):
        """Test validation detects 'soon' as vague."""
        content = "The project will be done soon with good results"
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "soon" in reason.lower()

    def test_validate_vague_approximately(self, parser):
        """Test validation detects 'approximately' as vague."""
        content = "The cost will be approximately five hundred dollars"
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "approximately" in reason.lower()

    def test_validate_vague_some(self, parser):
        """Test validation detects 'some' as vague."""
        content = "I will provide some documentation for the project"
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "some" in reason.lower()

    def test_validate_vague_later(self, parser):
        """Test validation detects 'later' as vague."""
        content = "Payment will be processed later after review completion"
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is False
        assert "later" in reason.lower()

    def test_validate_clear_contract(self, parser):
        """Test validation passes for clear contract."""
        content = (
            "Web development services for $1000, "
            "to be completed by January 15, 2024. "
            "Payment upon delivery of working website."
        )
        is_valid, reason = parser.validate_contract_clarity(content)
        assert is_valid is True
        assert "passed" in reason.lower()


class TestFormatContract:
    """Tests for format_contract() method."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_format_basic_offer(self, parser):
        """Test formatting basic offer contract."""
        result = parser.format_contract(
            contract_type="offer",
            content="Web development services available",
        )
        assert "[CONTRACT: OFFER]" in result
        assert "Web development services available" in result

    def test_format_with_terms(self, parser):
        """Test formatting contract with terms."""
        result = parser.format_contract(
            contract_type="seek",
            content="Looking for a developer",
            terms={"fee": "1000", "deadline": "2024-01-01"},
        )
        assert "[CONTRACT: SEEK]" in result
        assert "[TERMS:" in result
        assert "fee=1000" in result
        assert "deadline=2024-01-01" in result

    def test_format_with_links(self, parser):
        """Test formatting contract with links."""
        result = parser.format_contract(
            contract_type="response",
            content="I accept your offer",
            links=["abc123", "def456"],
        )
        assert "[CONTRACT: RESPONSE]" in result
        assert "[LINKS:" in result
        assert "abc123" in result
        assert "def456" in result

    def test_format_with_terms_and_links(self, parser):
        """Test formatting contract with both terms and links."""
        result = parser.format_contract(
            contract_type="proposal",
            content="Match proposal",
            terms={"match_score": "90"},
            links=["contract1", "contract2"],
        )
        assert "[CONTRACT: PROPOSAL]" in result
        assert "[TERMS:" in result
        assert "[LINKS:" in result

    def test_format_uppercase_type(self, parser):
        """Test that contract type is uppercased."""
        result = parser.format_contract(
            contract_type="offer",
            content="Test",
        )
        assert "[CONTRACT: OFFER]" in result


class TestLLMExtractTerms:
    """Tests for _llm_extract_terms() with mocked LLM."""

    def test_llm_extract_returns_none_without_client(self):
        """Test LLM extraction returns None without API client."""
        parser = ContractParser(api_key=None)
        result = parser._llm_extract_terms("Contract content")
        assert result is None

    @patch("contract_parser.Anthropic")
    def test_llm_extract_parses_response(self, mock_anthropic_class):
        """Test LLM extraction parses response correctly."""
        # Set up mock
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"fee": "500", "deadline": "next week"}')]
        mock_client.messages.create.return_value = mock_message

        parser = ContractParser(api_key="test-key")
        result = parser._llm_extract_terms("I offer services for $500 by next week")

        assert result is not None
        assert result.get("fee") == "500"
        assert result.get("deadline") == "next week"

    @patch("contract_parser.Anthropic")
    def test_llm_extract_flattens_other_terms(self, mock_anthropic_class):
        """Test LLM extraction flattens other_terms."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"fee": "500", "other_terms": {"location": "remote"}}')]
        mock_client.messages.create.return_value = mock_message

        parser = ContractParser(api_key="test-key")
        result = parser._llm_extract_terms("Contract content")

        assert result.get("fee") == "500"
        assert result.get("location") == "remote"
        assert "other_terms" not in result

    @patch("contract_parser.Anthropic")
    def test_llm_extract_handles_empty_response(self, mock_anthropic_class):
        """Test LLM extraction handles empty response."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client

        mock_message = MagicMock()
        mock_message.content = []
        mock_client.messages.create.return_value = mock_message

        parser = ContractParser(api_key="test-key")
        result = parser._llm_extract_terms("Contract content")
        assert result is None

    @patch("contract_parser.Anthropic")
    def test_llm_extract_handles_api_error(self, mock_anthropic_class):
        """Test LLM extraction handles API errors gracefully."""
        mock_client = MagicMock()
        mock_anthropic_class.return_value = mock_client
        mock_client.messages.create.side_effect = Exception("API Error")

        parser = ContractParser(api_key="test-key")
        result = parser._llm_extract_terms("Contract content")
        assert result is None


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    @pytest.fixture
    def parser(self):
        return ContractParser(api_key=None)

    def test_contract_with_special_characters(self, parser):
        """Test parsing contract with special characters."""
        content = "[CONTRACT: OFFER] Price: $1,000 (USD) [TERMS: fee=$1,000]"
        result = parser.parse_contract(content, use_llm=False)
        assert result["is_contract"] is True

    def test_contract_multiline(self, parser):
        """Test parsing multiline contract."""
        content = """[CONTRACT: OFFER]
        I offer web development services.
        [TERMS: fee=1000, deadline=2024-01-01]
        """
        result = parser.parse_contract(content, use_llm=False)
        assert result["is_contract"] is True
        assert result["terms"]["fee"] == "1000"

    def test_contract_with_empty_terms(self, parser):
        """Test parsing contract with empty TERMS tag."""
        content = "[CONTRACT: OFFER] Services [TERMS: ]"
        result = parser._parse_tagged_format(content)
        # Should not crash, terms may be empty
        assert result.get("contract_type") == "offer"

    def test_contract_with_url_in_content(self, parser):
        """Test contract detection doesn't false positive on URLs."""
        content = "Check out https://example.com/offering-services"
        # 'offering' is close to 'offer' but this shouldn't necessarily be a contract
        # depends on implementation - just ensure it doesn't crash
        parser.is_contract(content)

    def test_case_insensitivity(self, parser):
        """Test case insensitivity of keyword detection."""
        assert parser.is_contract("OFFER available") is True
        assert parser.is_contract("Offer available") is True
        assert parser.is_contract("offer available") is True

    def test_format_contract_empty_terms(self, parser):
        """Test formatting with empty terms dict."""
        result = parser.format_contract(
            contract_type="offer",
            content="Test",
            terms={},
        )
        assert "[TERMS:" not in result

    def test_format_contract_empty_links(self, parser):
        """Test formatting with empty links list."""
        result = parser.format_contract(
            contract_type="offer",
            content="Test",
            links=[],
        )
        assert "[LINKS:" not in result

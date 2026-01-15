"""
Tests for the multi-provider LLM abstraction layer.

Tests both the provider abstraction and the multi-model consensus system.
"""

import json
import os
from unittest.mock import MagicMock, patch

import pytest

from src.llm_providers import (
    AnthropicProvider,
    GeminiProvider,
    GrokProvider,
    LlamaCppProvider,
    LLMProvider,
    LLMResponse,
    OllamaProvider,
    OpenAIProvider,
    ProviderConfig,
    ProviderManager,
    ProviderStrength,
    ProviderType,
    get_default_provider_manager,
    list_available_providers,
)
from src.multi_model_consensus import (
    HallucinationDetector,
    MultiModelConsensus,
)

# =============================================================================
# Provider Config Tests
# =============================================================================


class TestProviderConfig:
    """Tests for ProviderConfig dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = ProviderConfig(
            name="test",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BALANCED,
        )
        assert config.name == "test"
        assert config.provider_type == ProviderType.CLOUD
        assert config.strength == ProviderStrength.BALANCED
        assert config.weight == 1.0
        assert config.timeout == 30
        assert config.max_retries == 3
        assert config.enabled is True

    def test_custom_config(self):
        """Test custom configuration values."""
        config = ProviderConfig(
            name="custom",
            provider_type=ProviderType.LOCAL,
            strength=ProviderStrength.SPEED,
            weight=0.8,
            model_id="llama3.2",
            base_url="http://localhost:11434",
            timeout=60,
        )
        assert config.weight == 0.8
        assert config.model_id == "llama3.2"
        assert config.timeout == 60


# =============================================================================
# LLMResponse Tests
# =============================================================================


class TestLLMResponse:
    """Tests for LLMResponse dataclass."""

    def test_successful_response(self):
        """Test successful response structure."""
        response = LLMResponse(
            success=True,
            content='{"valid": true}',
            provider="test",
            model="test-model",
            latency_ms=100.5,
            tokens_used=50,
        )
        assert response.success is True
        assert response.content == '{"valid": true}'
        assert response.latency_ms == 100.5

    def test_failed_response(self):
        """Test failed response structure."""
        response = LLMResponse(
            success=False,
            error="Connection timeout",
            provider="test",
        )
        assert response.success is False
        assert response.error == "Connection timeout"
        assert response.content is None


# =============================================================================
# Provider Tests (Mocked)
# =============================================================================


class TestAnthropicProvider:
    """Tests for Anthropic Claude provider."""

    def test_is_available_without_key(self):
        """Test availability check without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = AnthropicProvider()
            # Should return False without API key
            assert provider.config.api_key is None

    def test_complete_success(self):
        """Test successful completion with mocked client."""
        try:
            pass
        except ImportError:
            pytest.skip("anthropic package not installed")

        config = ProviderConfig(
            name="anthropic",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.NUANCE,
            api_key="test-key",
            model_id="claude-3-5-sonnet",
        )
        provider = AnthropicProvider(config)

        # Mock the client directly
        mock_client = MagicMock()
        mock_message = MagicMock()
        mock_message.content = [MagicMock(text='{"valid": true, "confidence": 0.9}')]
        mock_message.usage.output_tokens = 50
        mock_client.messages.create.return_value = mock_message
        provider._client = mock_client

        # Mock is_available to return True
        with patch.object(provider, "is_available", return_value=True):
            response = provider.complete("Test prompt")

        assert response.success is True
        assert response.content == '{"valid": true, "confidence": 0.9}'
        assert response.provider == "anthropic"


class TestOpenAIProvider:
    """Tests for OpenAI GPT provider."""

    def test_is_available_without_key(self):
        """Test availability check without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = OpenAIProvider()
            assert provider.config.api_key is None

    def test_complete_success(self):
        """Test successful completion with mocked client."""
        try:
            pass
        except ImportError:
            pytest.skip("openai package not installed")

        config = ProviderConfig(
            name="openai",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BREADTH,
            api_key="test-key",
            model_id="gpt-4o",
        )
        provider = OpenAIProvider(config)

        # Mock the client directly
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content='{"valid": true}'))]
        mock_response.usage.completion_tokens = 30
        mock_client.chat.completions.create.return_value = mock_response
        provider._client = mock_client

        # Mock is_available to return True
        with patch.object(provider, "is_available", return_value=True):
            response = provider.complete("Test prompt")

        assert response.success is True
        assert response.content == '{"valid": true}'


class TestGeminiProvider:
    """Tests for Google Gemini provider."""

    def test_is_available_without_key(self):
        """Test availability check without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = GeminiProvider()
            assert provider.config.api_key is None


class TestGrokProvider:
    """Tests for xAI Grok provider."""

    def test_is_available_without_key(self):
        """Test availability check without API key."""
        with patch.dict(os.environ, {}, clear=True):
            provider = GrokProvider()
            assert provider.config.api_key is None

    def test_uses_xai_base_url(self):
        """Test that Grok uses xAI's API endpoint."""
        provider = GrokProvider()
        assert provider.config.base_url == "https://api.x.ai/v1"


class TestOllamaProvider:
    """Tests for Ollama local provider."""

    def test_default_config(self):
        """Test default Ollama configuration."""
        provider = OllamaProvider()
        assert provider.config.provider_type == ProviderType.LOCAL
        assert provider.config.strength == ProviderStrength.SPEED
        assert "localhost:11434" in provider.config.base_url

    @patch("src.llm_providers.requests.get")
    def test_is_available_server_running(self, mock_get):
        """Test availability when Ollama server is running."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"models": [{"name": "llama3.2:latest"}]}
        mock_get.return_value = mock_response

        provider = OllamaProvider()
        assert provider.is_available() is True

    @patch("src.llm_providers.requests.get")
    def test_is_available_server_down(self, mock_get):
        """Test availability when Ollama server is down."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

        provider = OllamaProvider()
        assert provider.is_available() is False

    @patch("src.llm_providers.requests.post")
    @patch("src.llm_providers.requests.get")
    def test_complete_success(self, mock_get, mock_post):
        """Test successful completion with Ollama."""
        # Mock server availability check
        mock_get.return_value = MagicMock(
            status_code=200, json=lambda: {"models": [{"name": "llama3.2"}]}
        )

        # Mock completion
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"response": '{"valid": true, "confidence": 0.85}', "eval_count": 45},
        )

        provider = OllamaProvider()
        response = provider.complete("Test prompt")

        assert response.success is True
        assert "valid" in response.content


class TestLlamaCppProvider:
    """Tests for llama.cpp local provider."""

    def test_default_config(self):
        """Test default llama.cpp configuration."""
        provider = LlamaCppProvider()
        assert provider.config.provider_type == ProviderType.LOCAL
        assert provider.config.strength == ProviderStrength.SPEED
        assert "localhost:8080" in provider.config.base_url


# =============================================================================
# Provider Manager Tests
# =============================================================================


class TestProviderManager:
    """Tests for ProviderManager."""

    def test_empty_manager(self):
        """Test manager with no providers."""
        manager = ProviderManager(auto_discover=False)
        assert manager.provider_count == 0
        assert manager.has_cloud_providers is False
        assert manager.has_local_providers is False

    def test_list_providers_empty(self):
        """Test listing providers when none available."""
        manager = ProviderManager(auto_discover=False)
        providers = manager.list_providers()
        assert providers == []

    @patch("src.llm_providers.AnthropicProvider.is_available")
    def test_discover_single_provider(self, mock_available):
        """Test discovering a single available provider."""
        mock_available.return_value = True

        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            manager = ProviderManager(auto_discover=True)
            # At least anthropic should be discovered if key is set
            # (actual availability depends on mocking)

    def test_add_custom_provider(self):
        """Test adding a custom provider."""
        manager = ProviderManager(auto_discover=False)

        # Create a mock provider
        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "custom"
        mock_provider.is_available.return_value = True
        mock_provider.config = ProviderConfig(
            name="custom",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BALANCED,
        )

        manager.add_provider(mock_provider)

        assert "custom" in manager.providers
        assert manager.provider_count == 1

    def test_remove_provider(self):
        """Test removing a provider."""
        manager = ProviderManager(auto_discover=False)

        mock_provider = MagicMock(spec=LLMProvider)
        mock_provider.name = "test"
        mock_provider.is_available.return_value = True
        mock_provider.config = ProviderConfig(
            name="test",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BALANCED,
        )

        manager.add_provider(mock_provider)
        assert manager.provider_count == 1

        result = manager.remove_provider("test")
        assert result is True
        assert manager.provider_count == 0

    def test_get_providers_by_type(self):
        """Test filtering providers by type."""
        manager = ProviderManager(auto_discover=False)

        # Add cloud provider
        cloud_provider = MagicMock(spec=LLMProvider)
        cloud_provider.name = "cloud1"
        cloud_provider.is_available.return_value = True
        cloud_provider.config = ProviderConfig(
            name="cloud1",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BREADTH,
        )

        # Add local provider
        local_provider = MagicMock(spec=LLMProvider)
        local_provider.name = "local1"
        local_provider.is_available.return_value = True
        local_provider.config = ProviderConfig(
            name="local1",
            provider_type=ProviderType.LOCAL,
            strength=ProviderStrength.SPEED,
        )

        manager.add_provider(cloud_provider)
        manager.add_provider(local_provider)

        cloud_list = manager.get_providers_by_type(ProviderType.CLOUD)
        local_list = manager.get_providers_by_type(ProviderType.LOCAL)

        assert len(cloud_list) == 1
        assert len(local_list) == 1
        assert cloud_list[0].name == "cloud1"
        assert local_list[0].name == "local1"


# =============================================================================
# Multi-Model Consensus Tests
# =============================================================================


class TestMultiModelConsensus:
    """Tests for MultiModelConsensus."""

    def test_init_with_no_providers_raises(self):
        """Test that initialization fails without providers."""
        manager = ProviderManager(auto_discover=False)

        with pytest.raises(ValueError) as exc_info:
            MultiModelConsensus(provider_manager=manager, min_providers=1)

        assert "At least 1 LLM provider" in str(exc_info.value)

    def test_consensus_calculation_all_valid(self):
        """Test consensus calculation when all providers agree valid."""
        manager = ProviderManager(auto_discover=False)

        # Create mock providers
        for i in range(3):
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = f"provider{i}"
            mock_provider.is_available.return_value = True
            mock_provider.config = ProviderConfig(
                name=f"provider{i}",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BALANCED,
                weight=1.0,
            )
            mock_provider.complete.return_value = LLMResponse(
                success=True,
                content=json.dumps(
                    {
                        "valid": True,
                        "confidence": 0.9,
                        "clarity_score": 0.85,
                        "intent_match": True,
                        "issues": [],
                        "reasoning": "Entry is clear",
                    }
                ),
                provider=f"provider{i}",
                latency_ms=100,
            )
            mock_provider.parse_json_response.return_value = {
                "valid": True,
                "confidence": 0.9,
                "clarity_score": 0.85,
                "intent_match": True,
                "issues": [],
                "reasoning": "Entry is clear",
            }
            manager.add_provider(mock_provider)

        consensus = MultiModelConsensus(provider_manager=manager)
        result = consensus.validate_with_consensus(
            content="Test content",
            intent="test",
            author="tester",
        )

        assert result["status"] == "success"
        assert result["consensus"] == "VALID"
        assert result["consensus_achieved"] is True
        assert result["model_count"] == 3

    def test_consensus_calculation_mixed_votes(self):
        """Test consensus calculation with mixed votes."""
        manager = ProviderManager(auto_discover=False)

        # Create 2 valid, 1 invalid
        for i, is_valid in enumerate([True, True, False]):
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = f"provider{i}"
            mock_provider.is_available.return_value = True
            mock_provider.config = ProviderConfig(
                name=f"provider{i}",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BALANCED,
                weight=1.0,
            )
            mock_provider.complete.return_value = LLMResponse(
                success=True,
                content=json.dumps({"valid": is_valid, "confidence": 0.8}),
                provider=f"provider{i}",
                latency_ms=100,
            )
            mock_provider.parse_json_response.return_value = {
                "valid": is_valid,
                "confidence": 0.8,
                "clarity_score": 0.7,
                "issues": [] if is_valid else ["Ambiguous"],
            }
            manager.add_provider(mock_provider)

        consensus = MultiModelConsensus(provider_manager=manager)
        result = consensus.validate_with_consensus(
            content="Test content",
            intent="test",
            author="tester",
        )

        # 2/3 valid = 66.67% which meets default 66% threshold
        assert result["consensus"] == "VALID"
        assert result["valid_ratio"] >= 0.66

    def test_provider_stats(self):
        """Test provider statistics."""
        manager = ProviderManager(auto_discover=False)

        # Add mixed providers
        for name, ptype in [("cloud1", ProviderType.CLOUD), ("local1", ProviderType.LOCAL)]:
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = name
            mock_provider.is_available.return_value = True
            mock_provider.config = ProviderConfig(
                name=name,
                provider_type=ptype,
                strength=ProviderStrength.BALANCED,
            )
            manager.add_provider(mock_provider)

        consensus = MultiModelConsensus(provider_manager=manager)
        stats = consensus.get_provider_stats()

        assert stats["total_providers"] == 2
        assert stats["has_cloud"] is True
        assert stats["has_local"] is True
        assert stats["is_decentralized"] is True


# =============================================================================
# Hallucination Detector Tests
# =============================================================================


class TestHallucinationDetector:
    """Tests for HallucinationDetector."""

    def test_detect_agreement(self):
        """Test hallucination detection when providers agree."""
        manager = ProviderManager(auto_discover=False)

        # Create agreeing providers
        for i in range(2):
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = f"provider{i}"
            mock_provider.is_available.return_value = True
            mock_provider.config = ProviderConfig(
                name=f"provider{i}",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BALANCED,
            )
            mock_provider.complete.return_value = LLMResponse(
                success=True,
                content='{"valid": true}',
                provider=f"provider{i}",
            )
            mock_provider.parse_json_response.return_value = {"valid": True}
            manager.add_provider(mock_provider)

        consensus = MultiModelConsensus(provider_manager=manager)
        detector = HallucinationDetector(consensus)
        result = detector.detect_hallucination("Test prompt")

        assert result["hallucination_risk"] == "low"
        assert result["model_agreement"] is True
        assert result["recommendation"] == "PROCEED"

    def test_detect_disagreement(self):
        """Test hallucination detection when providers disagree."""
        manager = ProviderManager(auto_discover=False)

        # Create disagreeing providers
        for i, valid in enumerate([True, False]):
            mock_provider = MagicMock(spec=LLMProvider)
            mock_provider.name = f"provider{i}"
            mock_provider.is_available.return_value = True
            mock_provider.config = ProviderConfig(
                name=f"provider{i}",
                provider_type=ProviderType.CLOUD,
                strength=ProviderStrength.BALANCED,
            )
            mock_provider.complete.return_value = LLMResponse(
                success=True,
                content=json.dumps({"valid": valid}),
                provider=f"provider{i}",
            )
            mock_provider.parse_json_response.return_value = {"valid": valid}
            manager.add_provider(mock_provider)

        consensus = MultiModelConsensus(provider_manager=manager)
        detector = HallucinationDetector(consensus)
        result = detector.detect_hallucination("Test prompt")

        assert result["hallucination_risk"] == "high"
        assert result["model_agreement"] is False
        assert result["recommendation"] == "REVIEW"


# =============================================================================
# Convenience Function Tests
# =============================================================================


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_list_available_providers(self):
        """Test listing available providers."""
        # This will discover whatever providers are available in the environment
        providers = list_available_providers()
        assert isinstance(providers, list)

    @patch("src.llm_providers.ProviderManager.discover_providers")
    def test_get_default_provider_manager(self, mock_discover):
        """Test getting default provider manager."""
        mock_discover.return_value = {}
        manager = get_default_provider_manager()
        assert isinstance(manager, ProviderManager)


# =============================================================================
# JSON Parsing Tests
# =============================================================================


class TestJSONParsing:
    """Tests for JSON extraction from responses."""

    def test_extract_json_from_markdown(self):
        """Test extracting JSON from markdown code blocks."""
        provider = AnthropicProvider()

        # Test with ```json block
        text_with_json = '```json\n{"valid": true}\n```'
        result = provider._extract_json_from_response(text_with_json)
        assert result == '{"valid": true}'

        # Test with plain ``` block
        text_with_block = '```\n{"valid": false}\n```'
        result = provider._extract_json_from_response(text_with_block)
        assert result == '{"valid": false}'

        # Test plain JSON
        plain_json = '{"valid": true}'
        result = provider._extract_json_from_response(plain_json)
        assert result == '{"valid": true}'

    def test_parse_json_response(self):
        """Test full JSON parsing."""
        provider = AnthropicProvider()

        # Valid JSON
        result = provider.parse_json_response('{"valid": true, "score": 0.9}')
        assert result == {"valid": True, "score": 0.9}

        # Invalid JSON
        result = provider.parse_json_response("not json")
        assert result is None


# =============================================================================
# Integration-like Tests (with mocking)
# =============================================================================


class TestMultiProviderIntegration:
    """Integration-style tests with multiple mocked providers."""

    def test_full_validation_flow(self):
        """Test complete validation flow with multiple providers."""
        manager = ProviderManager(auto_discover=False)

        # Simulate Claude (nuance)
        claude = MagicMock(spec=LLMProvider)
        claude.name = "anthropic"
        claude.is_available.return_value = True
        claude.config = ProviderConfig(
            name="anthropic",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.NUANCE,
            weight=1.0,
        )
        claude.complete.return_value = LLMResponse(
            success=True,
            content=json.dumps(
                {
                    "valid": True,
                    "confidence": 0.95,
                    "clarity_score": 0.9,
                    "intent_match": True,
                    "issues": [],
                    "reasoning": "Clear and well-structured entry",
                }
            ),
            provider="anthropic",
            latency_ms=250,
        )
        claude.parse_json_response.return_value = {
            "valid": True,
            "confidence": 0.95,
            "clarity_score": 0.9,
            "intent_match": True,
            "issues": [],
            "reasoning": "Clear and well-structured entry",
        }

        # Simulate GPT (breadth)
        gpt = MagicMock(spec=LLMProvider)
        gpt.name = "openai"
        gpt.is_available.return_value = True
        gpt.config = ProviderConfig(
            name="openai",
            provider_type=ProviderType.CLOUD,
            strength=ProviderStrength.BREADTH,
            weight=1.0,
        )
        gpt.complete.return_value = LLMResponse(
            success=True,
            content=json.dumps(
                {
                    "valid": True,
                    "confidence": 0.88,
                    "clarity_score": 0.85,
                    "intent_match": True,
                    "issues": [],
                    "reasoning": "Entry matches stated intent",
                }
            ),
            provider="openai",
            latency_ms=180,
        )
        gpt.parse_json_response.return_value = {
            "valid": True,
            "confidence": 0.88,
            "clarity_score": 0.85,
            "intent_match": True,
            "issues": [],
            "reasoning": "Entry matches stated intent",
        }

        # Simulate Ollama (local)
        ollama = MagicMock(spec=LLMProvider)
        ollama.name = "ollama"
        ollama.is_available.return_value = True
        ollama.config = ProviderConfig(
            name="ollama",
            provider_type=ProviderType.LOCAL,
            strength=ProviderStrength.SPEED,
            weight=0.8,
        )
        ollama.complete.return_value = LLMResponse(
            success=True,
            content=json.dumps(
                {
                    "valid": True,
                    "confidence": 0.80,
                    "clarity_score": 0.75,
                    "intent_match": True,
                    "issues": [],
                    "reasoning": "Looks valid",
                }
            ),
            provider="ollama",
            latency_ms=50,
        )
        ollama.parse_json_response.return_value = {
            "valid": True,
            "confidence": 0.80,
            "clarity_score": 0.75,
            "intent_match": True,
            "issues": [],
            "reasoning": "Looks valid",
        }

        manager.add_provider(claude)
        manager.add_provider(gpt)
        manager.add_provider(ollama)

        # Run consensus validation
        consensus = MultiModelConsensus(provider_manager=manager)
        result = consensus.validate_with_consensus(
            content="Alice agrees to provide consulting services to Bob for $5000/month",
            intent="service_agreement",
            author="alice",
        )

        # Verify results
        assert result["status"] == "success"
        assert result["consensus"] == "VALID"
        assert result["model_count"] == 3
        assert result["consensus_achieved"] is True
        assert result["provider_diversity"]["cloud_providers"] == 2
        assert result["provider_diversity"]["local_providers"] == 1
        assert result["provider_diversity"]["is_decentralized"] is True

        # Check weighted averages are calculated
        assert 0.7 <= result["average_confidence"] <= 1.0
        assert 0.7 <= result["average_clarity"] <= 1.0

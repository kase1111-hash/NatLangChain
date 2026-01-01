"""
NatLangChain - Multi-Model Consensus

Implements cross-model validation to eliminate hallucination risk and
reduce centralization by using multiple LLM providers for robust consensus.

Supported Providers:
- Anthropic Claude (cloud) - Nuance specialist
- OpenAI GPT-4/GPT-4o (cloud) - Breadth specialist
- Google Gemini (cloud) - Balanced capabilities
- xAI Grok (cloud) - Logic specialist
- Ollama (local) - Fast local inference
- llama.cpp (local) - Ultra-fast GGUF inference

This addresses the centralization risk identified in blockchain research:
"Unlike PoW/PoS where anyone can participate, LLM validation requires API access"

By supporting 6+ providers including 2 local options, any node can participate
in validation without depending on a single cloud provider.
"""

import json
import logging
from typing import Any

from src.llm_providers import (
    LLMProvider,
    LLMResponse,
    ProviderManager,
    ProviderStrength,
    ProviderType,
)

# Configure module-level logger
logger = logging.getLogger(__name__)


class MultiModelConsensus:
    """
    Multi-model consensus validator using diverse LLM providers.

    As described in Future.md's Tiered Validation Stack:
    "Cross-references Claude (Nuance), GPT (Breadth), Llama (Logic), and Grok (Speed)
    to eliminate hallucination and centralization risk"

    Uses multiple LLM providers and models to achieve robust validation
    through majority voting or weighted consensus.
    """

    def __init__(
        self,
        provider_manager: ProviderManager | None = None,
        auto_discover: bool = True,
        min_providers: int = 1,
        required_providers: list[str] | None = None,
    ):
        """
        Initialize multi-model consensus.

        Args:
            provider_manager: Pre-configured provider manager (optional)
            auto_discover: Automatically discover available providers
            min_providers: Minimum providers required for consensus
            required_providers: List of provider names that must be available

        Raises:
            ValueError: If fewer than min_providers are available
        """
        if provider_manager:
            self.provider_manager = provider_manager
        else:
            self.provider_manager = ProviderManager(
                auto_discover=auto_discover,
                required_providers=required_providers,
            )

        if self.provider_manager.provider_count < min_providers:
            available = list(self.provider_manager.providers.keys())
            raise ValueError(
                f"At least {min_providers} LLM provider(s) required, "
                f"but only {len(available)} available: {available}\n"
                "Configure providers via environment variables:\n"
                "  Cloud: ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY, XAI_API_KEY\n"
                "  Local: Start 'ollama serve' or 'llama-server'"
            )

        # Log available providers
        providers = self.provider_manager.list_providers()
        logger.info(
            "MultiModelConsensus initialized with %d providers: %s",
            len(providers),
            [p["name"] for p in providers],
        )

    @property
    def providers(self) -> dict[str, LLMProvider]:
        """Access to underlying providers dict for backwards compatibility."""
        return self.provider_manager.providers

    @property
    def models(self) -> dict[str, dict[str, Any]]:
        """
        Backwards-compatible access to model configurations.

        Returns dict in old format: {name: {client, model_id, strength, weight}}
        """
        result = {}
        for name, provider in self.provider_manager.providers.items():
            result[name] = {
                "provider": provider,
                "model_id": provider.config.model_id,
                "strength": provider.config.strength.value,
                "weight": provider.config.weight,
            }
        return result

    def validate_with_consensus(
        self,
        content: str,
        intent: str,
        author: str,
        consensus_threshold: float = 0.66,
        require_cloud: bool = False,
        require_local: bool = False,
    ) -> dict[str, Any]:
        """
        Validate entry using multi-model consensus.

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author
            consensus_threshold: Minimum agreement ratio (0.0-1.0)
            require_cloud: Require at least one cloud provider response
            require_local: Require at least one local provider response

        Returns:
            Consensus validation result with model breakdown
        """
        validations = []

        # Validation prompt
        prompt = f"""Validate this blockchain entry for clarity and intent:

AUTHOR: {author}
STATED INTENT: {intent}
CONTENT: {content}

Assess:
1. Does content match stated intent?
2. Is the content clear and unambiguous?
3. Are there any contradictions or issues?

Return JSON:
{{
    "valid": true/false,
    "confidence": 0.0-1.0,
    "intent_match": true/false,
    "clarity_score": 0.0-1.0,
    "issues": ["list of any issues found"],
    "reasoning": "explanation"
}}"""

        # Query each available provider
        cloud_responses = 0
        local_responses = 0

        for name, provider in self.provider_manager.providers.items():
            try:
                response = provider.complete(prompt)
                if response.success and response.content:
                    parsed = provider.parse_json_response(response.content)
                    if parsed:
                        validations.append({
                            "model": name,
                            "strength": provider.config.strength.value,
                            "weight": provider.config.weight,
                            "type": provider.config.provider_type.value,
                            "latency_ms": response.latency_ms,
                            "result": parsed,
                        })

                        if provider.config.provider_type == ProviderType.CLOUD:
                            cloud_responses += 1
                        else:
                            local_responses += 1
            except Exception as e:
                logger.warning(
                    "Provider '%s' validation failed during consensus: %s: %s",
                    name,
                    type(e).__name__,
                    str(e),
                )

        # Check diversity requirements
        if require_cloud and cloud_responses == 0:
            return {
                "status": "error",
                "consensus": "FAILED",
                "reason": "No cloud provider responses (required)",
            }

        if require_local and local_responses == 0:
            return {
                "status": "error",
                "consensus": "FAILED",
                "reason": "No local provider responses (required)",
            }

        if not validations:
            return {
                "status": "error",
                "consensus": "FAILED",
                "reason": "All providers failed to validate",
            }

        # Calculate consensus
        return self._calculate_consensus(validations, consensus_threshold)

    def _query_model(self, model_name: str, prompt: str) -> dict[str, Any] | None:
        """
        Query a specific model (backwards compatible method).

        Args:
            model_name: Name of provider to query
            prompt: Validation prompt

        Returns:
            Parsed JSON response or None
        """
        provider = self.provider_manager.get_provider(model_name)
        if not provider:
            return None

        response = provider.complete(prompt)
        if response.success and response.content:
            return provider.parse_json_response(response.content)
        return None

    def _calculate_consensus(
        self,
        validations: list[dict[str, Any]],
        threshold: float,
    ) -> dict[str, Any]:
        """
        Calculate consensus from multiple model validations.

        Uses weighted voting based on provider strengths.

        Args:
            validations: List of model validations
            threshold: Consensus threshold

        Returns:
            Consensus result with detailed breakdown
        """
        if not validations:
            return {"consensus": "NO_MODELS"}

        # Count valid/invalid votes with weights
        total_weight = sum(v["weight"] for v in validations)
        valid_weight = sum(v["weight"] for v in validations if v["result"].get("valid"))
        invalid_weight = total_weight - valid_weight

        valid_ratio = valid_weight / total_weight
        invalid_ratio = invalid_weight / total_weight

        # Determine consensus
        if valid_ratio >= threshold:
            consensus_decision = "VALID"
        elif invalid_ratio >= threshold:
            consensus_decision = "INVALID"
        else:
            consensus_decision = "NO_CONSENSUS"

        # Aggregate confidence (weighted average)
        avg_confidence = sum(
            v["result"].get("confidence", 0.5) * v["weight"] for v in validations
        ) / total_weight

        # Aggregate clarity (weighted average)
        avg_clarity = sum(
            v["result"].get("clarity_score", 0.5) * v["weight"] for v in validations
        ) / total_weight

        # Collect all issues with provider attribution
        all_issues = []
        for v in validations:
            issues = v["result"].get("issues", [])
            for issue in issues:
                if issue not in all_issues:
                    all_issues.append(f"[{v['model']}] {issue}")

        # Calculate provider diversity metrics
        cloud_count = sum(1 for v in validations if v["type"] == "cloud")
        local_count = sum(1 for v in validations if v["type"] == "local")

        # Average latency
        avg_latency = sum(v.get("latency_ms", 0) for v in validations) / len(validations)

        return {
            "status": "success",
            "consensus": consensus_decision,
            "model_count": len(validations),
            "valid_votes": valid_weight,
            "invalid_votes": invalid_weight,
            "valid_ratio": round(valid_ratio, 3),
            "consensus_threshold": threshold,
            "consensus_achieved": consensus_decision != "NO_CONSENSUS",
            "average_confidence": round(avg_confidence, 3),
            "average_clarity": round(avg_clarity, 3),
            "issues_found": all_issues,
            "provider_diversity": {
                "cloud_providers": cloud_count,
                "local_providers": local_count,
                "is_decentralized": local_count > 0,
            },
            "average_latency_ms": round(avg_latency, 2),
            "model_validations": validations,
        }

    def cross_verify_contract_match(
        self,
        contract1: str,
        contract2: str,
        min_models: int = 2,
    ) -> dict[str, Any]:
        """
        Cross-verify contract matching using multiple models.

        Reduces risk of incorrect matches by requiring multi-provider agreement.

        Args:
            contract1: First contract
            contract2: Second contract
            min_models: Minimum models required for consensus

        Returns:
            Cross-verified match result
        """
        prompt = f"""Rate the compatibility of these two contracts (0-100):

CONTRACT A:
{contract1}

CONTRACT B:
{contract2}

Assess if they are complementary (e.g., one offers what the other seeks).

Return JSON:
{{
    "match_score": 0-100,
    "compatible": true/false,
    "reasoning": "explanation",
    "confidence": 0.0-1.0
}}"""

        scores = []

        for name, provider in self.provider_manager.providers.items():
            try:
                response = provider.complete(prompt)
                if response.success and response.content:
                    result = provider.parse_json_response(response.content)
                    if result:
                        scores.append({
                            "model": name,
                            "type": provider.config.provider_type.value,
                            "score": result.get("match_score", 0),
                            "compatible": result.get("compatible", False),
                            "confidence": result.get("confidence", 0.5),
                            "latency_ms": response.latency_ms,
                        })
            except Exception as e:
                logger.warning(
                    "Provider '%s' contract match verification failed: %s: %s",
                    name,
                    type(e).__name__,
                    str(e),
                )

        if len(scores) < min_models:
            return {
                "status": "insufficient_models",
                "match_verified": False,
                "reason": f"Need at least {min_models} models, got {len(scores)}",
            }

        # Calculate average score
        avg_score = sum(s["score"] for s in scores) / len(scores)

        # Count compatible votes
        compatible_votes = sum(1 for s in scores if s["compatible"])

        # Consensus if majority agree
        consensus_compatible = compatible_votes > len(scores) / 2

        return {
            "status": "success",
            "match_verified": consensus_compatible,
            "average_match_score": round(avg_score, 2),
            "compatible_votes": compatible_votes,
            "total_models": len(scores),
            "model_scores": scores,
            "consensus_reached": True,
        }

    def get_provider_stats(self) -> dict[str, Any]:
        """
        Get statistics about available providers.

        Returns:
            Provider statistics and configuration
        """
        providers = self.provider_manager.list_providers()

        by_type = {"cloud": [], "local": []}
        by_strength = {}

        for p in providers:
            by_type[p["type"]].append(p["name"])
            strength = p["strength"]
            if strength not in by_strength:
                by_strength[strength] = []
            by_strength[strength].append(p["name"])

        return {
            "total_providers": len(providers),
            "providers": providers,
            "by_type": by_type,
            "by_strength": by_strength,
            "has_cloud": len(by_type["cloud"]) > 0,
            "has_local": len(by_type["local"]) > 0,
            "is_decentralized": len(by_type["local"]) > 0,
            "can_operate_offline": len(by_type["local"]) > 0 and len(by_type["cloud"]) == 0,
        }


class HallucinationDetector:
    """
    Detects potential LLM hallucinations through cross-model verification.

    If providers disagree significantly, flags potential hallucination.
    Uses multi-provider diversity to increase detection reliability.
    """

    def __init__(self, consensus: MultiModelConsensus):
        """
        Initialize hallucination detector.

        Args:
            consensus: Multi-model consensus instance
        """
        self.consensus = consensus

    def detect_hallucination(
        self,
        prompt: str,
        expected_factual: bool = True,
    ) -> dict[str, Any]:
        """
        Detect potential hallucination by checking model agreement.

        Args:
            prompt: Prompt to evaluate
            expected_factual: Whether response should be factual

        Returns:
            Hallucination detection result
        """
        responses = []

        for name, provider in self.consensus.provider_manager.providers.items():
            try:
                response = provider.complete(prompt)
                if response.success and response.content:
                    result = provider.parse_json_response(response.content)
                    if result:
                        responses.append({
                            "model": name,
                            "type": provider.config.provider_type.value,
                            "response": result,
                        })
            except Exception as e:
                logger.warning(
                    "Provider '%s' hallucination detection failed: %s: %s",
                    name,
                    type(e).__name__,
                    str(e),
                )

        if len(responses) < 2:
            return {
                "hallucination_risk": "unknown",
                "reason": "Insufficient providers for comparison",
            }

        # Check for significant disagreement
        unique_decisions = {
            str(r["response"].get("valid", "unknown")) for r in responses
        }

        disagreement = len(unique_decisions) > 1

        # Check if local and cloud providers agree
        cloud_decisions = {
            str(r["response"].get("valid", "unknown"))
            for r in responses
            if r["type"] == "cloud"
        }
        local_decisions = {
            str(r["response"].get("valid", "unknown"))
            for r in responses
            if r["type"] == "local"
        }

        cross_type_agreement = bool(
            cloud_decisions and local_decisions and cloud_decisions == local_decisions
        )

        return {
            "hallucination_risk": "high" if disagreement else "low",
            "model_agreement": not disagreement,
            "cross_type_agreement": cross_type_agreement,
            "model_count": len(responses),
            "cloud_responses": len([r for r in responses if r["type"] == "cloud"]),
            "local_responses": len([r for r in responses if r["type"] == "local"]),
            "unique_responses": len(unique_decisions),
            "responses": responses,
            "recommendation": "REVIEW" if disagreement else "PROCEED",
        }


# =============================================================================
# Convenience Functions
# =============================================================================


def create_consensus_validator(
    min_providers: int = 1,
    required_providers: list[str] | None = None,
) -> MultiModelConsensus:
    """
    Create a consensus validator with auto-discovered providers.

    Args:
        min_providers: Minimum required providers
        required_providers: Specific providers that must be available

    Returns:
        Configured MultiModelConsensus instance
    """
    return MultiModelConsensus(
        auto_discover=True,
        min_providers=min_providers,
        required_providers=required_providers,
    )


def quick_validate(
    content: str,
    intent: str,
    author: str = "anonymous",
) -> dict[str, Any]:
    """
    Quick validation using all available providers.

    Args:
        content: Entry content
        intent: Entry intent
        author: Entry author

    Returns:
        Consensus validation result
    """
    try:
        consensus = MultiModelConsensus(auto_discover=True, min_providers=1)
        return consensus.validate_with_consensus(content, intent, author)
    except ValueError as e:
        return {
            "status": "error",
            "consensus": "FAILED",
            "reason": str(e),
        }

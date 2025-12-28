"""
NatLangChain - Multi-Model Consensus
Implements cross-model validation to eliminate hallucination risk
Uses multiple LLM providers for robust consensus
"""

import os
import json
import logging
from typing import Dict, Any, Optional, List
from anthropic import Anthropic

# Configure module-level logger
logger = logging.getLogger(__name__)


class MultiModelConsensus:
    """
    Multi-model consensus validator.

    As described in Future.md's Tiered Validation Stack:
    "Cross-references Claude 3.5 (Nuance), Llama 4 (Logic), and GPT-5 (Breadth)
    to eliminate hallucination"

    Uses multiple LLM providers and models to achieve robust validation
    through majority voting or weighted consensus.
    """

    def __init__(self, anthropic_api_key: Optional[str] = None):
        """
        Initialize multi-model consensus.

        Note: Currently supports Claude (Anthropic). Can be extended to:
        - OpenAI GPT-4/GPT-5
        - Meta Llama via replicate/together
        - Google Gemini
        - Local models via ollama

        Args:
            anthropic_api_key: Anthropic API key
        """
        self.anthropic_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")

        # Initialize available models
        self.models = {}

        if self.anthropic_key:
            self.models["claude"] = {
                "client": Anthropic(api_key=self.anthropic_key),
                "model_id": "claude-3-5-sonnet-20241022",
                "strength": "nuance",  # Best at semantic nuance
                "weight": 1.0
            }

        # Placeholder for future model integration
        # self.models["gpt5"] = {...}  # Breadth
        # self.models["llama4"] = {...}  # Logic

        if not self.models:
            raise ValueError("At least one LLM provider required")

    def validate_with_consensus(
        self,
        content: str,
        intent: str,
        author: str,
        consensus_threshold: float = 0.66
    ) -> Dict[str, Any]:
        """
        Validate entry using multi-model consensus.

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author
            consensus_threshold: Minimum agreement ratio (0.0-1.0)

        Returns:
            Consensus validation result
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

        # Query each available model
        for model_name, model_config in self.models.items():
            try:
                result = self._query_model(model_name, prompt)
                if result:
                    validations.append({
                        "model": model_name,
                        "strength": model_config["strength"],
                        "weight": model_config["weight"],
                        "result": result
                    })
            except Exception as e:
                logger.warning(
                    "Model '%s' validation failed during consensus: %s: %s",
                    model_name, type(e).__name__, str(e)
                )

        if not validations:
            return {
                "status": "error",
                "consensus": "FAILED",
                "reason": "All models failed to validate"
            }

        # Calculate consensus
        return self._calculate_consensus(validations, consensus_threshold)

    def _query_model(self, model_name: str, prompt: str) -> Optional[Dict[str, Any]]:
        """
        Query a specific model.

        Args:
            model_name: Name of model to query
            prompt: Validation prompt

        Returns:
            Model's response as dict or None

        Raises:
            ValueError: If API response format is invalid
            json.JSONDecodeError: If response cannot be parsed as JSON
        """
        model_config = self.models.get(model_name)
        if not model_config:
            return None

        if model_name == "claude":
            message = model_config["client"].messages.create(
                model=model_config["model_id"],
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )

            # Safe access to API response with clear error messages
            if not message.content:
                raise ValueError(f"Empty response from model '{model_name}': no content returned")
            if not hasattr(message.content[0], 'text'):
                raise ValueError(f"Invalid response format from model '{model_name}': missing 'text' attribute")

            response_text = message.content[0].text

            # Extract JSON from response
            response_text = self._extract_json_from_response(response_text)

            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                raise json.JSONDecodeError(
                    f"Failed to parse JSON from model '{model_name}' response: {e.msg}",
                    e.doc,
                    e.pos
                )

        # Add other model handlers here
        # elif model_name == "gpt5": ...
        # elif model_name == "llama4": ...

        return None

    def _extract_json_from_response(self, response_text: str) -> str:
        """
        Extract JSON from a response that may contain markdown code blocks.

        Args:
            response_text: Raw response text

        Returns:
            Extracted JSON string

        Raises:
            ValueError: If JSON extraction fails
        """
        if "```json" in response_text:
            json_start = response_text.find("```json") + 7
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                raise ValueError("Malformed response: unclosed JSON code block")
            return response_text[json_start:json_end].strip()
        elif "```" in response_text:
            json_start = response_text.find("```") + 3
            json_end = response_text.find("```", json_start)
            if json_end == -1:
                raise ValueError("Malformed response: unclosed code block")
            return response_text[json_start:json_end].strip()
        return response_text.strip()

    def _calculate_consensus(
        self,
        validations: List[Dict[str, Any]],
        threshold: float
    ) -> Dict[str, Any]:
        """
        Calculate consensus from multiple model validations.

        Args:
            validations: List of model validations
            threshold: Consensus threshold

        Returns:
            Consensus result
        """
        if not validations:
            return {"consensus": "NO_MODELS"}

        # Count valid/invalid votes
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

        # Aggregate confidence
        avg_confidence = sum(
            v["result"].get("confidence", 0.5) * v["weight"]
            for v in validations
        ) / total_weight

        # Aggregate clarity
        avg_clarity = sum(
            v["result"].get("clarity_score", 0.5) * v["weight"]
            for v in validations
        ) / total_weight

        # Collect all issues
        all_issues = []
        for v in validations:
            issues = v["result"].get("issues", [])
            for issue in issues:
                if issue not in all_issues:
                    all_issues.append(f"[{v['model']}] {issue}")

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
            "model_validations": validations
        }

    def cross_verify_contract_match(
        self,
        contract1: str,
        contract2: str,
        min_models: int = 2
    ) -> Dict[str, Any]:
        """
        Cross-verify contract matching using multiple models.

        Reduces risk of incorrect matches.

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

        for model_name in self.models.keys():
            try:
                result = self._query_model(model_name, prompt)
                if result:
                    scores.append({
                        "model": model_name,
                        "score": result.get("match_score", 0),
                        "compatible": result.get("compatible", False),
                        "confidence": result.get("confidence", 0.5)
                    })
            except Exception as e:
                logger.warning(
                    "Model '%s' contract match verification failed: %s: %s",
                    model_name, type(e).__name__, str(e)
                )

        if len(scores) < min_models:
            return {
                "status": "insufficient_models",
                "match_verified": False,
                "reason": f"Need at least {min_models} models, got {len(scores)}"
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
            "consensus_reached": True
        }


class HallucimationDetector:
    """
    Detects potential LLM hallucinations through cross-model verification.

    If models disagree significantly, flags potential hallucination.
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
        expected_factual: bool = True
    ) -> Dict[str, Any]:
        """
        Detect potential hallucination by checking model agreement.

        Args:
            prompt: Prompt to evaluate
            expected_factual: Whether response should be factual

        Returns:
            Hallucination detection result
        """
        responses = []

        for model_name in self.consensus.models.keys():
            try:
                result = self.consensus._query_model(model_name, prompt)
                if result:
                    responses.append({
                        "model": model_name,
                        "response": result
                    })
            except Exception as e:
                logger.warning(
                    "Model '%s' hallucination detection failed: %s: %s",
                    model_name, type(e).__name__, str(e)
                )

        if len(responses) < 2:
            return {
                "hallucination_risk": "unknown",
                "reason": "Insufficient models for comparison"
            }

        # Check for significant disagreement
        # (Simple version - can be enhanced with semantic similarity)
        unique_decisions = set(
            str(r["response"].get("valid", "unknown"))
            for r in responses
        )

        disagreement = len(unique_decisions) > 1

        return {
            "hallucination_risk": "high" if disagreement else "low",
            "model_agreement": not disagreement,
            "model_count": len(responses),
            "unique_responses": len(unique_decisions),
            "responses": responses,
            "recommendation": "REVIEW" if disagreement else "PROCEED"
        }

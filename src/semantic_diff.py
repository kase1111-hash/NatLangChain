"""
NatLangChain - Semantic Drift Detection
Evaluates semantic drift between on-chain intent and real-time execution logs
Integrated version with correct data structures

Implements NCIP-002 drift thresholds and mandatory validator responses.
"""

import json
import os
from typing import Any, Optional

from anthropic import Anthropic

# Import NCIP-002 drift classification
try:
    from drift_thresholds import (
        DriftClassification,
        DriftLevel,
        SemanticDriftClassifier,
        TemporalFixityContext,
        classify_drift_score,
        get_mandatory_response,
    )

    NCIP_002_AVAILABLE = True
except ImportError:
    NCIP_002_AVAILABLE = False


class SemanticDriftDetector:
    """
    Evaluates 'Semantic Drift' between on-chain Intent Prose
    and real-time Agent Execution.

    This is a security feature that helps prevent agents from deviating
    from their stated intentions recorded on the blockchain.

    Integrates NCIP-002 drift thresholds for normative classification:
    - D0 (0.00-0.10): Stable
    - D1 (0.10-0.25): Soft Drift
    - D2 (0.25-0.45): Ambiguous Drift
    - D3 (0.45-0.70): Hard Drift
    - D4 (0.70-1.00): Semantic Break
    """

    def __init__(
        self,
        api_key: str | None = None,
        validator_id: str = "default",
        enable_ncip_002: bool = True,
    ):
        """
        Initialize the semantic drift detector.

        Args:
            api_key: Anthropic API key (defaults to env variable)
            validator_id: Identifier for this validator instance
            enable_ncip_002: Enable NCIP-002 drift classification
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for drift detection")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.threshold = 0.7  # Legacy threshold (D4 boundary per NCIP-002)

        # NCIP-002 integration
        self.enable_ncip_002 = enable_ncip_002 and NCIP_002_AVAILABLE
        self.validator_id = validator_id
        self._classifier = None

    @property
    def classifier(self) -> Optional["SemanticDriftClassifier"]:
        """Get the NCIP-002 drift classifier (lazy initialization)."""
        if self._classifier is None and self.enable_ncip_002:
            self._classifier = SemanticDriftClassifier(validator_id=self.validator_id)
        return self._classifier

    def check_alignment(self, on_chain_intent: str, execution_log: str) -> dict[str, Any]:
        """
        Uses LLM to detect inconsistencies between intent and action.

        This implements a "Semantic Firewall" that can trigger circuit breakers
        if an agent's actions diverge from its stated on-chain intent.

        Args:
            on_chain_intent: The canonical intent from the blockchain entry
            execution_log: The real-time execution log or action description

        Returns:
            Dict with drift analysis including score, violation flag, and reasoning
        """
        try:
            prompt = f"""[NatLangChain Security Protocol]
Compare the following CANONICAL INTENT against the EXECUTION LOG.

CANONICAL INTENT (Immutable): "{on_chain_intent}"
EXECUTION LOG (Real-time): "{execution_log}"

Task:
1. Identify if the action violates the spirit of the intent.
2. Assign a 'Divergence Score' from 0 (Perfect Match) to 1 (Adversarial Drift).
3. Flag for Circuit Breaker if Score > {self.threshold}.

Return JSON only:
{{
    "score": float (0.0-1.0),
    "is_violating": bool,
    "reason": str,
    "recommended_action": "ALLOW/WARN/BLOCK"
}}"""

            message = self.client.messages.create(
                model=self.model, max_tokens=500, messages=[{"role": "user", "content": prompt}]
            )

            # Extract and parse JSON response
            response_text = message.content[0].text

            # Handle markdown code blocks
            if "```json" in response_text:
                json_start = response_text.find("```json") + 7
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()
            elif "```" in response_text:
                json_start = response_text.find("```") + 3
                json_end = response_text.find("```", json_start)
                response_text = response_text[json_start:json_end].strip()

            result = json.loads(response_text)

            response = {
                "status": "success",
                "drift_analysis": result,
                "threshold": self.threshold,
                "alert": result.get("score", 0) > self.threshold,
            }

            # Add NCIP-002 classification if enabled
            score = result.get("score")
            if self.enable_ncip_002 and self.classifier and score is not None:
                ncip_response = self.classifier.get_validator_response(score)
                response["ncip_002"] = ncip_response
                response["drift_level"] = ncip_response["drift_level"]

            return response

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "drift_analysis": {
                    "score": None,
                    "is_violating": None,
                    "reason": f"Analysis failed: {e!s}",
                    "recommended_action": "ERROR",
                },
            }

    def check_entry_execution_alignment(
        self, entry_content: str, entry_intent: str, execution_log: str
    ) -> dict[str, Any]:
        """
        Check alignment between a blockchain entry and its execution.

        This combines the entry content and intent into a canonical representation
        before checking alignment with execution logs.

        Args:
            entry_content: The natural language content from the blockchain entry
            entry_intent: The stated intent from the blockchain entry
            execution_log: The execution log or action description

        Returns:
            Drift analysis result
        """
        # Combine content and intent for canonical representation
        canonical = f"Intent: {entry_intent}. Content: {entry_content}"

        return self.check_alignment(canonical, execution_log)

    def set_threshold(self, threshold: float):
        """
        Set the drift sensitivity threshold.

        Args:
            threshold: Float between 0.0 and 1.0. Higher means more tolerant of drift.
        """
        if not 0.0 <= threshold <= 1.0:
            raise ValueError("Threshold must be between 0.0 and 1.0")

        self.threshold = threshold

    def check_alignment_ncip_002(
        self,
        on_chain_intent: str,
        execution_log: str,
        affected_terms: list[str] | None = None,
        entry_id: str | None = None,
    ) -> dict[str, Any]:
        """
        NCIP-002 compliant drift check with mandatory responses.

        This method provides full NCIP-002 compliance including:
        - Drift level classification (D0-D4)
        - Mandatory validator responses per level
        - Logging for D2+ events
        - Action recommendations

        Args:
            on_chain_intent: The canonical intent from the blockchain entry
            execution_log: The real-time execution log or action description
            affected_terms: Optional list of affected canonical terms
            entry_id: Optional entry ID for logging

        Returns:
            Dict with NCIP-002 compliant drift analysis and actions
        """
        # Get basic alignment check
        base_result = self.check_alignment(on_chain_intent, execution_log)

        if base_result["status"] != "success":
            return base_result

        score = base_result["drift_analysis"].get("score")
        if score is None:
            return base_result

        # Build NCIP-002 response
        if not self.enable_ncip_002 or not self.classifier:
            return base_result

        # Get full validator response with logging
        ncip_response = self.classifier.get_validator_response(
            score=score,
            affected_terms=affected_terms,
            source=f"Intent: {on_chain_intent[:100]}... vs Execution: {execution_log[:100]}...",
            entry_id=entry_id,
        )

        # Combine responses
        result = {
            "status": "success",
            "drift_score": score,
            "drift_level": ncip_response["drift_level"],
            "classification": ncip_response["classification"],
            "message": ncip_response["message"],
            "legacy_analysis": base_result["drift_analysis"],
            "ncip_002": ncip_response,
            "validator_actions": ncip_response["actions"],
            "requires_human": ncip_response["requires_human"],
        }

        return result

    def aggregate_component_drift(self, component_scores: dict[str, float]) -> dict[str, Any]:
        """
        Aggregate drift scores from multiple components per NCIP-002.

        Per NCIP-002 Section 6: The maximum drift score governs response.

        Args:
            component_scores: Dict mapping component names to drift scores
                            e.g., {"term_a": 0.2, "clause_b": 0.5}

        Returns:
            Aggregated drift result with governing component
        """
        if not self.enable_ncip_002 or not self.classifier:
            # Fallback without NCIP-002
            if not component_scores:
                return {"max_score": 0.0, "governing_component": "none"}
            max_component = max(component_scores, key=component_scores.get)
            return {
                "max_score": component_scores[max_component],
                "governing_component": max_component,
                "component_scores": component_scores,
            }

        aggregated = self.classifier.aggregate_drift(component_scores)

        return {
            "max_score": aggregated.max_score,
            "drift_level": aggregated.max_level.value,
            "governing_component": aggregated.governing_component,
            "component_scores": aggregated.component_scores,
            "classification": aggregated.classification.classification,
            "message": aggregated.classification.message,
            "actions": {
                "proceed": self.classifier.should_proceed(aggregated.classification),
                "warn": self.classifier.should_warn(aggregated.classification),
                "pause": self.classifier.should_pause(aggregated.classification),
                "require_ratification": self.classifier.should_require_ratification(
                    aggregated.classification
                ),
                "reject": self.classifier.should_reject(aggregated.classification),
                "escalate_dispute": self.classifier.should_escalate(aggregated.classification),
            },
            "requires_human": aggregated.classification.requires_human,
        }

    def get_drift_level(self, score: float) -> str:
        """
        Get the NCIP-002 drift level for a score.

        Args:
            score: Drift score [0.0, 1.0]

        Returns:
            Drift level string (D0, D1, D2, D3, D4)
        """
        if not self.enable_ncip_002 or not self.classifier:
            # Fallback classification
            if score < 0.10:
                return "D0"
            elif score < 0.25:
                return "D1"
            elif score < 0.45:
                return "D2"
            elif score < 0.70:
                return "D3"
            else:
                return "D4"

        classification = self.classifier.classify(score)
        return classification.level.value

    def get_drift_log(self) -> list[dict[str, Any]]:
        """
        Get the drift event log.

        Returns:
            List of logged drift events (D2 and above)
        """
        if not self.enable_ncip_002 or not self.classifier:
            return []

        return [
            {
                "timestamp": entry.timestamp,
                "drift_score": entry.drift_score,
                "drift_level": entry.drift_level,
                "affected_terms": entry.affected_terms,
                "source_of_divergence": entry.source_of_divergence,
                "validator_id": entry.validator_id,
                "entry_id": entry.entry_id,
            }
            for entry in self.classifier.get_drift_log()
        ]

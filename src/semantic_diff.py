"""
NatLangChain - Semantic Drift Detection
Evaluates semantic drift between on-chain intent and real-time execution logs
Integrated version with correct data structures
"""

import os
import json
from typing import Dict, Any, Optional
from anthropic import Anthropic


class SemanticDriftDetector:
    """
    Evaluates 'Semantic Drift' between on-chain Intent Prose
    and real-time Agent Execution.

    This is a security feature that helps prevent agents from deviating
    from their stated intentions recorded on the blockchain.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the semantic drift detector.

        Args:
            api_key: Anthropic API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for drift detection")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"
        self.threshold = 0.7  # Drift sensitivity (0.0-1.0)

    def check_alignment(
        self,
        on_chain_intent: str,
        execution_log: str
    ) -> Dict[str, Any]:
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
                model=self.model,
                max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
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

            return {
                "status": "success",
                "drift_analysis": result,
                "threshold": self.threshold,
                "alert": result.get("score", 0) > self.threshold
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "drift_analysis": {
                    "score": None,
                    "is_violating": None,
                    "reason": f"Analysis failed: {str(e)}",
                    "recommended_action": "ERROR"
                }
            }

    def check_entry_execution_alignment(
        self,
        entry_content: str,
        entry_intent: str,
        execution_log: str
    ) -> Dict[str, Any]:
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

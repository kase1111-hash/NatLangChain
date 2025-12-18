"""
NatLangChain - Dialectic Consensus
Implements debate-based validation using Skeptic/Facilitator roles
Integrated version with correct data structures
"""

import os
import json
from typing import Dict, Any, Optional
from anthropic import Anthropic


class DialecticConsensus:
    """
    Implements a debate-based consensus mechanism for validating blockchain entries.

    Uses a dialectic approach with two roles:
    - Skeptic: Critically examines entries for ambiguities and loopholes
    - Facilitator: Extracts core intent and economic spirit

    The system achieves consensus by reconciling these perspectives.
    This is particularly useful for financial or legal entries where
    precision is critical.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the dialectic consensus system.

        Args:
            api_key: Anthropic API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for dialectic consensus")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def validate_entry(
        self,
        content: str,
        intent: str,
        author: str
    ) -> Dict[str, Any]:
        """
        Validate an entry through dialectic debate.

        The Skeptic looks for problems while the Facilitator seeks understanding.
        Their perspectives are reconciled to reach a final decision.

        Args:
            content: The natural language content to validate
            intent: The stated intent
            author: The entry author

        Returns:
            Validation result with dialectic analysis
        """
        try:
            # Step 1: Skeptic analysis
            skeptic_analysis = self._skeptic_review(content, intent)

            # Step 2: Facilitator analysis
            facilitator_analysis = self._facilitator_review(content, intent)

            # Step 3: Reconciliation
            final_decision = self._reconcile_perspectives(
                content,
                intent,
                skeptic_analysis,
                facilitator_analysis
            )

            return {
                "status": "success",
                "method": "dialectic_consensus",
                "skeptic_perspective": skeptic_analysis,
                "facilitator_perspective": facilitator_analysis,
                "final_decision": final_decision,
                "decision": final_decision.get("status", "ERROR")
            }

        except Exception as e:
            return {
                "status": "error",
                "error": str(e),
                "decision": "ERROR"
            }

    def _skeptic_review(self, content: str, intent: str) -> Dict[str, Any]:
        """
        The Skeptic: Critically examines for ambiguity and loopholes.

        Args:
            content: Entry content
            intent: Entry intent

        Returns:
            Skeptic's analysis
        """
        prompt = f"""Role: The Skeptic (Financial Auditor/Critical Examiner)

You are reviewing a NatLangChain entry for inclusion in an immutable ledger.
Be extremely critical and look for problems.

STATED INTENT: {intent}
ENTRY CONTENT: {content}

Task: Identify any issues that would make this entry problematic:
1. Vague or ambiguous terms (e.g., "soon", "some", "approximately")
2. Force majeure loopholes or escape clauses
3. Unclear timelines or deadlines
4. Undefined quantities or values
5. Missing critical details
6. Contradictions between intent and content

Be thorough and critical. This will be used in financial/legal contexts.

Return JSON:
{{
    "concerns": ["list of specific concerns"],
    "severity": "CRITICAL/MODERATE/MINOR/NONE",
    "ambiguous_terms": ["list of ambiguous terms found"],
    "recommendation": "REJECT/NEEDS_CLARIFICATION/ACCEPTABLE",
    "reasoning": "explanation of your assessment"
}}"""

        return self._call_llm(prompt, role="Skeptic")

    def _facilitator_review(self, content: str, intent: str) -> Dict[str, Any]:
        """
        The Facilitator: Extracts core intent and spirit.

        Args:
            content: Entry content
            intent: Entry intent

        Returns:
            Facilitator's analysis
        """
        prompt = f"""Role: The Facilitator (Intent Specialist/Interpreter)

You are reviewing a NatLangChain entry to understand its core purpose.
Focus on extracting the essential meaning and economic/operational spirit.

STATED INTENT: {intent}
ENTRY CONTENT: {content}

Task: Analyze the entry's core meaning:
1. Provide a 1-sentence summary of the canonical intent
2. Identify the primary outcome or goal
3. Extract key commitments or obligations
4. Assess if the content aligns with the stated intent
5. Determine if the spirit of the entry is clear

Focus on understanding, not criticism.

Return JSON:
{{
    "canonical_intent": "1-sentence summary of core intent",
    "key_commitments": ["list of commitments/obligations"],
    "primary_outcome": "the main expected result",
    "intent_alignment": true/false,
    "clarity_score": 0.0-1.0,
    "reasoning": "explanation of your interpretation"
}}"""

        return self._call_llm(prompt, role="Facilitator")

    def _reconcile_perspectives(
        self,
        content: str,
        intent: str,
        skeptic: Dict[str, Any],
        facilitator: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Reconcile Skeptic and Facilitator perspectives.

        Args:
            content: Entry content
            intent: Entry intent
            skeptic: Skeptic's analysis
            facilitator: Facilitator's analysis

        Returns:
            Final consensus decision
        """
        prompt = f"""Role: Consensus Engine (Final Arbiter)

You must reconcile two perspectives on a NatLangChain entry:

ENTRY:
Intent: {intent}
Content: {content}

SKEPTIC'S PERSPECTIVE:
{json.dumps(skeptic, indent=2)}

FACILITATOR'S PERSPECTIVE:
{json.dumps(facilitator, indent=2)}

Task: Make a final decision:
1. If Skeptic's concerns are CRITICAL (making entry unenforceable), REJECT
2. If concerns are MODERATE but Facilitator shows clear intent, NEEDS_CLARIFICATION
3. If Facilitator's interpretation is sound and Skeptic's concerns are MINOR, ACCEPT

Return JSON:
{{
    "status": "ACCEPT/NEEDS_CLARIFICATION/REJECT",
    "final_summary": "concise summary of the entry's validated meaning",
    "reasoning": "explanation of decision considering both perspectives",
    "required_clarifications": ["list of clarifications needed if status is NEEDS_CLARIFICATION"],
    "confidence": 0.0-1.0
}}"""

        result = self._call_llm(prompt, role="Consensus_Engine")

        # Map status to standard validation decisions
        status_map = {
            "ACCEPT": "VALID",
            "NEEDS_CLARIFICATION": "NEEDS_CLARIFICATION",
            "REJECT": "INVALID"
        }

        result["decision"] = status_map.get(result.get("status", "REJECT"), "ERROR")

        return result

    def _call_llm(self, prompt: str, role: str) -> Dict[str, Any]:
        """
        Make an API call to Claude for analysis.

        Args:
            prompt: The prompt to send
            role: The role identifier for logging

        Returns:
            Parsed JSON response
        """
        try:
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
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

            return json.loads(response_text)

        except Exception as e:
            return {
                "error": str(e),
                "role": role,
                "status": "ERROR"
            }

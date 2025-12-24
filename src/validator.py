"""
NatLangChain - Linguistic Validation
Implements Proof of Understanding using LLM-powered semantic validation
"""

import os
from typing import Dict, List, Tuple, Any, Optional
from anthropic import Anthropic


class ProofOfUnderstanding:
    """
    Implements the core innovation: Proof of Understanding consensus.
    Validators paraphrase entries to demonstrate comprehension and achieve consensus.
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the validator with Anthropic API.

        Args:
            api_key: Anthropic API key (defaults to env variable)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for validation")

        self.client = Anthropic(api_key=self.api_key)
        self.model = "claude-3-5-sonnet-20241022"

    def validate_entry(self, content: str, intent: str, author: str) -> Dict[str, Any]:
        """
        Validate a natural language entry through LLM-powered understanding.

        This implements Proof of Understanding by:
        1. Having the LLM paraphrase the entry
        2. Checking for semantic consistency
        3. Detecting potential ambiguities or adversarial phrasing
        4. Providing validation evidence

        Args:
            content: The natural language content to validate
            intent: The stated intent
            author: The entry author

        Returns:
            Validation result with paraphrase and assessment
        """
        try:
            validation_prompt = f"""You are a validator node in the NatLangChain, a blockchain where natural language is the primary substrate.

Your task is to validate the following entry through "Proof of Understanding":

AUTHOR: {author}
STATED INTENT: {intent}

ENTRY CONTENT:
{content}

Please provide:
1. A paraphrase of the entry in your own words (demonstrating understanding)
2. An assessment of whether the content matches the stated intent
3. Detection of any ambiguities, contradictions, or potential adversarial phrasing
4. A validation decision: VALID, NEEDS_CLARIFICATION, or INVALID

Respond in JSON format:
{{
    "paraphrase": "your paraphrase here",
    "intent_match": true/false,
    "ambiguities": ["list of any ambiguities detected"],
    "adversarial_indicators": ["list of any adversarial patterns detected"],
    "decision": "VALID/NEEDS_CLARIFICATION/INVALID",
    "reasoning": "brief explanation of your decision"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": validation_prompt}
                ]
            )

            # Parse the response
            import json

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during entry validation")
            if not hasattr(message.content[0], 'text'):
                raise ValueError("Invalid API response format: missing 'text' attribute in entry validation")

            response_text = message.content[0].text

            # Extract JSON from response with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                result = json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse validation JSON: {e.msg} at position {e.pos}")

            return {
                "status": "success",
                "validation": result
            }

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"JSON parsing error: {str(e)}",
                "validation": {
                    "decision": "ERROR",
                    "reasoning": f"JSON parsing failed: {str(e)}"
                }
            }
        except ValueError as e:
            return {
                "status": "error",
                "error": f"Validation error: {str(e)}",
                "validation": {
                    "decision": "ERROR",
                    "reasoning": f"Response validation failed: {str(e)}"
                }
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"Unexpected error: {str(e)}",
                "validation": {
                    "decision": "ERROR",
                    "reasoning": f"Validation failed: {str(e)}"
                }
            }

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
        if not response_text or not response_text.strip():
            raise ValueError("Empty response text received")

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

    # Maximum validators to prevent DoS
    MAX_VALIDATORS = 10

    def multi_validator_consensus(
        self,
        content: str,
        intent: str,
        author: str,
        num_validators: int = 3
    ) -> Dict[str, Any]:
        """
        Achieve consensus through multiple validator nodes.

        This simulates a multi-node validation where several LLM instances
        must agree on the interpretation.

        Args:
            content: Entry content
            intent: Stated intent
            author: Entry author
            num_validators: Number of validator nodes to simulate (max 10)

        Returns:
            Consensus result with all validator opinions
        """
        # Bound the number of validators to prevent DoS
        num_validators = min(num_validators, self.MAX_VALIDATORS)
        validations = []

        for i in range(num_validators):
            result = self.validate_entry(content, intent, author)
            if result["status"] == "success":
                validations.append(result["validation"])

        if not validations:
            return {
                "consensus": "FAILED",
                "reason": "All validators encountered errors"
            }

        # Count decisions
        decisions = [v["decision"] for v in validations]
        decision_counts = {
            "VALID": decisions.count("VALID"),
            "NEEDS_CLARIFICATION": decisions.count("NEEDS_CLARIFICATION"),
            "INVALID": decisions.count("INVALID")
        }

        # Determine consensus (simple majority)
        consensus_decision = max(decision_counts, key=decision_counts.get)
        consensus_threshold = num_validators / 2

        if decision_counts[consensus_decision] > consensus_threshold:
            consensus = consensus_decision
        else:
            consensus = "NO_CONSENSUS"

        return {
            "consensus": consensus,
            "validator_count": num_validators,
            "decision_distribution": decision_counts,
            "validations": validations,
            "paraphrases": [v.get("paraphrase", "") for v in validations]
        }

    def detect_semantic_drift(
        self,
        original: str,
        paraphrase: str
    ) -> Dict[str, Any]:
        """
        Detect semantic drift between original and paraphrase.

        This helps identify if validators truly understand the content
        or if there's interpretation divergence.

        Args:
            original: Original entry content
            paraphrase: Validator's paraphrase

        Returns:
            Drift analysis
        """
        try:
            drift_prompt = f"""Compare these two texts for semantic equivalence:

ORIGINAL:
{original}

PARAPHRASE:
{paraphrase}

Assess whether they convey the same meaning. Respond in JSON:
{{
    "semantically_equivalent": true/false,
    "drift_score": 0.0-1.0 (0=identical meaning, 1=completely different),
    "key_differences": ["list of meaning differences if any"],
    "assessment": "brief explanation"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": drift_prompt}
                ]
            )

            import json

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during drift detection")
            if not hasattr(message.content[0], 'text'):
                raise ValueError("Invalid API response format: missing 'text' attribute in drift detection")

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse drift detection JSON: {e.msg} at position {e.pos}")

        except json.JSONDecodeError as e:
            return {
                "error": f"JSON parsing error: {str(e)}",
                "semantically_equivalent": None,
                "drift_score": None
            }
        except ValueError as e:
            return {
                "error": f"Validation error: {str(e)}",
                "semantically_equivalent": None,
                "drift_score": None
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "semantically_equivalent": None,
                "drift_score": None
            }

    def clarification_protocol(
        self,
        content: str,
        ambiguities: List[str]
    ) -> Dict[str, Any]:
        """
        Generate clarification questions for ambiguous entries.

        Part of the multi-round clarification consensus mechanism.

        Args:
            content: The ambiguous content
            ambiguities: List of detected ambiguities

        Returns:
            Suggested clarifications
        """
        try:
            clarification_prompt = f"""The following entry has been flagged for ambiguity:

CONTENT:
{content}

DETECTED AMBIGUITIES:
{chr(10).join(f"- {amb}" for amb in ambiguities)}

Generate specific clarification questions that would resolve these ambiguities. Respond in JSON:
{{
    "clarification_questions": ["question 1", "question 2", ...],
    "suggested_rewording": "a clearer version of the content if possible"
}}"""

            message = self.client.messages.create(
                model=self.model,
                max_tokens=512,
                messages=[
                    {"role": "user", "content": clarification_prompt}
                ]
            )

            import json

            # Safe access to API response
            if not message.content:
                raise ValueError("Empty response from API: no content returned during clarification protocol")
            if not hasattr(message.content[0], 'text'):
                raise ValueError("Invalid API response format: missing 'text' attribute in clarification protocol")

            response_text = message.content[0].text

            # Extract JSON with validation
            response_text = self._extract_json_from_response(response_text)

            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                raise ValueError(f"Failed to parse clarification JSON: {e.msg} at position {e.pos}")

        except json.JSONDecodeError as e:
            return {
                "error": f"JSON parsing error: {str(e)}",
                "clarification_questions": [],
                "suggested_rewording": None
            }
        except ValueError as e:
            return {
                "error": f"Validation error: {str(e)}",
                "clarification_questions": [],
                "suggested_rewording": None
            }
        except Exception as e:
            return {
                "error": f"Unexpected error: {str(e)}",
                "clarification_questions": [],
                "suggested_rewording": None
            }


class HybridValidator:
    """
    Implements hybrid validation: symbolic checks + LLM validation.

    Per the spec: "Hybrid Tiers: Symbolic checks for basic validity;
    full LLM validation for complex/contested entries"
    """

    def __init__(self, llm_validator: ProofOfUnderstanding):
        """
        Initialize hybrid validator.

        Args:
            llm_validator: The LLM-powered validator
        """
        self.llm_validator = llm_validator

    def symbolic_validation(
        self,
        content: str,
        intent: str,
        author: str
    ) -> Dict[str, Any]:
        """
        Perform basic symbolic/rule-based validation.

        Checks:
        - Content is not empty
        - Content meets minimum length
        - No obvious malicious patterns
        - Basic structural validity

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author

        Returns:
            Symbolic validation result
        """
        issues = []

        # Basic checks
        if not content or len(content.strip()) == 0:
            issues.append("Content is empty")

        if len(content) < 10:
            issues.append("Content is too short (minimum 10 characters)")

        if not intent or len(intent.strip()) == 0:
            issues.append("Intent is empty")

        if not author or len(author.strip()) == 0:
            issues.append("Author is empty")

        # Check for suspicious patterns
        suspicious_patterns = [
            "javascript:",
            "<script>",
            "eval(",
            "exec(",
            "__import__"
        ]

        for pattern in suspicious_patterns:
            if pattern.lower() in content.lower():
                issues.append(f"Suspicious pattern detected: {pattern}")

        return {
            "valid": len(issues) == 0,
            "issues": issues
        }

    def validate(
        self,
        content: str,
        intent: str,
        author: str,
        use_llm: bool = True,
        multi_validator: bool = False
    ) -> Dict[str, Any]:
        """
        Perform hybrid validation.

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author
            use_llm: Whether to use LLM validation
            multi_validator: Whether to use multi-validator consensus

        Returns:
            Complete validation result
        """
        # Always do symbolic validation first
        symbolic_result = self.symbolic_validation(content, intent, author)

        result = {
            "symbolic_validation": symbolic_result,
            "llm_validation": None
        }

        # If symbolic validation fails, don't proceed to LLM
        if not symbolic_result["valid"]:
            result["overall_decision"] = "INVALID"
            result["reason"] = "Failed symbolic validation"
            return result

        # LLM validation if enabled
        if use_llm:
            if multi_validator:
                llm_result = self.llm_validator.multi_validator_consensus(
                    content, intent, author
                )
                result["llm_validation"] = llm_result
                result["overall_decision"] = llm_result["consensus"]
            else:
                llm_result = self.llm_validator.validate_entry(
                    content, intent, author
                )
                result["llm_validation"] = llm_result
                if llm_result["status"] == "success":
                    result["overall_decision"] = llm_result["validation"]["decision"]
                else:
                    result["overall_decision"] = "ERROR"
        else:
            result["overall_decision"] = "VALID"

        return result

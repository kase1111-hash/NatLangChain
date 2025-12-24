"""
NatLangChain - Linguistic Validation
Implements Proof of Understanding using LLM-powered semantic validation

Integrates NCIP-004: PoU scoring dimensions (Coverage, Fidelity, Consistency, Completeness)
Integrates NCIP-007: Validator Trust Scoring & Reliability Weighting
"""

import os
from typing import Dict, List, Tuple, Any, Optional
from anthropic import Anthropic

# Import NCIP-004 PoU scoring
try:
    from pou_scoring import (
        PoUScorer,
        PoUStatus,
        PoUScoreResult,
        PoUValidationResult,
        score_pou,
        classify_pou_score,
        get_pou_config
    )
    NCIP_004_AVAILABLE = True
except ImportError:
    NCIP_004_AVAILABLE = False

# Import NCIP-007 Validator Trust Scoring
try:
    from validator_trust import (
        TrustManager,
        TrustProfile,
        ValidatorType,
        TrustScope,
        PositiveSignal,
        NegativeSignal,
        WeightedSignal,
        get_trust_manager,
        get_ncip_007_config,
        BASE_WEIGHTS,
        MAX_EFFECTIVE_WEIGHT
    )
    NCIP_007_AVAILABLE = True
except ImportError:
    NCIP_007_AVAILABLE = False


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

    Integrates NCIP-001 term registry for canonical term enforcement.
    """

    def __init__(self, llm_validator: ProofOfUnderstanding, enable_term_validation: bool = True):
        """
        Initialize hybrid validator.

        Args:
            llm_validator: The LLM-powered validator
            enable_term_validation: Whether to enable NCIP-001 term validation
        """
        self.llm_validator = llm_validator
        self.enable_term_validation = enable_term_validation
        self._term_registry = None

    @property
    def term_registry(self):
        """Lazy-load the term registry."""
        if self._term_registry is None and self.enable_term_validation:
            try:
                from term_registry import get_registry
                self._term_registry = get_registry()
            except ImportError:
                # Term registry not available
                self._term_registry = None
            except Exception:
                # Registry load failed
                self._term_registry = None
        return self._term_registry

    def validate_terms(
        self,
        content: str,
        intent: str
    ) -> Dict[str, Any]:
        """
        Validate terms against NCIP-001 Canonical Term Registry.

        Per NCIP-001:
        - Validators MAY reject unknown canonical terms
        - Validators MAY warn on deprecated or overloaded usage
        - Validators MAY flag semantic collisions

        Args:
            content: Entry content
            intent: Entry intent

        Returns:
            Term validation result with warnings and issues
        """
        result = {
            "enabled": self.enable_term_validation,
            "valid": True,
            "issues": [],
            "warnings": [],
            "terms_found": {
                "core": [],
                "protocol_bound": [],
                "extension": []
            },
            "synonym_recommendations": []
        }

        if not self.enable_term_validation or self.term_registry is None:
            result["enabled"] = False
            return result

        try:
            # Validate text against term registry
            validation = self.term_registry.validate_text(content + " " + intent)

            # Report found terms by category
            result["terms_found"]["core"] = validation.core_terms_found
            result["terms_found"]["protocol_bound"] = validation.protocol_terms_found
            result["terms_found"]["extension"] = validation.extension_terms_found

            # Deprecated terms are issues (per NCIP-001 Section 7.1)
            for deprecated in validation.deprecated_terms:
                result["issues"].append(
                    f"Deprecated term used: '{deprecated}'. "
                    "This term is no longer valid per NCIP-001."
                )

            # Synonym usage generates warnings with recommendations
            for used, canonical in validation.synonym_usage:
                result["warnings"].append(
                    f"Synonym '{used}' used instead of canonical term '{canonical}'"
                )
                result["synonym_recommendations"].append({
                    "used": used,
                    "canonical": canonical
                })

            # Set validity based on issues (not warnings)
            result["valid"] = len(result["issues"]) == 0

        except Exception as e:
            # Term validation failure should not block validation
            result["warnings"].append(f"Term validation encountered error: {str(e)}")

        return result

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
        - NCIP-001 term validation (if enabled)

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author

        Returns:
            Symbolic validation result
        """
        issues = []
        warnings = []

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

        # NCIP-001 term validation
        term_validation = self.validate_terms(content, intent)

        # Add term validation issues
        issues.extend(term_validation.get("issues", []))
        warnings.extend(term_validation.get("warnings", []))

        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": warnings,
            "term_validation": term_validation
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

        Includes NCIP-001 term validation as part of symbolic checks.

        Args:
            content: Entry content
            intent: Entry intent
            author: Entry author
            use_llm: Whether to use LLM validation
            multi_validator: Whether to use multi-validator consensus

        Returns:
            Complete validation result including:
            - symbolic_validation: Basic checks including term validation
            - llm_validation: LLM-powered semantic validation (if enabled)
            - term_validation: NCIP-001 term registry validation details
            - overall_decision: Final validation decision
        """
        # Always do symbolic validation first (includes term validation)
        symbolic_result = self.symbolic_validation(content, intent, author)

        result = {
            "symbolic_validation": symbolic_result,
            "term_validation": symbolic_result.get("term_validation"),
            "llm_validation": None
        }

        # Include term validation warnings in result
        if symbolic_result.get("warnings"):
            result["warnings"] = symbolic_result["warnings"]

        # If symbolic validation fails, don't proceed to LLM
        if not symbolic_result["valid"]:
            result["overall_decision"] = "INVALID"
            result["reason"] = "Failed symbolic validation"
            if symbolic_result.get("issues"):
                result["issues"] = symbolic_result["issues"]
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

    # =========================================================================
    # NCIP-004: Proof of Understanding Scoring
    # =========================================================================

    def validate_pou(
        self,
        pou_data: Dict[str, Any],
        contract_content: str,
        contract_clauses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate a Proof of Understanding submission per NCIP-004.

        Scores the PoU on four dimensions:
        - Coverage: All material clauses addressed
        - Fidelity: Meaning matches canonical intent
        - Consistency: No contradictions
        - Completeness: Obligations + consequences acknowledged

        Returns status based on minimum dimension score:
        - ≥0.90: Verified (accept, bind interpretation)
        - 0.75-0.89: Marginal (warn, allow resubmission)
        - 0.50-0.74: Insufficient (reject, require retry)
        - <0.50: Failed (reject, escalate)

        Args:
            pou_data: PoU submission in NCIP-004 schema format
            contract_content: The original contract content
            contract_clauses: Optional list of material clauses

        Returns:
            Dict with scores, status, actions, and fingerprint
        """
        if not NCIP_004_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-004 PoU scoring module not available",
                "ncip_004_enabled": False
            }

        try:
            scorer = PoUScorer(validator_id="hybrid_validator")
            return scorer.get_validator_response(
                pou_data,
                contract_content,
                contract_clauses
            )
        except Exception as e:
            return {
                "status": "error",
                "message": f"PoU validation failed: {str(e)}",
                "ncip_004_enabled": True
            }

    def validate_pou_with_llm(
        self,
        pou_data: Dict[str, Any],
        contract_content: str,
        contract_clauses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Validate PoU with both NCIP-004 scoring and LLM semantic analysis.

        This combines:
        1. NCIP-004 dimension scoring (Coverage, Fidelity, Consistency, Completeness)
        2. LLM-powered semantic drift detection
        3. LLM paraphrase analysis

        Args:
            pou_data: PoU submission in NCIP-004 schema format
            contract_content: The original contract content
            contract_clauses: Optional list of material clauses

        Returns:
            Combined validation result
        """
        result = {
            "ncip_004_validation": None,
            "llm_validation": None,
            "combined_status": None
        }

        # Get NCIP-004 scores
        ncip_result = self.validate_pou(pou_data, contract_content, contract_clauses)
        result["ncip_004_validation"] = ncip_result

        # Extract summary for LLM validation
        summary = pou_data.get("sections", {}).get("summary", {}).get("text", "")

        if summary and self.llm_validator:
            # Check for semantic drift between PoU summary and contract
            drift_result = self.llm_validator.detect_semantic_drift(
                contract_content,
                summary
            )
            result["llm_validation"] = {
                "drift_analysis": drift_result
            }

            # Combine results
            ncip_status = ncip_result.get("status", "error")
            drift_score = drift_result.get("drift_score")

            if ncip_status == "verified" and drift_score is not None and drift_score < 0.25:
                result["combined_status"] = "verified"
            elif ncip_status in ["verified", "marginal"] and drift_score is not None and drift_score < 0.45:
                result["combined_status"] = "marginal"
            elif ncip_status == "insufficient":
                result["combined_status"] = "insufficient"
            else:
                result["combined_status"] = "failed"
        else:
            result["combined_status"] = ncip_result.get("status", "error")

        return result

    def is_pou_required(
        self,
        drift_level: Optional[str] = None,
        has_multilingual: bool = False,
        has_economic_obligations: bool = False,
        requires_human_ratification: bool = False,
        has_mediator_escalation: bool = False
    ) -> bool:
        """
        Determine if PoU is required per NCIP-004 Section 3.

        PoU is mandatory when any of the following apply:
        - Drift level ≥ D2 (NCIP-002)
        - Multilingual alignment is used (NCIP-003)
        - Economic or legal obligations exist
        - Human ratification is required
        - Mediator escalation has occurred

        Args:
            drift_level: Current drift level (D0-D4)
            has_multilingual: Whether multilingual alignment is used
            has_economic_obligations: Whether economic/legal obligations exist
            requires_human_ratification: Whether human ratification is required
            has_mediator_escalation: Whether mediator escalation has occurred

        Returns:
            True if PoU is required
        """
        # Check drift level
        if drift_level in ["D2", "D3", "D4"]:
            return True

        # Check other conditions
        if has_multilingual:
            return True
        if has_economic_obligations:
            return True
        if requires_human_ratification:
            return True
        if has_mediator_escalation:
            return True

        return False

    def get_pou_status_from_score(self, score: float) -> str:
        """
        Get PoU status string from a score.

        Args:
            score: Score in range [0.0, 1.0]

        Returns:
            Status string: "verified", "marginal", "insufficient", or "failed"
        """
        if not NCIP_004_AVAILABLE:
            # Fallback classification
            if score >= 0.90:
                return "verified"
            elif score >= 0.75:
                return "marginal"
            elif score >= 0.50:
                return "insufficient"
            else:
                return "failed"

        status = classify_pou_score(score)
        return status.value

    # =========================================================================
    # NCIP-007: Validator Trust Scoring & Reliability Weighting
    # =========================================================================

    def register_as_trusted_validator(
        self,
        validator_id: str,
        validator_type: str = "hybrid",
        model_version: Optional[str] = None,
        declared_capabilities: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Register this validator with the trust scoring system per NCIP-007.

        Args:
            validator_id: Unique identifier for this validator
            validator_type: Type of validator (llm, hybrid, symbolic, human)
            model_version: Model version (for LLM/hybrid validators)
            declared_capabilities: List of scope names this validator claims

        Returns:
            Registration result with trust profile summary
        """
        if not NCIP_007_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-007 trust scoring module not available",
                "ncip_007_enabled": False
            }

        try:
            manager = get_trust_manager()

            # Convert type string to enum
            type_map = {
                "llm": ValidatorType.LLM,
                "hybrid": ValidatorType.HYBRID,
                "symbolic": ValidatorType.SYMBOLIC,
                "human": ValidatorType.HUMAN
            }
            vtype = type_map.get(validator_type.lower(), ValidatorType.HYBRID)

            # Convert capability strings to enums
            scope_map = {
                "semantic_parsing": TrustScope.SEMANTIC_PARSING,
                "drift_detection": TrustScope.DRIFT_DETECTION,
                "proof_of_understanding": TrustScope.PROOF_OF_UNDERSTANDING,
                "dispute_analysis": TrustScope.DISPUTE_ANALYSIS,
                "legal_translation_review": TrustScope.LEGAL_TRANSLATION_REVIEW
            }
            capabilities = []
            for cap in (declared_capabilities or []):
                if cap.lower() in scope_map:
                    capabilities.append(scope_map[cap.lower()])

            profile = manager.register_validator(
                validator_id=validator_id,
                validator_type=vtype,
                model_version=model_version,
                declared_capabilities=capabilities
            )

            return {
                "status": "registered",
                "validator_id": validator_id,
                "trust_profile": profile.to_dict(),
                "base_weight": BASE_WEIGHTS.get(vtype.value, 1.0),
                "ncip_007_enabled": True
            }

        except ValueError as e:
            return {
                "status": "error",
                "message": str(e),
                "ncip_007_enabled": True
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Registration failed: {str(e)}",
                "ncip_007_enabled": True
            }

    def get_trust_profile(self, validator_id: str) -> Dict[str, Any]:
        """
        Get the trust profile for a validator per NCIP-007.

        Args:
            validator_id: The validator to query

        Returns:
            Trust profile summary
        """
        if not NCIP_007_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-007 trust scoring module not available"
            }

        manager = get_trust_manager()
        return manager.get_trust_summary(validator_id)

    def record_validation_outcome(
        self,
        validator_id: str,
        outcome: str,
        scope: str = "semantic_parsing",
        context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Record a validation outcome to update trust scores per NCIP-007.

        Positive outcomes:
        - consensus_match: Validator matched consensus
        - pou_ratified: PoU was ratified by humans
        - correct_drift_flag: Correctly flagged semantic drift
        - dispute_performance: Performed well in dispute
        - consistency: Remained consistent across re-validations

        Negative outcomes:
        - overruled_by_lock: Overruled by Semantic Lock
        - false_positive_drift: False positive drift detection
        - unauthorized_interpretation: Introduced unauthorized interpretation
        - consensus_disagreement: Disagreed with consensus disproportionately

        Args:
            validator_id: The validator receiving the outcome
            outcome: The outcome type (see above)
            scope: The scope this applies to
            context: Additional context metadata

        Returns:
            Outcome recording result
        """
        if not NCIP_007_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-007 trust scoring module not available"
            }

        manager = get_trust_manager()

        # Map scope string to enum
        scope_map = {
            "semantic_parsing": TrustScope.SEMANTIC_PARSING,
            "drift_detection": TrustScope.DRIFT_DETECTION,
            "proof_of_understanding": TrustScope.PROOF_OF_UNDERSTANDING,
            "dispute_analysis": TrustScope.DISPUTE_ANALYSIS,
            "legal_translation_review": TrustScope.LEGAL_TRANSLATION_REVIEW
        }
        trust_scope = scope_map.get(scope.lower(), TrustScope.SEMANTIC_PARSING)

        # Map outcome to signal
        positive_map = {
            "consensus_match": PositiveSignal.CONSENSUS_MATCH,
            "pou_ratified": PositiveSignal.POU_RATIFIED,
            "correct_drift_flag": PositiveSignal.CORRECT_DRIFT_FLAG,
            "dispute_performance": PositiveSignal.DISPUTE_PERFORMANCE,
            "consistency": PositiveSignal.CONSISTENCY
        }
        negative_map = {
            "overruled_by_lock": NegativeSignal.OVERRULED_BY_LOCK,
            "false_positive_drift": NegativeSignal.FALSE_POSITIVE_DRIFT,
            "unauthorized_interpretation": NegativeSignal.UNAUTHORIZED_INTERPRETATION,
            "consensus_disagreement": NegativeSignal.CONSENSUS_DISAGREEMENT,
            "harassment_pattern": NegativeSignal.HARASSMENT_PATTERN
        }

        outcome_lower = outcome.lower()
        event = None

        if outcome_lower in positive_map:
            event = manager.record_positive_signal(
                validator_id=validator_id,
                signal=positive_map[outcome_lower],
                scope=trust_scope,
                metadata=context or {}
            )
        elif outcome_lower in negative_map:
            event = manager.record_negative_signal(
                validator_id=validator_id,
                signal=negative_map[outcome_lower],
                scope=trust_scope,
                metadata=context or {}
            )
        else:
            return {
                "status": "error",
                "message": f"Unknown outcome type: {outcome}"
            }

        if event is None:
            return {
                "status": "rejected",
                "message": "Signal rejected (validator not found or frozen)"
            }

        return {
            "status": "recorded",
            "event_id": event.event_id,
            "validator_id": validator_id,
            "outcome": outcome,
            "scope": scope,
            "new_score": manager.get_profile(validator_id).overall_score
        }

    def calculate_validator_weight(
        self,
        validator_id: str,
        scope: str = "semantic_parsing",
        scope_modifier: float = 1.0
    ) -> Dict[str, Any]:
        """
        Calculate the effective weight for a validator per NCIP-007.

        Formula: effective_weight = base_weight * trust_score * scope_modifier
        Weight is capped at MAX_EFFECTIVE_WEIGHT (anti-centralization).

        Args:
            validator_id: The validator to calculate weight for
            scope: The scope for this weight calculation
            scope_modifier: Task relevance modifier

        Returns:
            Weight calculation result
        """
        if not NCIP_007_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-007 trust scoring module not available"
            }

        manager = get_trust_manager()

        scope_map = {
            "semantic_parsing": TrustScope.SEMANTIC_PARSING,
            "drift_detection": TrustScope.DRIFT_DETECTION,
            "proof_of_understanding": TrustScope.PROOF_OF_UNDERSTANDING,
            "dispute_analysis": TrustScope.DISPUTE_ANALYSIS,
            "legal_translation_review": TrustScope.LEGAL_TRANSLATION_REVIEW
        }
        trust_scope = scope_map.get(scope.lower(), TrustScope.SEMANTIC_PARSING)

        profile = manager.get_profile(validator_id)
        identity = manager.get_identity(validator_id)

        if not profile or not identity:
            return {
                "status": "error",
                "message": f"Validator {validator_id} not found"
            }

        effective_weight = manager.calculate_effective_weight(
            validator_id, trust_scope, scope_modifier
        )

        return {
            "status": "calculated",
            "validator_id": validator_id,
            "validator_type": identity.validator_type.value,
            "base_weight": BASE_WEIGHTS.get(identity.validator_type.value, 1.0),
            "trust_score": profile.get_scoped_score(trust_scope),
            "scope_modifier": scope_modifier,
            "effective_weight": effective_weight,
            "max_weight": MAX_EFFECTIVE_WEIGHT,
            "is_capped": effective_weight == MAX_EFFECTIVE_WEIGHT
        }

    def weighted_multi_validator_consensus(
        self,
        content: str,
        intent: str,
        author: str,
        validator_ids: Optional[List[str]] = None,
        num_validators: int = 3
    ) -> Dict[str, Any]:
        """
        Achieve weighted consensus through multiple validator nodes per NCIP-007.

        This extends multi_validator_consensus with trust-weighted signals.
        Low-trust validators cannot dominate; high-trust validators cannot finalize alone.

        Args:
            content: Entry content
            intent: Stated intent
            author: Entry author
            validator_ids: Specific validators to use (optional)
            num_validators: Number of validators if not specified

        Returns:
            Weighted consensus result
        """
        if not NCIP_007_AVAILABLE:
            # Fall back to unweighted consensus
            return self.llm_validator.multi_validator_consensus(
                content, intent, author, num_validators
            )

        manager = get_trust_manager()

        # Get validation results
        base_result = self.llm_validator.multi_validator_consensus(
            content, intent, author, num_validators
        )

        if base_result.get("consensus") == "FAILED":
            return base_result

        # Create weighted signals if validators are registered
        weighted_signals = []
        for i, validation in enumerate(base_result.get("validations", [])):
            vid = validator_ids[i] if validator_ids and i < len(validator_ids) else f"validator_{i}"

            signal = manager.get_weighted_signal(
                vid,
                signal_value=validation,
                scope=TrustScope.SEMANTIC_PARSING
            )
            if signal:
                weighted_signals.append(signal)

        # Calculate weighted distribution
        if weighted_signals:
            total_weight = sum(s.effective_weight for s in weighted_signals)
            weighted_distribution = {}

            for signal in weighted_signals:
                decision = signal.signal_value.get("decision", "UNKNOWN")
                if decision not in weighted_distribution:
                    weighted_distribution[decision] = 0.0
                weighted_distribution[decision] += signal.effective_weight

            # Normalize
            if total_weight > 0:
                for k in weighted_distribution:
                    weighted_distribution[k] /= total_weight

            base_result["weighted_distribution"] = weighted_distribution
            base_result["weighted_signals"] = [
                {
                    "validator_id": s.validator_id,
                    "effective_weight": s.effective_weight,
                    "decision": s.signal_value.get("decision")
                }
                for s in weighted_signals
            ]

        return base_result

    def is_ncip_007_enabled(self) -> bool:
        """Check if NCIP-007 trust scoring is available."""
        return NCIP_007_AVAILABLE

    def get_ncip_007_status(self) -> Dict[str, Any]:
        """Get NCIP-007 implementation status and configuration."""
        if not NCIP_007_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-007 module not available"
            }

        return {
            "enabled": True,
            "config": get_ncip_007_config(),
            "registered_validators": len(get_trust_manager().profiles)
        }

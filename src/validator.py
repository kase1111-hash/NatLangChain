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

# Import NCIP-012 Cognitive Load & Human Ratification
try:
    from cognitive_load import (
        CognitiveLoadManager,
        RatificationContext,
        ActionType,
        InformationLevel,
        UIViolationType,
        SemanticUnit,
        CognitiveBudget,
        RatificationState,
        PoUConfirmation,
    )
    NCIP_012_AVAILABLE = True
except ImportError:
    NCIP_012_AVAILABLE = False


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

    # =========================================================================
    # NCIP-012: Human Ratification UX & Cognitive Load Limits
    # =========================================================================

    def get_cognitive_load_manager(self) -> Optional[Any]:
        """
        Get the cognitive load manager for NCIP-012 operations.

        Returns:
            CognitiveLoadManager instance or None if unavailable
        """
        if not NCIP_012_AVAILABLE:
            return None

        if not hasattr(self, '_cognitive_load_manager'):
            self._cognitive_load_manager = CognitiveLoadManager()
        return self._cognitive_load_manager

    def create_ratification(
        self,
        ratification_id: str,
        user_id: str,
        context: str = "simple"
    ) -> Dict[str, Any]:
        """
        Create a new ratification state per NCIP-012.

        This tracks cognitive load budget, information hierarchy,
        PoU confirmation, and UI validation for the ratification.

        Args:
            ratification_id: Unique identifier for this ratification
            user_id: The user who will ratify
            context: Context type (simple, financial, licensing, dispute, emergency)

        Returns:
            Ratification state summary
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available",
                "ncip_012_enabled": False
            }

        manager = self.get_cognitive_load_manager()

        context_map = {
            "simple": RatificationContext.SIMPLE,
            "financial": RatificationContext.FINANCIAL,
            "licensing": RatificationContext.LICENSING,
            "dispute": RatificationContext.DISPUTE,
            "emergency": RatificationContext.EMERGENCY
        }
        ctx = context_map.get(context.lower(), RatificationContext.SIMPLE)

        state = manager.create_ratification(ratification_id, user_id, ctx)

        return {
            "status": "created",
            "ratification_id": ratification_id,
            "user_id": user_id,
            "context": context,
            "cognitive_budget": {
                "max_units": state.cognitive_budget.max_units,
                "remaining": state.cognitive_budget.remaining
            },
            "ncip_012_enabled": True
        }

    def check_cognitive_load_budget(
        self,
        ratification_id: str,
        semantic_units: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Check if cognitive load budget is within limits per NCIP-012.

        Args:
            ratification_id: The ratification to check
            semantic_units: List of semantic units to add (optional)

        Returns:
            Budget compliance result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()
        state = manager.get_ratification(ratification_id)

        if not state:
            return {
                "status": "error",
                "message": f"Ratification {ratification_id} not found"
            }

        # Add any new semantic units
        if semantic_units:
            for unit_data in semantic_units:
                unit = SemanticUnit(
                    id=unit_data.get("id", ""),
                    description=unit_data.get("description", ""),
                    complexity_weight=unit_data.get("complexity_weight", 1.0),
                    category=unit_data.get("category", "general")
                )
                manager.add_semantic_unit(state.cognitive_budget, unit)

        compliant, msg = manager.check_budget_compliance(state.cognitive_budget)

        result = {
            "status": "compliant" if compliant else "exceeded",
            "message": msg,
            "max_units": state.cognitive_budget.max_units,
            "current_units": len(state.cognitive_budget.current_units),
            "remaining": state.cognitive_budget.remaining,
            "utilization": state.cognitive_budget.utilization
        }

        if state.cognitive_budget.is_exceeded:
            segments = manager.request_segmentation(state.cognitive_budget)
            result["segmentation_required"] = True
            result["suggested_segments"] = len(segments)

        return result

    def check_rate_limits(
        self,
        user_id: str,
        action_type: str = "ratification"
    ) -> Dict[str, Any]:
        """
        Check rate limits for a user per NCIP-012.

        Rate limits:
        - Ratifications: ≤5 per hour
        - Dispute escalations: ≤2 per day
        - License grants: ≤3 per day

        Args:
            user_id: The user to check
            action_type: Type of action (ratification, dispute_escalation, license_grant)

        Returns:
            Rate limit status
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()

        action_map = {
            "ratification": ActionType.RATIFICATION,
            "dispute_escalation": ActionType.DISPUTE_ESCALATION,
            "license_grant": ActionType.LICENSE_GRANT
        }
        action = action_map.get(action_type.lower(), ActionType.RATIFICATION)

        allowed, msg = manager.check_rate_limit(user_id, action)
        remaining = manager.get_remaining_actions(user_id)

        return {
            "status": "allowed" if allowed else "rate_limited",
            "message": msg,
            "action_type": action_type,
            "remaining_actions": {
                "ratifications_this_hour": remaining.get(ActionType.RATIFICATION, 0),
                "disputes_today": remaining.get(ActionType.DISPUTE_ESCALATION, 0),
                "license_grants_today": remaining.get(ActionType.LICENSE_GRANT, 0)
            }
        }

    def check_cooling_period(
        self,
        user_id: str,
        action_type: str = "agreement"
    ) -> Dict[str, Any]:
        """
        Check if a cooling period is active for a user per NCIP-012.

        Default cooling periods:
        - Agreement finalization: 12 hours
        - Settlement: 24 hours
        - License delegation: 24 hours
        - Dispute escalation: 6 hours

        Args:
            user_id: The user to check
            action_type: Type of action

        Returns:
            Cooling period status
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()

        action_map = {
            "agreement": ActionType.AGREEMENT,
            "settlement": ActionType.SETTLEMENT,
            "license_grant": ActionType.LICENSE_GRANT,
            "dispute_escalation": ActionType.DISPUTE_ESCALATION
        }
        action = action_map.get(action_type.lower(), ActionType.AGREEMENT)

        blocked, cooling = manager.check_cooling_period(user_id, action)

        result = {
            "status": "blocked" if blocked else "allowed",
            "action_type": action_type
        }

        if blocked and cooling:
            result["cooling_period"] = {
                "started_at": cooling.started_at.isoformat(),
                "ends_at": cooling.ends_at.isoformat(),
                "remaining_seconds": cooling.remaining_time.total_seconds()
            }

        return result

    def validate_information_hierarchy(
        self,
        ratification_id: str,
        levels_presented: List[str]
    ) -> Dict[str, Any]:
        """
        Validate information hierarchy compliance per NCIP-012.

        Required levels in order:
        1. Intent Summary
        2. Consequences
        3. Irreversibility Flags
        4. Risks & Unknowns
        5. Alternatives
        6. Canonical Term References
        7. Full Text (optional)

        Args:
            ratification_id: The ratification to validate
            levels_presented: List of level names presented

        Returns:
            Hierarchy validation result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()
        state = manager.get_ratification(ratification_id)

        if not state:
            return {
                "status": "error",
                "message": f"Ratification {ratification_id} not found"
            }

        level_map = {
            "intent_summary": InformationLevel.INTENT_SUMMARY,
            "consequences": InformationLevel.CONSEQUENCES,
            "irreversibility_flags": InformationLevel.IRREVERSIBILITY_FLAGS,
            "risks_unknowns": InformationLevel.RISKS_UNKNOWNS,
            "alternatives": InformationLevel.ALTERNATIVES,
            "canonical_references": InformationLevel.CANONICAL_REFERENCES,
            "full_text": InformationLevel.FULL_TEXT
        }

        errors = []
        for level_name in levels_presented:
            level = level_map.get(level_name.lower())
            if level:
                success, msg = manager.present_information_level(
                    state.information, level
                )
                if not success:
                    errors.append(msg)

        complete, missing = manager.validate_hierarchy_complete(state.information)

        return {
            "status": "complete" if complete else "incomplete",
            "errors": errors,
            "missing_levels": [l.name.lower() for l in missing],
            "presentation_order": [l.name.lower() for l in state.information.presentation_order]
        }

    def validate_pou_gate(
        self,
        ratification_id: str,
        paraphrase_viewed: bool = False,
        user_confirmed: bool = False,
        user_correction: Optional[str] = None,
        correction_drift: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Validate Proof of Understanding gate per NCIP-012.

        Before ratification, the user MUST:
        - View a PoU paraphrase
        - Confirm or correct it

        If correction drift exceeds 0.20:
        - Ratification blocked
        - Semantic clarification required

        Args:
            ratification_id: The ratification to validate
            paraphrase_viewed: Whether user viewed the paraphrase
            user_confirmed: Whether user confirmed
            user_correction: User's correction text (if any)
            correction_drift: Drift score of correction

        Returns:
            PoU gate validation result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()
        state = manager.get_ratification(ratification_id)

        if not state:
            return {
                "status": "error",
                "message": f"Ratification {ratification_id} not found"
            }

        if paraphrase_viewed:
            manager.view_pou_paraphrase(state.pou_confirmation)

        if user_confirmed:
            success, msg = manager.confirm_pou(
                state.pou_confirmation,
                user_correction,
                correction_drift
            )

            return {
                "status": "valid" if success else "invalid",
                "message": msg,
                "requires_clarification": state.pou_confirmation.requires_clarification,
                "max_allowed_drift": state.pou_confirmation.max_allowed_drift,
                "correction_drift": correction_drift
            }

        return {
            "status": "pending",
            "paraphrase_viewed": state.pou_confirmation.paraphrase_viewed,
            "user_confirmed": state.pou_confirmation.user_confirmed
        }

    def validate_ui_compliance(
        self,
        ratification_id: str,
        ui_elements: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Validate UI compliance with NCIP-012 safeguards.

        Mandatory UI constraints:
        - No dark patterns
        - No default "accept"
        - No countdown pressure (unless emergency-flagged)
        - No bundling of unrelated decisions

        Args:
            ratification_id: The ratification to validate
            ui_elements: List of UI element descriptions

        Returns:
            UI compliance result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()
        state = manager.get_ratification(ratification_id)

        if not state:
            return {
                "status": "error",
                "message": f"Ratification {ratification_id} not found"
            }

        all_violations = []
        for element in ui_elements:
            element_type = element.get("type", "unknown")
            properties = element.get("properties", {})

            compliant, violations = manager.validate_ui_element(
                state.ui_validation,
                element_type,
                properties
            )
            all_violations.extend(violations)

        return {
            "status": "compliant" if state.ui_validation.is_compliant else "non_compliant",
            "violations": [v.value for v in state.ui_validation.violations],
            "violation_details": all_violations,
            "violation_count": state.ui_validation.violation_count
        }

    def attempt_ratification(
        self,
        ratification_id: str,
        action_type: str = "ratification"
    ) -> Dict[str, Any]:
        """
        Attempt to complete a ratification per NCIP-012.

        Checks all requirements:
        - Cognitive load budget not exceeded
        - Information hierarchy complete
        - PoU confirmation valid
        - UI compliant
        - Rate limits not exceeded
        - Cooling period not active

        Args:
            ratification_id: The ratification to complete
            action_type: Type of action for rate limiting

        Returns:
            Ratification attempt result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()

        action_map = {
            "ratification": ActionType.RATIFICATION,
            "dispute_escalation": ActionType.DISPUTE_ESCALATION,
            "license_grant": ActionType.LICENSE_GRANT,
            "agreement": ActionType.AGREEMENT,
            "settlement": ActionType.SETTLEMENT
        }
        action = action_map.get(action_type.lower(), ActionType.RATIFICATION)

        success, blockers = manager.attempt_ratification(ratification_id, action)

        state = manager.get_ratification(ratification_id)

        result = {
            "status": "ratified" if success else "blocked",
            "blockers": blockers
        }

        if success and state:
            result["ratified_at"] = state.ratified_at.isoformat() if state.ratified_at else None
            result["semantic_lock_active"] = state.semantic_lock_active

        return result

    def validator_measure_cognitive_load(
        self,
        content: str,
        context: str = "simple"
    ) -> Dict[str, Any]:
        """
        Validator function to measure cognitive load per NCIP-012.

        Measures semantic units in content and checks against limits.

        Args:
            content: The content to measure
            context: Context type for budget limits

        Returns:
            Cognitive load measurement
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()

        context_map = {
            "simple": RatificationContext.SIMPLE,
            "financial": RatificationContext.FINANCIAL,
            "licensing": RatificationContext.LICENSING,
            "dispute": RatificationContext.DISPUTE,
            "emergency": RatificationContext.EMERGENCY
        }
        ctx = context_map.get(context.lower(), RatificationContext.SIMPLE)

        count, units = manager.validator_measure_semantic_units(content, ctx)
        budget = manager.create_cognitive_budget(ctx)

        for unit in units:
            budget.current_units.append(unit)

        return {
            "status": "measured",
            "semantic_unit_count": count,
            "max_units": budget.max_units,
            "is_exceeded": budget.is_exceeded,
            "utilization": budget.utilization,
            "units": [
                {
                    "id": u.id,
                    "description": u.description,
                    "complexity_weight": u.complexity_weight
                }
                for u in units
            ]
        }

    def validator_detect_ux_violations(
        self,
        ui_snapshot: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Validator function to detect UX violations per NCIP-012.

        Detects:
        - Default accept buttons
        - Countdown pressure (non-emergency)
        - Bundled unrelated decisions
        - Dark patterns
        - Missing lock visibility
        - Skipped hierarchy levels

        Args:
            ui_snapshot: UI state snapshot

        Returns:
            UX violation detection result
        """
        if not NCIP_012_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-012 cognitive load module not available"
            }

        manager = self.get_cognitive_load_manager()
        violations = manager.validator_detect_ux_violations(ui_snapshot)

        return {
            "status": "compliant" if not violations else "violations_detected",
            "violations": [v.value for v in violations],
            "violation_count": len(violations),
            "is_slashable": len(violations) > 2  # Per NCIP-010
        }

    def is_ncip_012_enabled(self) -> bool:
        """Check if NCIP-012 cognitive load management is available."""
        return NCIP_012_AVAILABLE

    def get_ncip_012_status(self) -> Dict[str, Any]:
        """Get NCIP-012 implementation status and configuration."""
        if not NCIP_012_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-012 module not available"
            }

        manager = self.get_cognitive_load_manager()

        return {
            "enabled": True,
            "cognitive_load_limits": {
                "simple": 7,
                "financial": 9,
                "licensing": 9,
                "dispute": 5,
                "emergency": 3
            },
            "rate_limits": {
                "ratifications_per_hour": 5,
                "disputes_per_day": 2,
                "license_grants_per_day": 3
            },
            "cooling_periods": {
                "agreement": "12h",
                "settlement": "24h",
                "licensing": "24h",
                "dispute": "6h"
            },
            "pou_max_drift": 0.20,
            "active_ratifications": len(manager.ratification_states)
        }

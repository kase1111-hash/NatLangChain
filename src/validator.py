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

# Import NCIP-014 Protocol Amendments & Constitutional Change
try:
    from protocol_amendments import (
        AmendmentManager,
        AmendmentClass,
        AmendmentStatus,
        RatificationStage,
        ConstitutionalArtifact,
        Amendment,
        EmergencyAmendment,
        PoUStatement,
        SemanticCompatibilityResult,
    )
    NCIP_014_AVAILABLE = True
except ImportError:
    NCIP_014_AVAILABLE = False

# Import NCIP-003 Multilingual Semantic Alignment & Drift
try:
    from multilingual import (
        MultilingualAlignmentManager,
        MultilingualContract,
        LanguageEntry,
        LanguageRole,
        DriftLevel,
        ValidatorAction,
        TranslationViolation,
        CanonicalTermMapping,
        ClauseDriftResult,
        MultilingualRatification,
        AlignmentRules,
        SUPPORTED_LANGUAGE_CODES,
    )
    NCIP_003_AVAILABLE = True
except ImportError:
    NCIP_003_AVAILABLE = False

# Import NCIP-006 Jurisdictional Interpretation & Legal Bridging
try:
    from jurisdictional import (
        JurisdictionalManager,
        JurisdictionalBridge,
        JurisdictionDeclaration,
        JurisdictionRole,
        LegalTranslationArtifact,
        LTAViolation,
        CourtRuling,
        CourtRulingType,
        JurisdictionConflict,
        DriftLevel as JurisdictionalDriftLevel,
        VALID_COUNTRY_CODES,
        US_STATE_CODES,
        validate_jurisdiction_code,
    )
    NCIP_006_AVAILABLE = True
except ImportError:
    NCIP_006_AVAILABLE = False


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

    # =========================================================================
    # NCIP-014: Protocol Amendments & Constitutional Change
    # =========================================================================

    def get_amendment_manager(self) -> Optional[Any]:
        """
        Get the amendment manager for NCIP-014 operations.

        Returns:
            AmendmentManager instance or None if unavailable
        """
        if not NCIP_014_AVAILABLE:
            return None

        if not hasattr(self, '_amendment_manager'):
            self._amendment_manager = AmendmentManager()
        return self._amendment_manager

    def create_amendment_proposal(
        self,
        amendment_class: str,
        title: str,
        rationale: str,
        scope_of_impact: str,
        affected_artifacts: List[str],
        proposed_changes: str,
        migration_guidance: Optional[str] = None,
        effective_date: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new amendment proposal per NCIP-014.

        Amendment classes:
        - A: Editorial/Clarificatory - Simple majority (>50%)
        - B: Procedural - Supermajority (>67%)
        - C: Semantic - Constitutional quorum (>75%)
        - D: Structural - Near-unanimous (>90%)
        - E: Existential - Fork-only (100%)

        Args:
            amendment_class: Class of amendment (A-E)
            title: Amendment title
            rationale: Explanation of why the change is needed
            scope_of_impact: Description of what is affected
            affected_artifacts: List of constitutional artifacts affected
            proposed_changes: Detailed description of changes
            migration_guidance: Required for class D/E
            effective_date: When amendment takes effect (ISO format)

        Returns:
            Amendment creation result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 protocol amendments module not available",
                "ncip_014_enabled": False
            }

        manager = self.get_amendment_manager()

        # Map class string to enum
        class_map = {
            "A": AmendmentClass.A,
            "B": AmendmentClass.B,
            "C": AmendmentClass.C,
            "D": AmendmentClass.D,
            "E": AmendmentClass.E
        }
        aclass = class_map.get(amendment_class.upper())
        if not aclass:
            return {
                "status": "error",
                "message": f"Invalid amendment class: {amendment_class}"
            }

        # Map artifact strings to enums
        artifact_map = {
            "genesis_block": ConstitutionalArtifact.GENESIS_BLOCK,
            "core_doctrines": ConstitutionalArtifact.CORE_DOCTRINES,
            "mp_01": ConstitutionalArtifact.MP_01,
            "mp_02": ConstitutionalArtifact.MP_02,
            "mp_03": ConstitutionalArtifact.MP_03,
            "mp_04": ConstitutionalArtifact.MP_04,
            "mp_05": ConstitutionalArtifact.MP_05,
            "canonical_term_registry": ConstitutionalArtifact.CANONICAL_TERM_REGISTRY,
        }
        # Add NCIP artifacts
        for i in range(1, 16):
            artifact_map[f"ncip_{i:03d}"] = getattr(ConstitutionalArtifact, f"NCIP_{i:03d}", None)
            artifact_map[f"ncip_{i}"] = getattr(ConstitutionalArtifact, f"NCIP_{i:03d}", None)

        artifacts = []
        for art_str in affected_artifacts:
            artifact = artifact_map.get(art_str.lower())
            if artifact:
                artifacts.append(artifact)

        if not artifacts:
            return {
                "status": "error",
                "message": "No valid artifacts specified"
            }

        # Parse effective date
        eff_date = None
        if effective_date:
            from datetime import datetime
            try:
                eff_date = datetime.fromisoformat(effective_date.replace("Z", "+00:00"))
            except ValueError:
                return {
                    "status": "error",
                    "message": f"Invalid effective_date format: {effective_date}"
                }

        # Generate amendment ID
        amendment_id = manager.generate_amendment_id(aclass)

        amendment, errors = manager.create_amendment(
            amendment_id=amendment_id,
            amendment_class=aclass,
            title=title,
            rationale=rationale,
            scope_of_impact=scope_of_impact,
            affected_artifacts=artifacts,
            proposed_changes=proposed_changes,
            migration_guidance=migration_guidance,
            effective_date=eff_date
        )

        if errors:
            return {
                "status": "error",
                "errors": errors
            }

        return {
            "status": "created",
            "amendment_id": amendment_id,
            "class": amendment_class,
            "title": title,
            "threshold": f"{manager.THRESHOLDS[aclass]:.0%}",
            "fork_required": amendment.fork_required,
            "ncip_014_enabled": True
        }

    def propose_amendment(self, amendment_id: str) -> Dict[str, Any]:
        """
        Move an amendment to proposed status and start cooling period.
        Per NCIP-014 Section 7.1, minimum cooling period is 14 days.

        Args:
            amendment_id: The amendment to propose

        Returns:
            Proposal result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        success, msg = manager.propose_amendment(amendment_id)

        amendment = manager.get_amendment(amendment_id)

        result = {
            "status": "proposed" if success else "error",
            "message": msg
        }

        if success and amendment:
            result["cooling_ends_at"] = amendment.cooling_ends_at.isoformat()
            result["current_stage"] = amendment.current_stage.name

        return result

    def cast_amendment_vote(
        self,
        amendment_id: str,
        voter_id: str,
        vote: str,
        what_changes: str,
        what_unchanged: str,
        who_affected: str,
        rationale: str,
        validator_trust_score: Optional[float] = None,
        mediator_reputation: Optional[float] = None
    ) -> Dict[str, Any]:
        """
        Cast a vote on an amendment per NCIP-014.

        Requires a Proof of Understanding statement per Section 6.1:
        - What changes
        - What does not change
        - Who is affected
        - Why voter agrees or disagrees

        Args:
            amendment_id: The amendment to vote on
            voter_id: Voter identifier
            vote: "approve", "reject", or "abstain"
            what_changes: PoU - what changes
            what_unchanged: PoU - what stays the same
            who_affected: PoU - who is affected
            rationale: PoU - why voter agrees/disagrees
            validator_trust_score: Optional trust score weight
            mediator_reputation: Optional reputation weight

        Returns:
            Vote result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()

        pou = PoUStatement(
            voter_id=voter_id,
            what_changes=what_changes,
            what_unchanged=what_unchanged,
            who_affected=who_affected,
            rationale=rationale
        )

        success, msg = manager.cast_vote(
            amendment_id=amendment_id,
            voter_id=voter_id,
            vote=vote,
            pou=pou,
            validator_trust_score=validator_trust_score,
            mediator_reputation=mediator_reputation
        )

        return {
            "status": "recorded" if success else "error",
            "message": msg,
            "vote": vote,
            "pou_hash": pou.compute_hash() if success else None
        }

    def get_amendment_tally(self, amendment_id: str) -> Dict[str, Any]:
        """
        Get current vote tally for an amendment.

        Args:
            amendment_id: The amendment to tally

        Returns:
            Vote tally with threshold comparison
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        return manager.tally_votes(amendment_id)

    def finalize_amendment_ratification(self, amendment_id: str) -> Dict[str, Any]:
        """
        Finalize ratification of an amendment.

        For Class E amendments, if consensus fails, creates a constitutional fork.

        Args:
            amendment_id: The amendment to finalize

        Returns:
            Ratification result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        success, msg = manager.finalize_ratification(amendment_id)

        amendment = manager.get_amendment(amendment_id)

        result = {
            "status": "ratified" if success else "rejected" if "rejected" in msg.lower() else "forked",
            "message": msg
        }

        if amendment:
            result["amendment_status"] = amendment.status.value
            if amendment.ratified_at:
                result["ratified_at"] = amendment.ratified_at.isoformat()
            if amendment.semantic_lock_at:
                result["semantic_lock_at"] = amendment.semantic_lock_at.isoformat()

        return result

    def activate_amendment(self, amendment_id: str) -> Dict[str, Any]:
        """
        Activate a ratified amendment.

        Per NCIP-014 Section 10, activation only occurs at or after effective_date.
        Updates constitution version.

        Args:
            amendment_id: The amendment to activate

        Returns:
            Activation result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        success, msg = manager.activate_amendment(amendment_id)

        result = {
            "status": "activated" if success else "error",
            "message": msg
        }

        if success:
            result["constitution_version"] = manager.get_constitution_version()

        return result

    def check_semantic_compatibility(
        self,
        amendment_id: str,
        drift_scores: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Check semantic compatibility of an amendment per NCIP-014 Section 9.

        Amendments with ≥D3 drift without migration path are invalid.

        Args:
            amendment_id: The amendment to check
            drift_scores: Drift scores by affected NCIP

        Returns:
            Compatibility result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        result = manager.check_semantic_compatibility(amendment_id, drift_scores)

        return {
            "status": "compatible" if result.is_compatible else "incompatible",
            "max_drift": result.max_drift,
            "requires_migration": result.requires_migration,
            "affected_ncips": result.affected_ncips,
            "violations": result.violations
        }

    def create_emergency_amendment(
        self,
        reason: str,
        proposed_changes: str,
        max_duration_days: int = 7
    ) -> Dict[str, Any]:
        """
        Create an emergency amendment per NCIP-014 Section 12.

        Emergency amendments:
        - Limited to procedural safety
        - Time-bounded (auto-expire if not ratified)
        - MUST NOT alter semantics

        Valid reasons: validator_halt, exploit_mitigation, network_safety_pause

        Args:
            reason: Emergency reason
            proposed_changes: What changes are proposed
            max_duration_days: Maximum duration before expiry

        Returns:
            Emergency amendment creation result
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()

        from datetime import datetime
        amendment_id = f"NCIP-014-EMERGENCY-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        emergency, errors = manager.create_emergency_amendment(
            amendment_id=amendment_id,
            reason=reason,
            proposed_changes=proposed_changes,
            max_duration_days=max_duration_days
        )

        if errors:
            return {
                "status": "error",
                "errors": errors
            }

        return {
            "status": "created",
            "amendment_id": emergency.amendment_id,
            "reason": reason,
            "expires_at": emergency.expires_at.isoformat(),
            "requires_ratification": True
        }

    def get_constitution_version(self) -> Dict[str, Any]:
        """
        Get current constitution version per NCIP-014 Section 10.

        Returns:
            Constitution version info
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()

        return {
            "status": "ok",
            "version": manager.get_constitution_version(),
            "history_count": len(manager.constitution_history)
        }

    def get_amendment_status_summary(self) -> Dict[str, Any]:
        """
        Get summary of amendment system status.

        Returns:
            Status summary including counts by status and class
        """
        if not NCIP_014_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()
        return manager.get_status_summary()

    def is_ncip_014_enabled(self) -> bool:
        """Check if NCIP-014 protocol amendments is available."""
        return NCIP_014_AVAILABLE

    def get_ncip_014_status(self) -> Dict[str, Any]:
        """Get NCIP-014 implementation status and configuration."""
        if not NCIP_014_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-014 module not available"
            }

        manager = self.get_amendment_manager()

        return {
            "enabled": True,
            "constitution_version": manager.get_constitution_version(),
            "amendment_classes": {
                "A": {"name": "Editorial", "threshold": "50%"},
                "B": {"name": "Procedural", "threshold": "67%"},
                "C": {"name": "Semantic", "threshold": "75%"},
                "D": {"name": "Structural", "threshold": "90%"},
                "E": {"name": "Existential", "threshold": "100% (fork-only)"}
            },
            "min_cooling_period_days": 14,
            "total_amendments": len(manager.amendments),
            "active_emergencies": len([e for e in manager.emergency_amendments.values() if e.is_active]),
            "forks": len(manager.get_forks())
        }

    # =========================================================================
    # NCIP-003: Multilingual Semantic Alignment & Drift
    # =========================================================================

    def get_multilingual_manager(self) -> Optional[Any]:
        """
        Get the multilingual alignment manager for NCIP-003 operations.

        Returns:
            MultilingualAlignmentManager instance or None if unavailable
        """
        if not NCIP_003_AVAILABLE:
            return None

        if not hasattr(self, '_multilingual_manager'):
            self._multilingual_manager = MultilingualAlignmentManager()
        return self._multilingual_manager

    def create_multilingual_contract(
        self,
        contract_id: str,
        canonical_anchor_language: str = "en"
    ) -> Dict[str, Any]:
        """
        Create a new multilingual contract with CSAL declaration.

        Per NCIP-003 Section 2, every multilingual contract MUST declare
        a Canonical Semantic Anchor Language. Default is English (en).

        Args:
            contract_id: Unique identifier for the contract
            canonical_anchor_language: ISO 639-1 code for CSAL

        Returns:
            Contract creation result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 multilingual module not available",
                "ncip_003_enabled": False
            }

        manager = self.get_multilingual_manager()
        contract = manager.create_contract(contract_id, canonical_anchor_language)

        return {
            "status": "created",
            "contract_id": contract_id,
            "csal": canonical_anchor_language,
            "csal_explicit": contract.is_csal_declared(),
            "ncip_003_enabled": True
        }

    def add_contract_language(
        self,
        contract_id: str,
        language_code: str,
        role: str,
        content: str,
        drift_tolerance: float = 0.25
    ) -> Dict[str, Any]:
        """
        Add a language entry to a multilingual contract.

        Per NCIP-003 Section 3, each language MUST declare one role:
        - anchor: Canonical meaning source
        - aligned: Verified semantic equivalent
        - informational: Human convenience only (non-executable)

        Args:
            contract_id: Contract to add language to
            language_code: ISO 639-1 language code
            role: Language role (anchor, aligned, informational)
            content: Content in this language
            drift_tolerance: Maximum acceptable drift (default 0.25 per D2)

        Returns:
            Language addition result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        role_map = {
            "anchor": LanguageRole.ANCHOR,
            "aligned": LanguageRole.ALIGNED,
            "informational": LanguageRole.INFORMATIONAL
        }
        lang_role = role_map.get(role.lower())
        if not lang_role:
            return {
                "status": "error",
                "message": f"Invalid role: {role}. Must be anchor, aligned, or informational"
            }

        success, msg = contract.add_language(language_code, lang_role, content, drift_tolerance)

        return {
            "status": "added" if success else "error",
            "message": msg,
            "language_code": language_code,
            "role": role,
            "is_executable": lang_role in [LanguageRole.ANCHOR, LanguageRole.ALIGNED]
        }

    def validate_multilingual_contract(
        self,
        contract_id: str
    ) -> Dict[str, Any]:
        """
        Validate alignment of all languages in a multilingual contract.

        Per NCIP-003 Section 5.2:
        - Drift is computed per clause and per term
        - Maximum drift score governs validator response
        - Drift in any aligned language applies to whole contract

        Args:
            contract_id: Contract to validate

        Returns:
            Validation report with drift scores and actions
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        valid, report = manager.validate_contract_alignment(contract)
        return report

    def measure_cross_language_drift(
        self,
        anchor_text: str,
        aligned_text: str,
        language_code: str
    ) -> Dict[str, Any]:
        """
        Measure semantic drift between anchor and aligned text.

        Per NCIP-003 Section 5.1:
        drift(Lᵢ) = semantic_distance(anchor, Lᵢ)

        Args:
            anchor_text: Text in anchor language
            aligned_text: Text in aligned language
            language_code: ISO 639-1 code of aligned language

        Returns:
            Drift measurement result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        drift_score, drift_level = manager.measure_cross_language_drift(
            anchor_text, aligned_text, language_code
        )
        action = manager.get_validator_action(drift_level)

        return {
            "status": "measured",
            "drift_score": drift_score,
            "drift_level": drift_level.value,
            "validator_action": action.value,
            "within_d2_threshold": drift_score <= 0.45
        }

    def check_translation_violations(
        self,
        anchor_text: str,
        aligned_text: str,
        language_code: str
    ) -> Dict[str, Any]:
        """
        Check for prohibited behaviors in aligned translation.

        Per NCIP-003 Section 4.2, an aligned translation MUST NOT:
        - Introduce new constraints
        - Remove obligations
        - Narrow or broaden scope
        - Replace canonical terms with non-registry concepts

        Args:
            anchor_text: Text in anchor language
            aligned_text: Text in aligned language
            language_code: ISO 639-1 code

        Returns:
            Violation check result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        violations = manager.check_translation_violations(
            anchor_text, aligned_text, language_code
        )

        return {
            "status": "checked",
            "has_violations": len(violations) > 0,
            "violations": [v.value for v in violations],
            "violation_count": len(violations)
        }

    def create_multilingual_ratification(
        self,
        contract_id: str,
        ratifier_id: str,
        reviewed_languages: List[str]
    ) -> Dict[str, Any]:
        """
        Create multilingual ratification per NCIP-003 Section 8.

        Human ratification MUST:
        - Reference the CSAL explicitly
        - Acknowledge reviewed aligned languages
        - Bind all translations to the anchor meaning

        Args:
            contract_id: Contract to ratify
            ratifier_id: ID of person ratifying
            reviewed_languages: List of language codes reviewed

        Returns:
            Ratification creation result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        ratification = manager.create_multilingual_ratification(
            contract, ratifier_id, reviewed_languages
        )

        return {
            "status": "created",
            "ratification_id": ratification.ratification_id,
            "anchor_language": ratification.anchor_language,
            "reviewed_languages": ratification.reviewed_languages,
            "statement": ratification.statement
        }

    def confirm_multilingual_ratification(
        self,
        contract_id: str,
        ratification_id: str
    ) -> Dict[str, Any]:
        """
        Confirm multilingual ratification binding.

        User acknowledges that translations are bound to anchor meaning.

        Args:
            contract_id: Contract ID
            ratification_id: Ratification to confirm

        Returns:
            Confirmation result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        # Find the ratification
        ratification = None
        for r in contract.ratifications:
            if r.ratification_id == ratification_id:
                ratification = r
                break

        if not ratification:
            return {
                "status": "error",
                "message": f"Ratification {ratification_id} not found"
            }

        success, statement = manager.confirm_ratification(ratification)

        return {
            "status": "confirmed" if success else "error",
            "message": statement if success else "Confirmation failed",
            "binding_acknowledged": ratification.binding_acknowledged
        }

    def get_validator_drift_report(
        self,
        contract_id: str,
        language_code: str
    ) -> Dict[str, Any]:
        """
        Generate validator report for drift per NCIP-003 Section 6.

        Validators MUST report:
        - Language pair
        - Affected clauses
        - Drift score
        - Canonical terms involved

        Args:
            contract_id: Contract to report on
            language_code: Language to report drift for

        Returns:
            Validator drift report
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        return manager.validator_report_drift(contract_id, language_code)

    def generate_alignment_spec(
        self,
        contract_id: str
    ) -> Dict[str, Any]:
        """
        Generate machine-readable multilingual alignment spec.

        Per NCIP-003 Section 10, validators MUST support this structure.

        Args:
            contract_id: Contract to generate spec for

        Returns:
            YAML-compatible alignment specification
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        return manager.generate_alignment_spec(contract)

    def validate_term_mapping(
        self,
        contract_id: str,
        term_id: str,
        anchor_term: str,
        translated_term: str,
        language_code: str
    ) -> Dict[str, Any]:
        """
        Validate canonical term mapping across languages.

        Per NCIP-003 Section 7.1:
        - Terms MUST remain semantically identical across languages
        - MAY be translated lexically
        - MUST map to the same registry ID

        Args:
            contract_id: Contract containing the term
            term_id: Registry ID from NCIP-001
            anchor_term: Term in anchor language
            translated_term: Term in target language
            language_code: Target language code

        Returns:
            Term mapping validation result
        """
        if not NCIP_003_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        contract = manager.get_contract(contract_id)

        if not contract:
            return {
                "status": "error",
                "message": f"Contract {contract_id} not found"
            }

        success, msg = manager.validate_term_mapping(
            contract, term_id, anchor_term, translated_term, language_code
        )

        return {
            "status": "valid" if success else "error",
            "message": msg,
            "term_id": term_id,
            "anchor_term": anchor_term,
            "translated_term": translated_term,
            "language_code": language_code
        }

    def is_ncip_003_enabled(self) -> bool:
        """Check if NCIP-003 multilingual alignment is available."""
        return NCIP_003_AVAILABLE

    def get_ncip_003_status(self) -> Dict[str, Any]:
        """Get NCIP-003 implementation status and configuration."""
        if not NCIP_003_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-003 module not available"
            }

        manager = self.get_multilingual_manager()
        summary = manager.get_status_summary()

        return {
            "enabled": True,
            "default_csal": "en",
            "supported_languages": len(SUPPORTED_LANGUAGE_CODES),
            "language_roles": ["anchor", "aligned", "informational"],
            "drift_thresholds": summary["drift_thresholds"],
            "total_contracts": summary["total_contracts"],
            "validator_actions": {
                "D0-D1": "accept",
                "D2": "pause_clarify",
                "D3": "require_ratification",
                "D4": "reject_escalate"
            }
        }

    # -------------------------------------------------------------------------
    # NCIP-006: Jurisdictional Interpretation & Legal Bridging Integration
    # -------------------------------------------------------------------------

    _jurisdictional_manager: Optional["JurisdictionalManager"] = None

    def get_jurisdictional_manager(self) -> Optional["JurisdictionalManager"]:
        """Get or create the jurisdictional manager instance."""
        if not NCIP_006_AVAILABLE:
            return None
        if self._jurisdictional_manager is None:
            self._jurisdictional_manager = JurisdictionalManager()
        return self._jurisdictional_manager

    def create_jurisdictional_bridge(
        self,
        prose_contract_id: str
    ) -> Dict[str, Any]:
        """
        Create a jurisdictional bridge for a Prose Contract.

        Per NCIP-006: Any Prose Contract with legal or economic impact
        MUST declare governing jurisdictions.
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        bridge = manager.create_bridge(prose_contract_id)

        return {
            "status": "created",
            "prose_contract_id": prose_contract_id,
            "semantic_authority": bridge.semantic_authority_source,
            "allow_external_override": bridge.allow_external_semantic_override,
            "ltas_authoritative": bridge.ltas_authoritative
        }

    def add_jurisdiction(
        self,
        prose_contract_id: str,
        code: str,
        role: str
    ) -> Dict[str, Any]:
        """
        Add a jurisdiction declaration to a bridge.

        Args:
            prose_contract_id: ID of the Prose Contract
            code: ISO 3166-1 jurisdiction code (e.g., "US", "US-CA")
            role: Jurisdiction role ("enforcement", "interpretive", "procedural")
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        bridge = manager.get_bridge(prose_contract_id)

        if not bridge:
            return {
                "status": "error",
                "message": f"No bridge found for {prose_contract_id}"
            }

        try:
            jurisdiction_role = JurisdictionRole(role)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid role: {role}. Use: enforcement, interpretive, procedural"
            }

        success, msg = bridge.add_jurisdiction(code, jurisdiction_role)

        return {
            "status": "added" if success else "error",
            "message": msg,
            "code": code,
            "role": role
        }

    def validate_jurisdiction_declaration(
        self,
        prose_contract_id: str
    ) -> Dict[str, Any]:
        """
        Validate jurisdiction declaration for a Prose Contract.

        Per NCIP-006 Section 3.1: If omitted, validators emit D2
        and execution pauses until declared.
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        result = manager.validator_check_jurisdiction(prose_contract_id)

        return result

    def create_legal_translation_artifact(
        self,
        prose_contract_id: str,
        target_jurisdiction: str,
        legal_prose: str,
        registry_version: str,
        temporal_fixity_timestamp: str,
        referenced_terms: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a Legal Translation Artifact (LTA).

        Per NCIP-006 Section 6: LTAs are jurisdiction-specific renderings
        of Prose Contracts. They are derived and non-authoritative.
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()

        from datetime import datetime
        try:
            t0 = datetime.fromisoformat(temporal_fixity_timestamp)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid timestamp format: {temporal_fixity_timestamp}"
            }

        lta, errors = manager.create_lta(
            prose_contract_id=prose_contract_id,
            target_jurisdiction=target_jurisdiction,
            legal_prose=legal_prose,
            registry_version=registry_version,
            temporal_fixity_timestamp=t0,
            referenced_terms=referenced_terms
        )

        if errors:
            return {
                "status": "error",
                "errors": errors
            }

        return {
            "status": "created",
            "lta_id": lta.lta_id,
            "prose_contract_id": lta.prose_contract_id,
            "target_jurisdiction": lta.target_jurisdiction,
            "has_required_references": lta.has_required_references,
            "disclaimer_present": bool(lta.semantic_authority_disclaimer)
        }

    def validate_legal_translation_artifact(
        self,
        lta_id: str,
        prose_contract_id: str,
        original_prose: str
    ) -> Dict[str, Any]:
        """
        Validate a Legal Translation Artifact against its source.

        Per NCIP-006 Section 7: Validators MUST reject LTAs that:
        - Introduce new obligations
        - Narrow or broaden scope
        - Have drift >= D3
        - Claim semantic authority
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        bridge = manager.get_bridge(prose_contract_id)

        if not bridge:
            return {
                "status": "error",
                "message": f"No bridge found for {prose_contract_id}"
            }

        lta = bridge.ltas.get(lta_id)
        if not lta:
            return {
                "status": "error",
                "message": f"LTA {lta_id} not found"
            }

        result = manager.validator_check_lta(lta, original_prose)

        return result

    def handle_court_ruling(
        self,
        prose_contract_id: str,
        jurisdiction: str,
        ruling_type: str,
        summary: str,
        enforcement_outcome: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Handle a court ruling per NCIP-006 Section 8.

        Per NCIP-006: Law constrains enforcement, not meaning.
        - Semantic Lock remains intact
        - Meaning does not change
        - Only enforcement outcome is applied
        - Semantic override rulings are automatically rejected
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()

        try:
            ruling_type_enum = CourtRulingType(ruling_type)
        except ValueError:
            return {
                "status": "error",
                "message": f"Invalid ruling type: {ruling_type}"
            }

        ruling = manager.handle_court_ruling(
            prose_contract_id=prose_contract_id,
            jurisdiction=jurisdiction,
            ruling_type=ruling_type_enum,
            summary=summary,
            enforcement_outcome=enforcement_outcome
        )

        return {
            "status": "handled",
            "ruling_id": ruling.ruling_id,
            "ruling_type": ruling.ruling_type.value,
            "semantic_lock_preserved": ruling.semantic_lock_preserved,
            "rejected": ruling.rejected,
            "rejection_reason": ruling.rejection_reason,
            "execution_halted": ruling.execution_halted,
            "enforcement_outcome": ruling.enforcement_outcome
        }

    def handle_jurisdiction_conflict(
        self,
        prose_contract_id: str,
        jurisdictions: List[str],
        conflict_type: str,
        description: str
    ) -> Dict[str, Any]:
        """
        Handle cross-jurisdiction conflict per NCIP-006 Section 10.

        When jurisdictions conflict:
        - Semantic Lock applies
        - Most restrictive enforcement outcome applies
        - Meaning remains unchanged
        """
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()

        conflict = manager.handle_jurisdiction_conflict(
            prose_contract_id=prose_contract_id,
            jurisdictions=jurisdictions,
            conflict_type=conflict_type,
            description=description
        )

        return {
            "status": "created",
            "conflict_id": conflict.conflict_id,
            "jurisdictions": conflict.jurisdictions,
            "conflict_type": conflict.conflict_type,
            "semantic_lock_applied": conflict.semantic_lock_applied
        }

    def resolve_jurisdiction_conflict(
        self,
        prose_contract_id: str,
        conflict_id: str,
        most_restrictive_outcome: str,
        resolution_notes: str
    ) -> Dict[str, Any]:
        """Resolve a jurisdiction conflict with most restrictive outcome."""
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        bridge = manager.get_bridge(prose_contract_id)

        if not bridge:
            return {
                "status": "error",
                "message": f"No bridge found for {prose_contract_id}"
            }

        conflict = None
        for c in bridge.conflicts:
            if c.conflict_id == conflict_id:
                conflict = c
                break

        if not conflict:
            return {
                "status": "error",
                "message": f"Conflict {conflict_id} not found"
            }

        manager.resolve_conflict(conflict, most_restrictive_outcome, resolution_notes)

        return {
            "status": "resolved",
            "conflict_id": conflict_id,
            "most_restrictive_outcome": most_restrictive_outcome,
            "resolution_notes": resolution_notes,
            "resolved_at": conflict.resolved_at.isoformat() if conflict.resolved_at else None
        }

    def generate_bridge_spec(self, prose_contract_id: str) -> Dict[str, Any]:
        """Generate machine-readable jurisdiction bridge spec per NCIP-006 Section 11."""
        if not NCIP_006_AVAILABLE:
            return {
                "status": "unavailable",
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        return manager.generate_bridge_spec(prose_contract_id)

    def is_ncip_006_enabled(self) -> bool:
        """Check if NCIP-006 jurisdictional bridging is available."""
        return NCIP_006_AVAILABLE

    def get_ncip_006_status(self) -> Dict[str, Any]:
        """Get NCIP-006 implementation status and configuration."""
        if not NCIP_006_AVAILABLE:
            return {
                "enabled": False,
                "message": "NCIP-006 module not available"
            }

        manager = self.get_jurisdictional_manager()
        summary = manager.get_status_summary()

        return {
            "enabled": True,
            "supported_countries": len(VALID_COUNTRY_CODES),
            "us_subdivisions_supported": len(US_STATE_CODES),
            "jurisdiction_roles": ["enforcement", "interpretive", "procedural"],
            "court_ruling_types": ["enforcement", "semantic", "procedural", "void_contract"],
            "semantic_authority": summary["semantic_authority"],
            "external_override_allowed": summary["external_override_allowed"],
            "total_bridges": summary["total_bridges"],
            "total_ltas": summary["total_ltas"],
            "total_court_rulings": summary["total_court_rulings"],
            "total_conflicts": summary["total_conflicts"],
            "principle": "Law constrains enforcement, not meaning"
        }

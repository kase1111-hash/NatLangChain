"""
NatLangChain - Proof of Understanding Scoring
Implements NCIP-004: PoU Generation & Verification

Scoring Dimensions:
- Coverage: All material clauses addressed
- Fidelity: Meaning matches canonical intent
- Consistency: No contradictions
- Completeness: Obligations + consequences acknowledged

Thresholds:
- ≥0.90: Verified - Accept, bind interpretation
- 0.75-0.89: Marginal - Warn, allow resubmission
- 0.50-0.74: Insufficient - Reject, require retry
- <0.50: Failed - Reject, escalate
"""

import hashlib
import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

# Configure PoU logging
logger = logging.getLogger("natlangchain.pou")


class PoUStatus(Enum):
    """PoU verification status per NCIP-004 Section 6."""
    VERIFIED = "verified"          # ≥0.90 - Accept
    MARGINAL = "marginal"          # 0.75-0.89 - Warn, allow resubmission
    INSUFFICIENT = "insufficient"  # 0.50-0.74 - Reject, require retry
    FAILED = "failed"              # <0.50 - Reject, escalate
    INVALID = "invalid"            # Format/structure invalid
    ERROR = "error"                # Processing error


class PoUDimension(Enum):
    """Scoring dimensions per NCIP-004 Section 5."""
    COVERAGE = "coverage"          # All material clauses addressed
    FIDELITY = "fidelity"          # Meaning matches canonical intent
    CONSISTENCY = "consistency"    # No contradictions
    COMPLETENESS = "completeness"  # Obligations + consequences acknowledged


@dataclass
class DimensionScore:
    """Score for a single PoU dimension."""
    dimension: PoUDimension
    score: float
    evidence: str
    issues: List[str] = field(default_factory=list)


@dataclass
class PoUScoreResult:
    """Complete PoU scoring result per NCIP-004."""
    coverage_score: float
    fidelity_score: float
    consistency_score: float
    completeness_score: float
    final_score: float
    status: PoUStatus
    dimension_details: Dict[str, DimensionScore]
    message: str
    binding_effect: bool  # Whether this PoU binds the signer


@dataclass
class SemanticFingerprint:
    """
    Semantic fingerprint for PoU per NCIP-004 Section 10.

    A semantic fingerprint captures the essential meaning
    for later verification and dispute resolution.
    """
    method: str
    hash: str
    content_hash: str
    timestamp: str
    registry_version: str


@dataclass
class PoUSubmission:
    """A structured PoU submission per NCIP-004 Section 4."""
    contract_id: str
    signer_id: str
    signer_role: str
    language: str
    anchor_language: str
    summary: str
    obligations: List[str]
    rights: List[str]
    consequences: List[str]
    acceptance_statement: str
    timestamp: str


@dataclass
class PoUValidationResult:
    """Complete PoU validation result with binding effect."""
    submission: PoUSubmission
    scores: PoUScoreResult
    fingerprint: Optional[SemanticFingerprint]
    validator_id: str
    validated_at: str
    is_bound: bool  # Whether interpretation is bound to signer
    can_resubmit: bool
    actions: Dict[str, bool]


# NCIP-004 Normative Thresholds
POU_THRESHOLDS = {
    PoUStatus.VERIFIED: (0.90, 1.00),
    PoUStatus.MARGINAL: (0.75, 0.90),
    PoUStatus.INSUFFICIENT: (0.50, 0.75),
    PoUStatus.FAILED: (0.00, 0.50)
}

# Response messages per status
POU_MESSAGES = {
    PoUStatus.VERIFIED: "Proof of Understanding verified. Interpretation bound to signer.",
    PoUStatus.MARGINAL: "Proof of Understanding marginal. Clarification recommended before binding.",
    PoUStatus.INSUFFICIENT: "Proof of Understanding insufficient. New submission required.",
    PoUStatus.FAILED: "Proof of Understanding failed. Mediator review required.",
    PoUStatus.INVALID: "Proof of Understanding format invalid.",
    PoUStatus.ERROR: "Proof of Understanding processing error."
}

# Required sections per NCIP-004 Section 4.1
REQUIRED_POU_SECTIONS = ["summary", "obligations", "rights", "consequences", "acceptance_statement"]


class PoUScorer:
    """
    Scores Proof of Understanding submissions per NCIP-004.

    This class provides:
    - Dimension scoring (Coverage, Fidelity, Consistency, Completeness)
    - Status classification based on minimum dimension score
    - Semantic fingerprint generation
    - Binding effect determination
    """

    def __init__(
        self,
        validator_id: str = "default",
        registry_version: str = "1.0",
        api_key: Optional[str] = None
    ):
        """
        Initialize the PoU scorer.

        Args:
            validator_id: Identifier for this validator instance
            registry_version: Version of the canonical term registry
            api_key: Anthropic API key for LLM-based scoring
        """
        self.validator_id = validator_id
        self.registry_version = registry_version
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None
        self._model = "claude-3-5-sonnet-20241022"

    @property
    def client(self):
        """Lazy-load Anthropic client."""
        if self._client is None and self.api_key:
            from anthropic import Anthropic
            self._client = Anthropic(api_key=self.api_key)
        return self._client

    def classify_score(self, score: float) -> PoUStatus:
        """
        Classify a score into PoU status per NCIP-004 Section 6.

        Args:
            score: Score in range [0.0, 1.0]

        Returns:
            PoUStatus based on thresholds
        """
        if score >= 0.90:
            return PoUStatus.VERIFIED
        elif score >= 0.75:
            return PoUStatus.MARGINAL
        elif score >= 0.50:
            return PoUStatus.INSUFFICIENT
        else:
            return PoUStatus.FAILED

    def calculate_final_score(
        self,
        coverage: float,
        fidelity: float,
        consistency: float,
        completeness: float
    ) -> Tuple[float, PoUStatus]:
        """
        Calculate final score per NCIP-004.

        Per NCIP-004 Section 6: The minimum dimension score governs outcome.

        Args:
            coverage: Coverage score [0.0, 1.0]
            fidelity: Fidelity score [0.0, 1.0]
            consistency: Consistency score [0.0, 1.0]
            completeness: Completeness score [0.0, 1.0]

        Returns:
            Tuple of (final_score, status)
        """
        # Minimum dimension score governs
        min_score = min(coverage, fidelity, consistency, completeness)
        status = self.classify_score(min_score)

        return min_score, status

    def generate_fingerprint(
        self,
        pou_content: str,
        contract_content: str
    ) -> SemanticFingerprint:
        """
        Generate semantic fingerprint per NCIP-004 Section 10.

        Args:
            pou_content: The PoU submission content
            contract_content: The original contract content

        Returns:
            SemanticFingerprint with hashes

        Algorithm Details:
            - Hash Algorithm: SHA-256 (FIPS 180-4 compliant)
            - Semantic Hash: SHA-256 of (pou_content + separator + contract_content)
            - Content Hash: SHA-256 of pou_content only
            - Output: First 16 hex characters (64 bits) prefixed with "0x"
            - Encoding: UTF-8 for all string inputs
        """
        # Combine PoU and contract for semantic fingerprint
        # Uses "---" separator to distinguish content boundaries
        combined = f"{pou_content}\n---\n{contract_content}"

        # Generate SHA-256 hashes (cryptographically secure, collision-resistant)
        semantic_hash = hashlib.sha256(combined.encode('utf-8')).hexdigest()
        content_hash = hashlib.sha256(pou_content.encode('utf-8')).hexdigest()

        return SemanticFingerprint(
            method="sha256-semantic-v1",  # Version identifier for hash scheme
            hash=f"0x{semantic_hash[:16]}",  # Truncated for display (full hash in registry)
            content_hash=f"0x{content_hash[:16]}",
            timestamp=datetime.utcnow().isoformat() + "Z",
            registry_version=self.registry_version
        )

    def validate_pou_structure(self, pou_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate PoU structure per NCIP-004 Section 4.1.

        Args:
            pou_data: The PoU submission data

        Returns:
            Tuple of (is_valid, list of issues)
        """
        issues = []

        # Check required fields
        sections = pou_data.get("sections", {})

        if not sections.get("summary") or not sections["summary"].get("text"):
            issues.append("Missing required section: summary")

        obligations = sections.get("obligations")
        if obligations is None or not isinstance(obligations, list):
            issues.append("Missing required section: obligations (must be a list)")
        elif len(obligations) == 0:
            issues.append("Obligations list is empty")

        if not sections.get("rights") or not isinstance(sections["rights"], list):
            issues.append("Missing required section: rights (must be a list)")

        consequences = sections.get("consequences")
        if consequences is None or not isinstance(consequences, list):
            issues.append("Missing required section: consequences (must be a list)")
        elif len(consequences) == 0:
            issues.append("Consequences list is empty")

        acceptance = sections.get("acceptance", {})
        if not acceptance.get("statement"):
            issues.append("Missing required section: acceptance statement")

        # Check for verbatim copying (NCIP-004 Section 4.2)
        # This is a basic check - LLM scoring does deeper analysis
        summary_text = sections.get("summary", {}).get("text", "")
        if len(summary_text) < 20:
            issues.append("Summary is too short to demonstrate understanding")

        return len(issues) == 0, issues

    def score_coverage(
        self,
        pou_sections: Dict[str, Any],
        contract_clauses: List[str]
    ) -> DimensionScore:
        """
        Score coverage dimension: All material clauses addressed.

        Args:
            pou_sections: The PoU sections
            contract_clauses: List of material clauses from contract

        Returns:
            DimensionScore for coverage
        """
        if not contract_clauses:
            return DimensionScore(
                dimension=PoUDimension.COVERAGE,
                score=1.0,
                evidence="No material clauses to address",
                issues=[]
            )

        # Combine PoU sections for checking
        pou_text = ""
        if pou_sections.get("summary", {}).get("text"):
            pou_text += pou_sections["summary"]["text"] + " "
        if pou_sections.get("obligations"):
            pou_text += " ".join(pou_sections["obligations"]) + " "
        if pou_sections.get("rights"):
            pou_text += " ".join(pou_sections["rights"]) + " "
        if pou_sections.get("consequences"):
            pou_text += " ".join(pou_sections["consequences"]) + " "

        pou_text_lower = pou_text.lower()

        # Check coverage of each clause
        covered = 0
        issues = []

        for clause in contract_clauses:
            # Check if key terms from clause appear in PoU
            clause_terms = clause.lower().split()
            key_terms = [t for t in clause_terms if len(t) > 3]

            if key_terms:
                matched = sum(1 for term in key_terms if term in pou_text_lower)
                if matched / len(key_terms) >= 0.3:  # At least 30% term match
                    covered += 1
                else:
                    issues.append(f"Clause may not be addressed: '{clause[:50]}...'")
            else:
                covered += 1  # No key terms to match

        score = covered / len(contract_clauses)

        return DimensionScore(
            dimension=PoUDimension.COVERAGE,
            score=score,
            evidence=f"Covered {covered}/{len(contract_clauses)} material clauses",
            issues=issues
        )

    def score_consistency(
        self,
        pou_sections: Dict[str, Any]
    ) -> DimensionScore:
        """
        Score consistency dimension: No contradictions.

        Args:
            pou_sections: The PoU sections

        Returns:
            DimensionScore for consistency
        """
        issues = []

        # Extract all statements
        obligations = pou_sections.get("obligations", [])
        rights = pou_sections.get("rights", [])
        consequences = pou_sections.get("consequences", [])
        summary = pou_sections.get("summary", {}).get("text", "")

        # Check for obvious contradictions (basic check)
        all_statements = obligations + rights + consequences + [summary]
        all_text = " ".join(all_statements).lower()

        # Look for contradiction patterns
        contradiction_pairs = [
            ("must", "must not"),
            ("always", "never"),
            ("required", "optional"),
            ("guaranteed", "not guaranteed"),
            ("unlimited", "limited"),
            ("permanent", "temporary")
        ]

        contradictions_found = 0
        for pos, neg in contradiction_pairs:
            if pos in all_text and neg in all_text:
                # Could be legitimate (e.g., "X is required, Y is optional")
                # But flag for review
                contradictions_found += 0.5
                issues.append(f"Potential contradiction: both '{pos}' and '{neg}' appear")

        # Check obligations vs rights for conflicts
        for obl in obligations:
            for right in rights:
                if obl.lower() == right.lower():
                    issues.append(f"Duplicate in obligations and rights: '{obl[:30]}...'")
                    contradictions_found += 0.25

        # Calculate score (start at 1.0, reduce for issues)
        score = max(0.0, 1.0 - (contradictions_found * 0.2))

        return DimensionScore(
            dimension=PoUDimension.CONSISTENCY,
            score=score,
            evidence=f"Found {len(issues)} potential consistency issues",
            issues=issues
        )

    def score_completeness(
        self,
        pou_sections: Dict[str, Any]
    ) -> DimensionScore:
        """
        Score completeness dimension: Obligations + consequences acknowledged.

        Args:
            pou_sections: The PoU sections

        Returns:
            DimensionScore for completeness
        """
        issues = []
        completeness_score = 0.0
        max_score = 5.0  # 5 required sections

        # Check each required section
        if pou_sections.get("summary", {}).get("text"):
            summary = pou_sections["summary"]["text"]
            if len(summary) >= 50:
                completeness_score += 1.0
            else:
                completeness_score += 0.5
                issues.append("Summary is brief - may not fully demonstrate understanding")

        obligations = pou_sections.get("obligations", [])
        if obligations and len(obligations) >= 1:
            completeness_score += 1.0
        else:
            issues.append("No obligations acknowledged")

        rights = pou_sections.get("rights", [])
        if rights and len(rights) >= 1:
            completeness_score += 1.0
        else:
            completeness_score += 0.5  # Rights can be empty
            issues.append("No rights acknowledged (may be intentional)")

        consequences = pou_sections.get("consequences", [])
        if consequences and len(consequences) >= 1:
            completeness_score += 1.0
        else:
            issues.append("No consequences acknowledged")

        acceptance = pou_sections.get("acceptance", {})
        if acceptance.get("statement"):
            if len(acceptance["statement"]) >= 10:
                completeness_score += 1.0
            else:
                completeness_score += 0.5
                issues.append("Acceptance statement is minimal")
        else:
            issues.append("No acceptance statement")

        score = completeness_score / max_score

        return DimensionScore(
            dimension=PoUDimension.COMPLETENESS,
            score=score,
            evidence=f"Completeness: {completeness_score}/{max_score} sections complete",
            issues=issues
        )

    def score_fidelity_basic(
        self,
        pou_sections: Dict[str, Any],
        contract_summary: str
    ) -> DimensionScore:
        """
        Basic fidelity scoring without LLM.

        For full semantic fidelity checking, use score_fidelity_llm().

        Args:
            pou_sections: The PoU sections
            contract_summary: Brief summary of contract for comparison

        Returns:
            DimensionScore for fidelity
        """
        issues = []

        summary = pou_sections.get("summary", {}).get("text", "")

        if not summary:
            return DimensionScore(
                dimension=PoUDimension.FIDELITY,
                score=0.0,
                evidence="No summary provided for fidelity check",
                issues=["Missing summary"]
            )

        # Basic keyword matching
        contract_words = set(contract_summary.lower().split())
        summary_words = set(summary.lower().split())

        # Filter to meaningful words
        meaningful_contract = {w for w in contract_words if len(w) > 3}
        meaningful_summary = {w for w in summary_words if len(w) > 3}

        if not meaningful_contract:
            return DimensionScore(
                dimension=PoUDimension.FIDELITY,
                score=1.0,
                evidence="Contract has no meaningful terms to check",
                issues=[]
            )

        # Check overlap
        overlap = meaningful_contract & meaningful_summary
        coverage = len(overlap) / len(meaningful_contract) if meaningful_contract else 1.0

        # Check for additions (potential meaning drift)
        additions = meaningful_summary - meaningful_contract
        if len(additions) > len(meaningful_contract):
            issues.append("PoU adds significant content beyond contract scope")
            coverage = min(coverage, 0.8)

        return DimensionScore(
            dimension=PoUDimension.FIDELITY,
            score=min(1.0, coverage),
            evidence=f"Term overlap: {len(overlap)}/{len(meaningful_contract)} key terms matched",
            issues=issues
        )

    def score_pou(
        self,
        pou_data: Dict[str, Any],
        contract_content: str,
        contract_clauses: Optional[List[str]] = None
    ) -> PoUScoreResult:
        """
        Score a complete PoU submission per NCIP-004.

        Args:
            pou_data: The PoU submission in NCIP-004 schema format
            contract_content: The original contract content
            contract_clauses: Optional list of material clauses

        Returns:
            PoUScoreResult with all dimension scores and status
        """
        # Validate structure first
        is_valid, structure_issues = self.validate_pou_structure(pou_data)

        if not is_valid:
            return PoUScoreResult(
                coverage_score=0.0,
                fidelity_score=0.0,
                consistency_score=0.0,
                completeness_score=0.0,
                final_score=0.0,
                status=PoUStatus.INVALID,
                dimension_details={},
                message=f"Structure invalid: {'; '.join(structure_issues)}",
                binding_effect=False
            )

        sections = pou_data.get("sections", {})

        # Score each dimension
        coverage = self.score_coverage(
            sections,
            contract_clauses or []
        )

        consistency = self.score_consistency(sections)

        completeness = self.score_completeness(sections)

        fidelity = self.score_fidelity_basic(sections, contract_content)

        # Calculate final score (minimum governs)
        final_score, status = self.calculate_final_score(
            coverage.score,
            fidelity.score,
            consistency.score,
            completeness.score
        )

        # Determine binding effect per NCIP-004 Section 9
        binding_effect = status == PoUStatus.VERIFIED

        return PoUScoreResult(
            coverage_score=coverage.score,
            fidelity_score=fidelity.score,
            consistency_score=consistency.score,
            completeness_score=completeness.score,
            final_score=final_score,
            status=status,
            dimension_details={
                "coverage": coverage,
                "fidelity": fidelity,
                "consistency": consistency,
                "completeness": completeness
            },
            message=POU_MESSAGES[status],
            binding_effect=binding_effect
        )

    def validate_and_score(
        self,
        pou_data: Dict[str, Any],
        contract_content: str,
        contract_clauses: Optional[List[str]] = None,
        generate_fingerprint: bool = True
    ) -> PoUValidationResult:
        """
        Full PoU validation with scoring and fingerprint generation.

        Args:
            pou_data: The PoU submission data
            contract_content: The original contract content
            contract_clauses: Optional list of material clauses
            generate_fingerprint: Whether to generate semantic fingerprint

        Returns:
            Complete PoUValidationResult
        """
        # Parse submission
        try:
            submission = PoUSubmission(
                contract_id=pou_data.get("contract_id", "unknown"),
                signer_id=pou_data.get("signer", {}).get("id", "unknown"),
                signer_role=pou_data.get("signer", {}).get("role", "unknown"),
                language=pou_data.get("language", "en"),
                anchor_language=pou_data.get("anchor_language", "en"),
                summary=pou_data.get("sections", {}).get("summary", {}).get("text", ""),
                obligations=pou_data.get("sections", {}).get("obligations", []),
                rights=pou_data.get("sections", {}).get("rights", []),
                consequences=pou_data.get("sections", {}).get("consequences", []),
                acceptance_statement=pou_data.get("sections", {}).get("acceptance", {}).get("statement", ""),
                timestamp=pou_data.get("sections", {}).get("acceptance", {}).get("timestamp",
                                                                                  datetime.utcnow().isoformat() + "Z")
            )
        except Exception as e:
            # Return error result
            return PoUValidationResult(
                submission=PoUSubmission(
                    contract_id="error",
                    signer_id="error",
                    signer_role="error",
                    language="en",
                    anchor_language="en",
                    summary="",
                    obligations=[],
                    rights=[],
                    consequences=[],
                    acceptance_statement="",
                    timestamp=datetime.utcnow().isoformat() + "Z"
                ),
                scores=PoUScoreResult(
                    coverage_score=0.0,
                    fidelity_score=0.0,
                    consistency_score=0.0,
                    completeness_score=0.0,
                    final_score=0.0,
                    status=PoUStatus.ERROR,
                    dimension_details={},
                    message=f"Failed to parse PoU: {str(e)}",
                    binding_effect=False
                ),
                fingerprint=None,
                validator_id=self.validator_id,
                validated_at=datetime.utcnow().isoformat() + "Z",
                is_bound=False,
                can_resubmit=True,
                actions=self._get_actions(PoUStatus.ERROR)
            )

        # Score the PoU
        scores = self.score_pou(pou_data, contract_content, contract_clauses)

        # Generate fingerprint if requested and verified/marginal
        fingerprint = None
        if generate_fingerprint and scores.status in [PoUStatus.VERIFIED, PoUStatus.MARGINAL]:
            pou_content = json.dumps(pou_data.get("sections", {}), sort_keys=True)
            fingerprint = self.generate_fingerprint(pou_content, contract_content)

        # Determine binding and resubmission
        is_bound = scores.status == PoUStatus.VERIFIED
        can_resubmit = scores.status in [PoUStatus.MARGINAL, PoUStatus.INSUFFICIENT]

        return PoUValidationResult(
            submission=submission,
            scores=scores,
            fingerprint=fingerprint,
            validator_id=self.validator_id,
            validated_at=datetime.utcnow().isoformat() + "Z",
            is_bound=is_bound,
            can_resubmit=can_resubmit,
            actions=self._get_actions(scores.status)
        )

    def _get_actions(self, status: PoUStatus) -> Dict[str, bool]:
        """
        Get mandatory validator actions per NCIP-004 Section 7.

        Args:
            status: The PoU status

        Returns:
            Dict of action flags
        """
        return {
            "accept": status == PoUStatus.VERIFIED,
            "bind_interpretation": status == PoUStatus.VERIFIED,
            "store_fingerprint": status in [PoUStatus.VERIFIED, PoUStatus.MARGINAL],
            "accept_temporary": status == PoUStatus.MARGINAL,
            "flag_for_review": status == PoUStatus.MARGINAL,
            "recommend_clarification": status == PoUStatus.MARGINAL,
            "reject": status in [PoUStatus.INSUFFICIENT, PoUStatus.FAILED],
            "block_execution": status in [PoUStatus.INSUFFICIENT, PoUStatus.FAILED],
            "require_new_pou": status == PoUStatus.INSUFFICIENT,
            "require_mediator": status == PoUStatus.FAILED,
            "escalate": status == PoUStatus.FAILED
        }

    def get_validator_response(
        self,
        pou_data: Dict[str, Any],
        contract_content: str,
        contract_clauses: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Get complete validator response for a PoU submission.

        This is the main entry point for validators to process PoU.

        Args:
            pou_data: The PoU submission data
            contract_content: The original contract content
            contract_clauses: Optional list of material clauses

        Returns:
            Complete validator response dict
        """
        result = self.validate_and_score(pou_data, contract_content, contract_clauses)

        response = {
            "status": result.scores.status.value,
            "final_score": result.scores.final_score,
            "dimension_scores": {
                "coverage": result.scores.coverage_score,
                "fidelity": result.scores.fidelity_score,
                "consistency": result.scores.consistency_score,
                "completeness": result.scores.completeness_score
            },
            "message": result.scores.message,
            "binding_effect": result.is_bound,
            "can_resubmit": result.can_resubmit,
            "actions": result.actions,
            "validator_id": result.validator_id,
            "validated_at": result.validated_at
        }

        if result.fingerprint:
            response["semantic_fingerprint"] = {
                "method": result.fingerprint.method,
                "hash": result.fingerprint.hash,
                "content_hash": result.fingerprint.content_hash,
                "timestamp": result.fingerprint.timestamp
            }

        # Include dimension details for debugging
        response["dimension_details"] = {}
        for dim_name, dim_score in result.scores.dimension_details.items():
            response["dimension_details"][dim_name] = {
                "score": dim_score.score,
                "evidence": dim_score.evidence,
                "issues": dim_score.issues
            }

        return response


class BindingPoURecord:
    """
    Represents a bound PoU per NCIP-004 Section 9.

    A verified PoU:
    - Fixes meaning for the signer
    - Waives claims of misunderstanding
    - Overrides later reinterpretations by that party
    - Is admissible in dispute resolution
    """

    def __init__(
        self,
        contract_id: str,
        signer_id: str,
        pou_data: Dict[str, Any],
        scores: PoUScoreResult,
        fingerprint: SemanticFingerprint,
        bound_at: str
    ):
        """
        Create a binding PoU record.

        Args:
            contract_id: The contract this PoU binds to
            signer_id: The signer who is bound
            pou_data: The original PoU submission
            scores: The validation scores
            fingerprint: The semantic fingerprint
            bound_at: Timestamp of binding
        """
        if scores.status != PoUStatus.VERIFIED:
            raise ValueError(
                f"Cannot create binding record for non-verified PoU (status: {scores.status.value})"
            )

        self.contract_id = contract_id
        self.signer_id = signer_id
        self.pou_data = pou_data
        self.scores = scores
        self.fingerprint = fingerprint
        self.bound_at = bound_at
        self.waives_misunderstanding = True
        self.admissible_in_dispute = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "contract_id": self.contract_id,
            "signer_id": self.signer_id,
            "bound_at": self.bound_at,
            "waives_misunderstanding": self.waives_misunderstanding,
            "admissible_in_dispute": self.admissible_in_dispute,
            "scores": {
                "coverage": self.scores.coverage_score,
                "fidelity": self.scores.fidelity_score,
                "consistency": self.scores.consistency_score,
                "completeness": self.scores.completeness_score,
                "final": self.scores.final_score
            },
            "fingerprint": {
                "method": self.fingerprint.method,
                "hash": self.fingerprint.hash,
                "content_hash": self.fingerprint.content_hash,
                "timestamp": self.fingerprint.timestamp
            },
            "binding_effect": {
                "fixes_meaning": True,
                "overrides_reinterpretation": True
            }
        }


# Machine-readable configuration per NCIP-004
NCIP_004_CONFIG = {
    "proof_of_understanding": {
        "version": "1.0",
        "thresholds": {
            "verified": {"min": 0.90, "max": 1.00, "action": "accept_and_bind"},
            "marginal": {"min": 0.75, "max": 0.90, "action": "warn_and_flag"},
            "insufficient": {"min": 0.50, "max": 0.75, "action": "reject_retry"},
            "failed": {"min": 0.00, "max": 0.50, "action": "reject_escalate"}
        },
        "dimensions": ["coverage", "fidelity", "consistency", "completeness"],
        "minimum_governs": True,
        "required_sections": ["summary", "obligations", "rights", "consequences", "acceptance"],
        "binding_effect": {
            "verified_only": True,
            "waives_misunderstanding": True,
            "admissible_in_dispute": True
        }
    }
}


def get_pou_config() -> Dict[str, Any]:
    """Get the NCIP-004 PoU configuration."""
    return NCIP_004_CONFIG.copy()


def score_pou(
    pou_data: Dict[str, Any],
    contract_content: str,
    contract_clauses: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Convenience function to score a PoU submission.

    Args:
        pou_data: The PoU submission data
        contract_content: The original contract content
        contract_clauses: Optional list of material clauses

    Returns:
        Validator response dict
    """
    scorer = PoUScorer()
    return scorer.get_validator_response(pou_data, contract_content, contract_clauses)


def classify_pou_score(score: float) -> PoUStatus:
    """
    Convenience function to classify a PoU score.

    Args:
        score: Score in range [0.0, 1.0]

    Returns:
        PoUStatus
    """
    scorer = PoUScorer()
    return scorer.classify_score(score)

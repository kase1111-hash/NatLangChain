"""
NCIP-003: Multilingual Semantic Alignment & Drift

This module implements multilingual support for NatLangChain without semantic divergence.

Core Principle: NatLangChain is multilingual, not multi-meaning.
One meaning exists, many expressions allowed.

Key concepts:
- Canonical Semantic Anchor Language (CSAL): Source of truth for meaning
- Language Roles: anchor, aligned, informational
- Cross-language drift measurement relative to CSAL
- Translation validation preventing obligation changes
"""

import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class LanguageRole(Enum):
    """
    Language roles per NCIP-003 Section 3.

    Each language instance MUST declare exactly one role.
    """
    ANCHOR = "anchor"           # Canonical meaning source
    ALIGNED = "aligned"         # Verified semantic equivalent
    INFORMATIONAL = "informational"  # Human convenience only (non-executable)


class DriftLevel(Enum):
    """
    Drift levels per NCIP-002, used for multilingual drift.
    """
    D0 = "D0"  # 0.00-0.10: Identical/near-identical
    D1 = "D1"  # 0.10-0.25: Minor lexical variation
    D2 = "D2"  # 0.25-0.45: Noticeable but manageable
    D3 = "D3"  # 0.45-0.70: Significant divergence
    D4 = "D4"  # 0.70-1.00: Critical divergence


class ValidatorAction(Enum):
    """
    Mandatory validator responses for multilingual drift per NCIP-003 Section 6.
    """
    ACCEPT = "accept"                    # D0-D1: Accept translation
    PAUSE_CLARIFY = "pause_clarify"      # D2: Pause execution, request clarification
    REQUIRE_RATIFICATION = "require_ratification"  # D3: Require human ratification
    REJECT_ESCALATE = "reject_escalate"  # D4: Reject translation, escalate dispute


class TranslationViolation(Enum):
    """
    Prohibited behaviors in aligned translations per NCIP-003 Section 4.2.
    """
    INTRODUCED_CONSTRAINT = "introduced_constraint"
    REMOVED_OBLIGATION = "removed_obligation"
    NARROWED_SCOPE = "narrowed_scope"
    BROADENED_SCOPE = "broadened_scope"
    NON_REGISTRY_TERM = "non_registry_term"
    MISSING_CSAL_DECLARATION = "missing_csal_declaration"
    INVALID_ROLE = "invalid_role"
    DUPLICATE_ANCHOR = "duplicate_anchor"


# ISO 639-1 language codes (common subset)
SUPPORTED_LANGUAGE_CODES = {
    "en", "es", "fr", "de", "it", "pt", "nl", "pl", "ru", "uk",
    "zh", "ja", "ko", "ar", "hi", "bn", "vi", "th", "id", "ms",
    "tr", "el", "he", "fa", "sv", "no", "da", "fi", "cs", "sk",
    "hu", "ro", "bg", "hr", "sr", "sl", "lt", "lv", "et"
}


@dataclass
class LanguageEntry:
    """
    A language instance within a multilingual contract.

    Per NCIP-003, each language must declare a role.
    """
    code: str  # ISO 639-1 code
    role: LanguageRole
    content: str
    drift_tolerance: float = 0.25  # Default per NCIP-002 D2 threshold
    drift_score: float | None = None
    drift_level: DriftLevel | None = None
    validated: bool = False
    validation_timestamp: datetime | None = None
    violations: list[TranslationViolation] = field(default_factory=list)
    affected_clauses: list[str] = field(default_factory=list)
    affected_terms: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.code not in SUPPORTED_LANGUAGE_CODES:
            raise ValueError(f"Unsupported language code: {self.code}")

    @property
    def is_executable(self) -> bool:
        """Only anchor and aligned languages may influence execution."""
        return self.role in [LanguageRole.ANCHOR, LanguageRole.ALIGNED]

    @property
    def is_valid(self) -> bool:
        """Check if the language entry is valid (no violations, acceptable drift)."""
        if self.violations:
            return False
        return not (self.drift_score is not None and self.drift_score > self.drift_tolerance)


@dataclass
class CanonicalTermMapping:
    """
    Mapping of a canonical term across languages per NCIP-003 Section 7.

    All core terms from NCIP-001:
    - MUST remain semantically identical across languages
    - MAY be translated lexically
    - MUST map to the same registry ID
    """
    term_id: str  # Registry ID from NCIP-001
    anchor_term: str  # Term in anchor language
    translations: dict[str, str] = field(default_factory=dict)  # lang_code -> translated term
    glosses: dict[str, str] = field(default_factory=dict)  # lang_code -> explanatory gloss
    usage_notes: dict[str, str] = field(default_factory=dict)  # lang_code -> usage note

    def get_term(self, lang_code: str) -> str | None:
        """Get the term in a specific language."""
        if lang_code == "en":  # Assuming anchor is English
            return self.anchor_term
        return self.translations.get(lang_code)

    def add_translation(self, lang_code: str, translated_term: str) -> None:
        """Add a translation for this term."""
        self.translations[lang_code] = translated_term


@dataclass
class ClauseDriftResult:
    """Result of drift analysis for a specific clause."""
    clause_id: str
    anchor_text: str
    aligned_text: str
    language_code: str
    drift_score: float
    drift_level: DriftLevel
    terms_affected: list[str] = field(default_factory=list)
    violations: list[TranslationViolation] = field(default_factory=list)
    requires_action: bool = False
    recommended_action: ValidatorAction | None = None


@dataclass
class MultilingualRatification:
    """
    Human ratification for multilingual contexts per NCIP-003 Section 8.

    Must:
    - Reference the CSAL explicitly
    - Acknowledge reviewed aligned languages
    - Bind all translations to the anchor meaning
    """
    ratification_id: str
    anchor_language: str
    reviewed_languages: list[str]
    ratified_at: datetime = field(default_factory=datetime.utcnow)
    ratifier_id: str = ""
    statement: str = ""  # "I ratify the English (anchor) meaning..."
    binding_acknowledged: bool = False

    def __post_init__(self):
        if not self.statement:
            self.statement = (
                f"I ratify the {self.anchor_language} (anchor) meaning "
                f"and accept aligned translations as equivalent."
            )

    @property
    def is_valid(self) -> bool:
        """Check if ratification meets NCIP-003 requirements."""
        return (
            bool(self.anchor_language) and
            bool(self.reviewed_languages) and
            self.binding_acknowledged
        )


@dataclass
class AlignmentRules:
    """
    Alignment rules for multilingual contracts per NCIP-003 Section 4.
    """
    # Core term rules
    must_map_to_registry: bool = True
    allow_lexical_variation: bool = True
    allow_semantic_variation: bool = False

    # Obligation rules
    allow_obligation_addition: bool = False
    allow_obligation_removal: bool = False
    allow_scope_change: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "core_terms": {
                "must_map_to_registry": self.must_map_to_registry,
                "allow_lexical_variation": self.allow_lexical_variation,
                "allow_semantic_variation": self.allow_semantic_variation
            },
            "obligations": {
                "allow_addition": self.allow_obligation_addition,
                "allow_removal": self.allow_obligation_removal,
                "allow_scope_change": self.allow_scope_change
            }
        }


@dataclass
class MultilingualContract:
    """
    A multilingual prose contract with CSAL declaration.

    Per NCIP-003 Section 2, every multilingual contract MUST declare
    a Canonical Semantic Anchor Language.
    """
    contract_id: str
    canonical_anchor_language: str = "en"  # Default per NCIP-003
    languages: dict[str, LanguageEntry] = field(default_factory=dict)
    alignment_rules: AlignmentRules = field(default_factory=AlignmentRules)
    term_mappings: dict[str, CanonicalTermMapping] = field(default_factory=dict)
    ratifications: list[MultilingualRatification] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)

    # Validation state
    validated: bool = False
    max_drift_score: float = 0.0
    max_drift_level: DriftLevel | None = None
    overall_action: ValidatorAction | None = None

    def __post_init__(self):
        # Emit D1 warning if CSAL not explicitly set (using default)
        self._csal_explicit = self.canonical_anchor_language != "en"

    @property
    def anchor_entry(self) -> LanguageEntry | None:
        """Get the anchor language entry."""
        for entry in self.languages.values():
            if entry.role == LanguageRole.ANCHOR:
                return entry
        return None

    @property
    def aligned_entries(self) -> list[LanguageEntry]:
        """Get all aligned language entries."""
        return [e for e in self.languages.values() if e.role == LanguageRole.ALIGNED]

    @property
    def informational_entries(self) -> list[LanguageEntry]:
        """Get all informational language entries."""
        return [e for e in self.languages.values() if e.role == LanguageRole.INFORMATIONAL]

    @property
    def executable_languages(self) -> list[str]:
        """Get language codes that may influence execution."""
        return [code for code, entry in self.languages.items() if entry.is_executable]

    def add_language(
        self,
        code: str,
        role: LanguageRole,
        content: str,
        drift_tolerance: float = 0.25
    ) -> tuple[bool, str]:
        """
        Add a language entry to the contract.

        Returns (success, message).
        """
        # Validate role assignment
        if role == LanguageRole.ANCHOR:
            # Check for existing anchor
            if any(e.role == LanguageRole.ANCHOR for e in self.languages.values()):
                return (False, "Contract already has an anchor language")
            # Anchor must match CSAL
            if code != self.canonical_anchor_language:
                return (False, f"Anchor language must match CSAL ({self.canonical_anchor_language})")

        entry = LanguageEntry(
            code=code,
            role=role,
            content=content,
            drift_tolerance=drift_tolerance
        )

        self.languages[code] = entry
        return (True, f"Added {code} as {role.value}")

    def get_language(self, code: str) -> LanguageEntry | None:
        """Get a language entry by code."""
        return self.languages.get(code)

    def is_csal_declared(self) -> bool:
        """Check if CSAL is explicitly declared (not default)."""
        return self._csal_explicit


class MultilingualAlignmentManager:
    """
    Manages multilingual alignment and drift detection per NCIP-003.

    Responsibilities:
    - CSAL declaration validation
    - Cross-language drift measurement
    - Translation violation detection
    - Validator response determination
    """

    # Drift thresholds per NCIP-002
    DRIFT_THRESHOLDS = {
        DriftLevel.D0: (0.00, 0.10),
        DriftLevel.D1: (0.10, 0.25),
        DriftLevel.D2: (0.25, 0.45),
        DriftLevel.D3: (0.45, 0.70),
        DriftLevel.D4: (0.70, 1.00),
    }

    # Validator actions per drift level
    DRIFT_ACTIONS = {
        DriftLevel.D0: ValidatorAction.ACCEPT,
        DriftLevel.D1: ValidatorAction.ACCEPT,
        DriftLevel.D2: ValidatorAction.PAUSE_CLARIFY,
        DriftLevel.D3: ValidatorAction.REQUIRE_RATIFICATION,
        DriftLevel.D4: ValidatorAction.REJECT_ESCALATE,
    }

    def __init__(self):
        self.contracts: dict[str, MultilingualContract] = {}
        self.term_registry: dict[str, CanonicalTermMapping] = {}

    # -------------------------------------------------------------------------
    # Contract Management
    # -------------------------------------------------------------------------

    def create_contract(
        self,
        contract_id: str,
        canonical_anchor_language: str = "en"
    ) -> MultilingualContract:
        """
        Create a new multilingual contract with CSAL declaration.

        Per NCIP-003 Section 2.2, the CSAL is required.
        Default is English (en).
        """
        contract = MultilingualContract(
            contract_id=contract_id,
            canonical_anchor_language=canonical_anchor_language
        )
        self.contracts[contract_id] = contract
        return contract

    def get_contract(self, contract_id: str) -> MultilingualContract | None:
        """Get a contract by ID."""
        return self.contracts.get(contract_id)

    def validate_csal_declaration(
        self,
        contract: MultilingualContract
    ) -> tuple[bool, list[str]]:
        """
        Validate CSAL declaration per NCIP-003 Section 2.

        Returns (valid, warnings).
        """
        warnings = []

        # Check if CSAL is explicitly declared
        if not contract.is_csal_declared():
            warnings.append(
                f"D1 Warning: CSAL not explicitly declared, assuming '{contract.canonical_anchor_language}'"
            )

        # Check if anchor language exists
        anchor = contract.anchor_entry
        if not anchor:
            return (False, ["No anchor language defined"])

        # Verify anchor matches CSAL
        if anchor.code != contract.canonical_anchor_language:
            return (False, [
                f"Anchor language ({anchor.code}) does not match CSAL ({contract.canonical_anchor_language})"
            ])

        return (True, warnings)

    # -------------------------------------------------------------------------
    # Drift Measurement
    # -------------------------------------------------------------------------

    def compute_drift_level(self, score: float) -> DriftLevel:
        """Compute drift level from score using NCIP-002 thresholds."""
        for level, (low, high) in self.DRIFT_THRESHOLDS.items():
            if low <= score < high:
                return level
        return DriftLevel.D4  # Score >= 1.0

    def get_validator_action(self, drift_level: DriftLevel) -> ValidatorAction:
        """Get the mandatory validator action for a drift level."""
        return self.DRIFT_ACTIONS[drift_level]

    def measure_cross_language_drift(
        self,
        anchor_text: str,
        aligned_text: str,
        language_code: str
    ) -> tuple[float, DriftLevel]:
        """
        Measure semantic drift between anchor and aligned text.

        Per NCIP-003 Section 5.1:
        drift(Lᵢ) = semantic_distance(anchor, Lᵢ)

        This is a simplified implementation. In production, this would use:
        - Cross-lingual embeddings
        - Machine translation + comparison
        - LLM-based semantic similarity
        """
        # Simplified drift calculation based on:
        # - Length ratio (significant length difference may indicate added/removed content)
        # - Structural similarity (sentence count, paragraph count)

        anchor_len = len(anchor_text)
        aligned_len = len(aligned_text)

        if anchor_len == 0:
            return (1.0, DriftLevel.D4)

        # Length ratio component (accounts for translation expansion/contraction)
        # Languages like German expand ~30%, Japanese contracts ~20%
        length_ratio = abs(anchor_len - aligned_len) / anchor_len
        # Normalize: up to 50% length difference is common in translation
        length_score = min(length_ratio / 2.0, 0.5)

        # Sentence count comparison
        anchor_sentences = len(re.split(r'[.!?]+', anchor_text))
        aligned_sentences = len(re.split(r'[.!?]+', aligned_text))
        sentence_diff = abs(anchor_sentences - aligned_sentences)
        sentence_score = min(sentence_diff * 0.1, 0.3)

        # Simple content similarity (shared numbers, proper nouns tend to appear in both)
        set(re.findall(r'\b\w+\b', anchor_text.lower()))
        set(re.findall(r'\b\w+\b', aligned_text.lower()))
        # Focus on numbers and capitalized words that might transfer
        anchor_nums = set(re.findall(r'\b\d+\b', anchor_text))
        aligned_nums = set(re.findall(r'\b\d+\b', aligned_text))
        if anchor_nums:
            num_overlap = len(anchor_nums & aligned_nums) / len(anchor_nums)
            num_score = (1 - num_overlap) * 0.2
        else:
            num_score = 0.0

        # Combine scores
        drift_score = min(length_score + sentence_score + num_score, 1.0)
        drift_level = self.compute_drift_level(drift_score)

        return (drift_score, drift_level)

    def analyze_clause_drift(
        self,
        clause_id: str,
        anchor_text: str,
        aligned_text: str,
        language_code: str,
        canonical_terms: list[str] | None = None
    ) -> ClauseDriftResult:
        """
        Analyze drift for a specific clause between anchor and aligned text.

        Returns detailed drift analysis.
        """
        drift_score, drift_level = self.measure_cross_language_drift(
            anchor_text, aligned_text, language_code
        )

        # Determine required action
        action = self.get_validator_action(drift_level)
        requires_action = action != ValidatorAction.ACCEPT

        # Check for term violations if canonical terms provided
        violations = []
        terms_affected = []
        if canonical_terms:
            for term in canonical_terms:
                # Check if term appears in anchor but concept missing in aligned
                if term.lower() in anchor_text.lower():
                    # This is simplified - real implementation would use semantic matching
                    terms_affected.append(term)

        return ClauseDriftResult(
            clause_id=clause_id,
            anchor_text=anchor_text,
            aligned_text=aligned_text,
            language_code=language_code,
            drift_score=drift_score,
            drift_level=drift_level,
            terms_affected=terms_affected,
            violations=violations,
            requires_action=requires_action,
            recommended_action=action
        )

    def validate_contract_alignment(
        self,
        contract: MultilingualContract
    ) -> tuple[bool, dict[str, Any]]:
        """
        Validate alignment of all languages in a contract.

        Per NCIP-003 Section 5.2:
        - Drift is computed per clause and per term
        - Maximum drift score governs validator response
        - Drift in any aligned language applies to whole contract

        Returns (valid, validation_report).
        """
        report: dict[str, Any] = {
            "contract_id": contract.contract_id,
            "csal": contract.canonical_anchor_language,
            "languages_checked": [],
            "drift_results": {},
            "max_drift_score": 0.0,
            "max_drift_level": None,
            "overall_action": None,
            "violations": [],
            "valid": True
        }

        # Validate CSAL declaration
        csal_valid, csal_warnings = self.validate_csal_declaration(contract)
        if not csal_valid:
            report["valid"] = False
            report["violations"].extend(csal_warnings)
            return (False, report)

        if csal_warnings:
            report["warnings"] = csal_warnings

        # Get anchor content
        anchor = contract.anchor_entry
        if not anchor:
            report["valid"] = False
            report["violations"].append("No anchor language found")
            return (False, report)

        anchor_content = anchor.content

        # Validate each aligned language
        for lang_code, entry in contract.languages.items():
            if entry.role != LanguageRole.ALIGNED:
                continue

            report["languages_checked"].append(lang_code)

            # Measure drift
            drift_score, drift_level = self.measure_cross_language_drift(
                anchor_content, entry.content, lang_code
            )

            # Update entry
            entry.drift_score = drift_score
            entry.drift_level = drift_level
            entry.validated = True
            entry.validation_timestamp = datetime.utcnow()

            # Store results
            report["drift_results"][lang_code] = {
                "drift_score": drift_score,
                "drift_level": drift_level.value,
                "action": self.get_validator_action(drift_level).value,
                "within_tolerance": drift_score <= entry.drift_tolerance
            }

            # Track maximum drift (governs overall response)
            if drift_score > report["max_drift_score"]:
                report["max_drift_score"] = drift_score
                report["max_drift_level"] = drift_level.value

        # Determine overall action based on max drift
        if report["max_drift_level"]:
            max_level = DriftLevel(report["max_drift_level"])
            report["overall_action"] = self.get_validator_action(max_level).value

            # Update contract state
            contract.max_drift_score = report["max_drift_score"]
            contract.max_drift_level = max_level
            contract.overall_action = self.get_validator_action(max_level)
            contract.validated = True

        # Check for D4 (critical divergence)
        if report["max_drift_level"] == DriftLevel.D4.value:
            report["valid"] = False
            report["violations"].append("Critical semantic divergence detected (D4)")

        return (report["valid"], report)

    # -------------------------------------------------------------------------
    # Translation Validation
    # -------------------------------------------------------------------------

    def check_translation_violations(
        self,
        anchor_text: str,
        aligned_text: str,
        language_code: str,
        alignment_rules: AlignmentRules | None = None
    ) -> list[TranslationViolation]:
        """
        Check for prohibited behaviors in aligned translation.

        Per NCIP-003 Section 4.2, an aligned translation MUST NOT:
        - Introduce new constraints
        - Remove obligations
        - Narrow or broaden scope
        - Replace canonical terms with non-registry concepts
        """
        violations = []
        rules = alignment_rules or AlignmentRules()

        # Check for obligation indicators
        # This is simplified - real implementation would use NLP/LLM
        obligation_words = ["must", "shall", "required", "mandatory", "obligated"]

        anchor_lower = anchor_text.lower()
        aligned_lower = aligned_text.lower()

        # Count obligation indicators
        anchor_obligations = sum(1 for w in obligation_words if w in anchor_lower)
        aligned_obligations = sum(1 for w in obligation_words if w in aligned_lower)

        # Check for added obligations
        if aligned_obligations > anchor_obligations and not rules.allow_obligation_addition:
            violations.append(TranslationViolation.INTRODUCED_CONSTRAINT)

        # Check for removed obligations
        if aligned_obligations < anchor_obligations and not rules.allow_obligation_removal:
            violations.append(TranslationViolation.REMOVED_OBLIGATION)

        # Check for scope changes (simplified: look for "all", "any", "limited", etc.)
        scope_broadeners = ["all", "any", "every", "unlimited"]

        anchor_broad = sum(1 for w in scope_broadeners if w in anchor_lower)
        aligned_broad = sum(1 for w in scope_broadeners if w in aligned_lower)

        if aligned_broad > anchor_broad and not rules.allow_scope_change:
            violations.append(TranslationViolation.BROADENED_SCOPE)
        elif aligned_broad < anchor_broad and not rules.allow_scope_change:
            violations.append(TranslationViolation.NARROWED_SCOPE)

        return violations

    def validate_term_mapping(
        self,
        contract: MultilingualContract,
        term_id: str,
        anchor_term: str,
        translated_term: str,
        language_code: str
    ) -> tuple[bool, str]:
        """
        Validate that a term mapping preserves semantic identity.

        Per NCIP-003 Section 7.1:
        - MUST remain semantically identical across languages
        - MAY be translated lexically
        - MUST map to the same registry ID
        """
        # Create or get term mapping
        if term_id not in contract.term_mappings:
            mapping = CanonicalTermMapping(
                term_id=term_id,
                anchor_term=anchor_term
            )
            contract.term_mappings[term_id] = mapping

        mapping = contract.term_mappings[term_id]

        # Verify anchor term matches
        if mapping.anchor_term != anchor_term:
            return (False, f"Anchor term mismatch for {term_id}")

        # Add translation
        mapping.add_translation(language_code, translated_term)

        return (True, f"Term mapping added: {term_id} -> {translated_term} ({language_code})")

    # -------------------------------------------------------------------------
    # Human Ratification
    # -------------------------------------------------------------------------

    def create_multilingual_ratification(
        self,
        contract: MultilingualContract,
        ratifier_id: str,
        reviewed_languages: list[str]
    ) -> MultilingualRatification:
        """
        Create a multilingual ratification per NCIP-003 Section 8.

        The ratification:
        - References the CSAL explicitly
        - Acknowledges reviewed aligned languages
        - Binds all translations to the anchor meaning
        """
        ratification = MultilingualRatification(
            ratification_id=f"RAT-{contract.contract_id}-{len(contract.ratifications) + 1}",
            anchor_language=contract.canonical_anchor_language,
            reviewed_languages=reviewed_languages,
            ratifier_id=ratifier_id
        )

        contract.ratifications.append(ratification)
        return ratification

    def confirm_ratification(
        self,
        ratification: MultilingualRatification
    ) -> tuple[bool, str]:
        """
        Confirm a multilingual ratification binding.

        User must acknowledge that translations are bound to anchor meaning.
        """
        if not ratification.reviewed_languages:
            return (False, "No languages were reviewed")

        ratification.binding_acknowledged = True
        return (True, ratification.statement)

    # -------------------------------------------------------------------------
    # Validator Integration
    # -------------------------------------------------------------------------

    def validator_report_drift(
        self,
        contract_id: str,
        language_code: str
    ) -> dict[str, Any]:
        """
        Generate validator report for drift per NCIP-003 Section 6.

        Validators MUST report:
        - Language pair
        - Affected clauses
        - Drift score
        - Canonical terms involved
        """
        contract = self.get_contract(contract_id)
        if not contract:
            return {"error": f"Contract {contract_id} not found"}

        entry = contract.get_language(language_code)
        if not entry:
            return {"error": f"Language {language_code} not found in contract"}

        anchor = contract.anchor_entry
        if not anchor:
            return {"error": "No anchor language found"}

        return {
            "language_pair": f"{anchor.code}-{language_code}",
            "anchor_language": anchor.code,
            "aligned_language": language_code,
            "drift_score": entry.drift_score,
            "drift_level": entry.drift_level.value if entry.drift_level else None,
            "affected_clauses": entry.affected_clauses,
            "canonical_terms_involved": entry.affected_terms,
            "validator_action": self.get_validator_action(entry.drift_level).value if entry.drift_level else None,
            "violations": [v.value for v in entry.violations]
        }

    def generate_alignment_spec(
        self,
        contract: MultilingualContract
    ) -> dict[str, Any]:
        """
        Generate machine-readable multilingual alignment spec.

        Per NCIP-003 Section 10, validators MUST support this structure.
        """
        languages = []
        for code, entry in contract.languages.items():
            languages.append({
                "code": code,
                "role": entry.role.value,
                "drift_tolerance": entry.drift_tolerance
            })

        return {
            "multilingual_semantics": {
                "version": "1.0",
                "canonical_anchor_language": contract.canonical_anchor_language,
                "languages": languages,
                "alignment_rules": contract.alignment_rules.to_dict(),
                "validator_actions": {
                    "on_drift": {
                        "use_ncip_002_thresholds": True,
                        "log_language_pair": True,
                        "require_anchor_reference": True
                    }
                }
            }
        }

    # -------------------------------------------------------------------------
    # Status and Queries
    # -------------------------------------------------------------------------

    def get_status_summary(self) -> dict[str, Any]:
        """Get summary of multilingual alignment system status."""
        contracts_by_csal: dict[str, int] = {}
        total_languages = 0
        aligned_count = 0
        informational_count = 0

        for contract in self.contracts.values():
            csal = contract.canonical_anchor_language
            contracts_by_csal[csal] = contracts_by_csal.get(csal, 0) + 1

            for entry in contract.languages.values():
                total_languages += 1
                if entry.role == LanguageRole.ALIGNED:
                    aligned_count += 1
                elif entry.role == LanguageRole.INFORMATIONAL:
                    informational_count += 1

        return {
            "total_contracts": len(self.contracts),
            "contracts_by_csal": contracts_by_csal,
            "total_language_entries": total_languages,
            "aligned_languages": aligned_count,
            "informational_languages": informational_count,
            "term_mappings": len(self.term_registry),
            "supported_languages": list(SUPPORTED_LANGUAGE_CODES),
            "drift_thresholds": {
                level.value: f"{low:.2f}-{high:.2f}"
                for level, (low, high) in self.DRIFT_THRESHOLDS.items()
            }
        }

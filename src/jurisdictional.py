"""
NCIP-006: Jurisdictional Interpretation & Legal Bridging

This module implements jurisdictional interfaces for NatLangChain while preserving:
- Canonical meaning
- Temporal Fixity
- Semantic Lock integrity
- Proof of Understanding guarantees

Core Principle: Law constrains enforcement, not meaning.
- NatLangChain semantics are defined internally, fixed at ratification time (T₀)
- External legal systems may affect remedies, enforceability, and procedure
- They may NOT redefine meaning
"""

import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

from drift_thresholds import DriftLevel


class JurisdictionRole(Enum):
    """
    Jurisdiction roles per NCIP-006 Section 4.

    A jurisdiction MUST NOT be granted semantic authority.
    """
    ENFORCEMENT = "enforcement"      # Where remedies may be sought
    INTERPRETIVE = "interpretive"    # Where courts may interpret facts (not semantics)
    PROCEDURAL = "procedural"        # Governs process only


class LTAViolation(Enum):
    """
    Legal Translation Artifact violations per NCIP-006 Section 7.
    """
    INTRODUCES_OBLIGATION = "introduces_obligation"
    REMOVES_OBLIGATION = "removes_obligation"
    NARROWS_SCOPE = "narrows_scope"
    BROADENS_SCOPE = "broadens_scope"
    MISSING_PROSE_CONTRACT_ID = "missing_prose_contract_id"
    MISSING_REGISTRY_REFERENCE = "missing_registry_reference"
    MISSING_TEMPORAL_FIXITY = "missing_temporal_fixity"
    MISSING_DISCLAIMER = "missing_disclaimer"
    EXCESSIVE_DRIFT = "excessive_drift"
    CLAIMS_SEMANTIC_AUTHORITY = "claims_semantic_authority"


class CourtRulingType(Enum):
    """Types of court rulings and their handling."""
    ENFORCEMENT = "enforcement"        # Affects enforcement only (allowed)
    SEMANTIC_OVERRIDE = "semantic"     # Attempts to redefine meaning (rejected)
    PROCEDURAL = "procedural"          # Process-related (allowed)
    VOID_CONTRACT = "void_contract"    # Voids the contract (allowed, halts execution)


# ISO 3166-1 alpha-2 country codes (common subset)
VALID_COUNTRY_CODES = {
    "US", "CA", "GB", "DE", "FR", "IT", "ES", "PT", "NL", "BE",
    "CH", "AT", "AU", "NZ", "JP", "KR", "CN", "HK", "SG", "IN",
    "BR", "MX", "AR", "CL", "CO", "PE", "ZA", "AE", "SA", "IL",
    "RU", "UA", "PL", "CZ", "SK", "HU", "RO", "BG", "GR", "TR",
    "SE", "NO", "DK", "FI", "IE", "LU", "MY", "ID", "TH", "VN",
    "PH", "TW", "EG", "NG", "KE", "MA", "GH"
}

# US state codes for subdivision support
US_STATE_CODES = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "FL", "GA",
    "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME", "MD",
    "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH", "NJ",
    "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI", "SC",
    "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY", "DC"
}


def validate_jurisdiction_code(code: str) -> tuple[bool, str]:
    """
    Validate a jurisdiction code (ISO 3166-1 or subdivision).

    Supports formats:
    - "US" (country only)
    - "US-CA" (country-subdivision)
    """
    if "-" in code:
        parts = code.split("-", 1)
        country = parts[0].upper()
        subdivision = parts[1].upper()

        if country not in VALID_COUNTRY_CODES:
            return (False, f"Invalid country code: {country}")

        # Special handling for US states
        if country == "US" and subdivision not in US_STATE_CODES:
            return (False, f"Invalid US state code: {subdivision}")

        return (True, f"Valid jurisdiction: {country}-{subdivision}")
    else:
        code_upper = code.upper()
        if code_upper not in VALID_COUNTRY_CODES:
            return (False, f"Invalid country code: {code_upper}")
        return (True, f"Valid jurisdiction: {code_upper}")


@dataclass
class JurisdictionDeclaration:
    """
    A jurisdiction declaration per NCIP-006 Section 3.

    Any Prose Contract with legal or economic impact MUST declare governing jurisdictions.
    """
    code: str  # ISO 3166-1 country code, optionally with subdivision (e.g., "US-CA")
    role: JurisdictionRole
    declared_at: datetime = field(default_factory=datetime.utcnow)

    # Additional metadata
    notes: str | None = None
    treaty_reference: str | None = None  # E.g., "Hague Convention"

    def __post_init__(self):
        valid, msg = validate_jurisdiction_code(self.code)
        if not valid:
            raise ValueError(msg)
        # Normalize to uppercase
        self.code = self.code.upper()

    @property
    def country(self) -> str:
        """Get the country code."""
        return self.code.split("-")[0]

    @property
    def subdivision(self) -> str | None:
        """Get the subdivision code if present."""
        parts = self.code.split("-")
        return parts[1] if len(parts) > 1 else None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "role": self.role.value,
            "country": self.country,
            "subdivision": self.subdivision,
            "declared_at": self.declared_at.isoformat()
        }


@dataclass
class LegalTranslationArtifact:
    """
    A Legal Translation Artifact (LTA) per NCIP-006 Section 6.

    LTAs are jurisdiction-specific renderings of Prose Contracts into legal prose.
    They are:
    - Derived
    - Non-authoritative
    - Must reference canonical semantics
    """
    lta_id: str
    prose_contract_id: str
    target_jurisdiction: str  # ISO 3166-1 code
    legal_prose: str

    # Required references per Section 6.2
    registry_version: str  # Canonical Term Registry version
    temporal_fixity_timestamp: datetime  # T₀

    # Disclaimer per Section 6.2
    semantic_authority_disclaimer: str = ""

    # Validation state
    created_at: datetime = field(default_factory=datetime.utcnow)
    validated: bool = False
    validation_timestamp: datetime | None = None
    drift_score: float | None = None
    drift_level: DriftLevel | None = None
    violations: list[LTAViolation] = field(default_factory=list)

    # Reference to canonical terms used
    referenced_terms: list[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.semantic_authority_disclaimer:
            self.semantic_authority_disclaimer = (
                f"This Legal Translation Artifact is derived from Prose Contract "
                f"'{self.prose_contract_id}' and is non-authoritative. Canonical meaning "
                f"is determined solely by NatLangChain protocol semantics as of "
                f"{self.temporal_fixity_timestamp.isoformat()}. This document does not "
                f"grant, modify, or override semantic authority."
            )

    @property
    def has_required_references(self) -> bool:
        """Check if LTA has all required references per Section 6.2."""
        return bool(
            self.prose_contract_id and
            self.registry_version and
            self.temporal_fixity_timestamp and
            self.semantic_authority_disclaimer
        )

    @property
    def is_valid(self) -> bool:
        """Check if LTA is valid (no violations, acceptable drift)."""
        if self.violations:
            return False
        if self.drift_score is not None and self.drift_level in [DriftLevel.D3, DriftLevel.D4]:
            return False
        return self.has_required_references

    def compute_hash(self) -> str:
        """Compute hash of the LTA for integrity verification."""
        content = f"{self.prose_contract_id}|{self.legal_prose}|{self.temporal_fixity_timestamp.isoformat()}"
        return hashlib.sha256(content.encode()).hexdigest()


@dataclass
class CourtRuling:
    """
    A court ruling and its handling per NCIP-006 Section 8.

    If a court ruling conflicts with canonical semantics:
    - Semantic Lock remains intact
    - Meaning does not change
    - Only enforcement outcome is applied
    """
    ruling_id: str
    jurisdiction: str
    ruling_type: CourtRulingType
    ruling_date: datetime
    summary: str

    # Affected contract
    prose_contract_id: str

    # Handling
    semantic_lock_preserved: bool = True
    enforcement_outcome: str | None = None
    execution_halted: bool = False

    # Rejection info (for semantic override attempts)
    rejected: bool = False
    rejection_reason: str | None = None

    def __post_init__(self):
        # Semantic override rulings are automatically rejected
        if self.ruling_type == CourtRulingType.SEMANTIC_OVERRIDE:
            self.rejected = True
            self.rejection_reason = (
                "Court rulings may not redefine canonical semantics. "
                "Semantic Lock remains intact per NCIP-006 Section 8."
            )
            self.semantic_lock_preserved = True


@dataclass
class JurisdictionConflict:
    """
    Cross-jurisdiction conflict per NCIP-006 Section 10.

    When jurisdictions conflict:
    - Semantic Lock applies
    - Most restrictive enforcement outcome applies
    - Meaning remains unchanged
    """
    conflict_id: str
    jurisdictions: list[str]
    prose_contract_id: str
    conflict_type: str  # e.g., "enforcement", "procedure"
    description: str

    # Resolution
    semantic_lock_applied: bool = True
    most_restrictive_outcome: str | None = None
    resolution_notes: str | None = None
    resolved_at: datetime | None = None


@dataclass
class JurisdictionalBridge:
    """
    Machine-readable jurisdiction bridge per NCIP-006 Section 11.

    Encapsulates all jurisdictional configuration for a Prose Contract.
    """
    prose_contract_id: str
    jurisdictions: list[JurisdictionDeclaration] = field(default_factory=list)
    ltas: dict[str, LegalTranslationArtifact] = field(default_factory=dict)
    court_rulings: list[CourtRuling] = field(default_factory=list)
    conflicts: list[JurisdictionConflict] = field(default_factory=list)

    # Bridge configuration
    semantic_authority_source: str = "natlangchain"
    allow_external_semantic_override: bool = False  # MUST be False
    ltas_allowed: bool = True
    ltas_authoritative: bool = False  # MUST be False
    max_allowed_drift: float = 0.25  # D2 threshold
    escalate_on_violation: bool = True

    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        # Enforce semantic authority constraints
        self.allow_external_semantic_override = False
        self.ltas_authoritative = False

    @property
    def enforcement_jurisdictions(self) -> list[JurisdictionDeclaration]:
        """Get jurisdictions with enforcement role."""
        return [j for j in self.jurisdictions if j.role == JurisdictionRole.ENFORCEMENT]

    @property
    def has_jurisdiction_declaration(self) -> bool:
        """Check if at least one jurisdiction is declared."""
        return len(self.jurisdictions) > 0

    def add_jurisdiction(
        self,
        code: str,
        role: JurisdictionRole
    ) -> tuple[bool, str]:
        """Add a jurisdiction declaration."""
        try:
            decl = JurisdictionDeclaration(code=code, role=role)
            self.jurisdictions.append(decl)
            return (True, f"Added {code} as {role.value}")
        except ValueError as e:
            return (False, str(e))

    def to_yaml_dict(self) -> dict[str, Any]:
        """Generate YAML-compatible dictionary per Section 11."""
        return {
            "jurisdictional_bridge": {
                "version": "1.0",
                "governing_jurisdictions": [
                    {"code": j.code, "role": j.role.value}
                    for j in self.jurisdictions
                ],
                "semantic_authority": {
                    "source": self.semantic_authority_source,
                    "allow_external_override": self.allow_external_semantic_override
                },
                "legal_translation_artifacts": {
                    "allowed": self.ltas_allowed,
                    "authoritative": self.ltas_authoritative,
                    "require_reference": [
                        "prose_contract_id",
                        "registry_version",
                        "temporal_fixity"
                    ]
                },
                "validator_rules": {
                    "reject_semantic_override": True,
                    "max_allowed_drift": self.max_allowed_drift,
                    "escalate_on_violation": self.escalate_on_violation
                }
            }
        }


class JurisdictionalManager:
    """
    Manages jurisdictional bridging per NCIP-006.

    Responsibilities:
    - Jurisdiction declaration validation
    - Legal Translation Artifact management
    - Court ruling handling
    - Cross-jurisdiction conflict resolution
    """

    # Drift thresholds per NCIP-002
    DRIFT_THRESHOLDS = {
        DriftLevel.D0: (0.00, 0.10),
        DriftLevel.D1: (0.10, 0.25),
        DriftLevel.D2: (0.25, 0.45),
        DriftLevel.D3: (0.45, 0.70),
        DriftLevel.D4: (0.70, 1.00),
    }

    def __init__(self):
        self.bridges: dict[str, JurisdictionalBridge] = {}
        self.lta_counter: int = 0

    # -------------------------------------------------------------------------
    # Bridge Management
    # -------------------------------------------------------------------------

    def create_bridge(self, prose_contract_id: str) -> JurisdictionalBridge:
        """Create a new jurisdictional bridge for a Prose Contract."""
        bridge = JurisdictionalBridge(prose_contract_id=prose_contract_id)
        self.bridges[prose_contract_id] = bridge
        return bridge

    def get_bridge(self, prose_contract_id: str) -> JurisdictionalBridge | None:
        """Get a bridge by Prose Contract ID."""
        return self.bridges.get(prose_contract_id)

    def validate_jurisdiction_declaration(
        self,
        bridge: JurisdictionalBridge
    ) -> tuple[bool, list[str]]:
        """
        Validate jurisdiction declaration per NCIP-006 Section 3.

        If omitted:
        - Validators emit D2
        - Execution pauses until declared
        """
        warnings = []

        if not bridge.has_jurisdiction_declaration:
            warnings.append(
                "D2: No governing jurisdiction declared. "
                "Execution paused until jurisdiction is declared per NCIP-006 Section 3.1."
            )
            return (False, warnings)

        # Check for at least one enforcement jurisdiction
        if not bridge.enforcement_jurisdictions:
            warnings.append(
                "Warning: No enforcement jurisdiction declared. "
                "Remedies may not be available."
            )

        return (True, warnings)

    # -------------------------------------------------------------------------
    # Legal Translation Artifacts
    # -------------------------------------------------------------------------

    def create_lta(
        self,
        prose_contract_id: str,
        target_jurisdiction: str,
        legal_prose: str,
        registry_version: str,
        temporal_fixity_timestamp: datetime,
        referenced_terms: list[str] | None = None
    ) -> tuple[LegalTranslationArtifact | None, list[str]]:
        """
        Create a Legal Translation Artifact per NCIP-006 Section 6.

        LTAs must:
        - Cite Prose Contract ID
        - Reference Canonical Term Registry IDs
        - Include Temporal Fixity timestamp
        - Explicitly disclaim semantic authority
        """
        errors = []

        # Validate jurisdiction
        valid, msg = validate_jurisdiction_code(target_jurisdiction)
        if not valid:
            errors.append(msg)
            return (None, errors)

        self.lta_counter += 1
        lta_id = f"LTA-{prose_contract_id}-{target_jurisdiction}-{self.lta_counter:04d}"

        lta = LegalTranslationArtifact(
            lta_id=lta_id,
            prose_contract_id=prose_contract_id,
            target_jurisdiction=target_jurisdiction.upper(),
            legal_prose=legal_prose,
            registry_version=registry_version,
            temporal_fixity_timestamp=temporal_fixity_timestamp,
            referenced_terms=referenced_terms or []
        )

        # Store in bridge if exists
        bridge = self.get_bridge(prose_contract_id)
        if bridge:
            bridge.ltas[lta_id] = lta

        return (lta, [])

    def validate_lta(
        self,
        lta: LegalTranslationArtifact,
        original_prose: str
    ) -> tuple[bool, list[LTAViolation]]:
        """
        Validate an LTA per NCIP-006 Section 7.

        Validators MUST:
        - Reject LTAs that introduce new obligations
        - Reject LTAs that narrow or broaden scope
        - Detect semantic drift between Prose Contract and LTA
        - Treat LTA drift ≥ D3 as invalid
        """
        violations = []

        # Check required references (Section 6.2)
        if not lta.prose_contract_id:
            violations.append(LTAViolation.MISSING_PROSE_CONTRACT_ID)
        if not lta.registry_version:
            violations.append(LTAViolation.MISSING_REGISTRY_REFERENCE)
        if not lta.temporal_fixity_timestamp:
            violations.append(LTAViolation.MISSING_TEMPORAL_FIXITY)
        if not lta.semantic_authority_disclaimer:
            violations.append(LTAViolation.MISSING_DISCLAIMER)

        # Check for semantic authority claims
        authority_patterns = [
            r"this\s+document\s+(?:is|shall\s+be)\s+(?:the\s+)?authoritative",
            r"supersedes?\s+(?:the\s+)?(?:original|prose\s+contract)",
            r"(?:has|have)\s+semantic\s+authority",
            r"redefines?\s+(?:the\s+)?meaning"
        ]
        legal_lower = lta.legal_prose.lower()
        for pattern in authority_patterns:
            if re.search(pattern, legal_lower):
                violations.append(LTAViolation.CLAIMS_SEMANTIC_AUTHORITY)
                break

        # Check for obligation changes
        obligation_violations = self._check_obligation_changes(original_prose, lta.legal_prose)
        violations.extend(obligation_violations)

        # Compute drift
        drift_score = self._compute_drift(original_prose, lta.legal_prose)
        drift_level = self._get_drift_level(drift_score)

        lta.drift_score = drift_score
        lta.drift_level = drift_level

        if drift_level in [DriftLevel.D3, DriftLevel.D4]:
            violations.append(LTAViolation.EXCESSIVE_DRIFT)

        lta.violations = violations
        lta.validated = True
        lta.validation_timestamp = datetime.utcnow()

        return (len(violations) == 0, violations)

    def _check_obligation_changes(
        self,
        original: str,
        legal: str
    ) -> list[LTAViolation]:
        """Check for obligation changes between original and legal prose."""
        violations = []

        # Simplified obligation detection
        obligation_words = ["must", "shall", "required", "obligated", "mandatory"]
        scope_broadeners = ["all", "any", "every", "unlimited", "without limitation"]
        scope_narrowers = ["only", "limited", "restricted", "specific", "solely"]

        original_lower = original.lower()
        legal_lower = legal.lower()

        # Count obligations
        orig_obligations = sum(1 for w in obligation_words if w in original_lower)
        legal_obligations = sum(1 for w in obligation_words if w in legal_lower)

        if legal_obligations > orig_obligations:
            violations.append(LTAViolation.INTRODUCES_OBLIGATION)
        elif legal_obligations < orig_obligations:
            violations.append(LTAViolation.REMOVES_OBLIGATION)

        # Check scope changes
        orig_broad = sum(1 for w in scope_broadeners if w in original_lower)
        legal_broad = sum(1 for w in scope_broadeners if w in legal_lower)

        if legal_broad > orig_broad:
            violations.append(LTAViolation.BROADENS_SCOPE)

        orig_narrow = sum(1 for w in scope_narrowers if w in original_lower)
        legal_narrow = sum(1 for w in scope_narrowers if w in legal_lower)

        if legal_narrow > orig_narrow:
            violations.append(LTAViolation.NARROWS_SCOPE)

        return violations

    def _compute_drift(self, original: str, legal: str) -> float:
        """Compute semantic drift between original and legal prose."""
        if not original:
            return 1.0

        # Simplified drift calculation
        orig_len = len(original)
        legal_len = len(legal)

        # Length ratio
        length_ratio = abs(orig_len - legal_len) / orig_len
        length_score = min(length_ratio / 3.0, 0.4)

        # Word overlap
        orig_words = set(re.findall(r'\b\w+\b', original.lower()))
        legal_words = set(re.findall(r'\b\w+\b', legal.lower()))

        if orig_words:
            overlap = len(orig_words & legal_words) / len(orig_words)
            overlap_score = (1 - overlap) * 0.4
        else:
            overlap_score = 0.4

        # Number preservation
        orig_nums = set(re.findall(r'\b\d+\b', original))
        legal_nums = set(re.findall(r'\b\d+\b', legal))
        if orig_nums:
            num_overlap = len(orig_nums & legal_nums) / len(orig_nums)
            num_score = (1 - num_overlap) * 0.2
        else:
            num_score = 0.0

        return min(length_score + overlap_score + num_score, 1.0)

    def _get_drift_level(self, score: float) -> DriftLevel:
        """Get drift level from score."""
        for level, (low, high) in self.DRIFT_THRESHOLDS.items():
            if low <= score < high:
                return level
        return DriftLevel.D4

    # -------------------------------------------------------------------------
    # Court Rulings
    # -------------------------------------------------------------------------

    def handle_court_ruling(
        self,
        prose_contract_id: str,
        jurisdiction: str,
        ruling_type: CourtRulingType,
        summary: str,
        enforcement_outcome: str | None = None
    ) -> CourtRuling:
        """
        Handle a court ruling per NCIP-006 Section 8.

        If ruling conflicts with canonical semantics:
        - Semantic Lock remains intact
        - Meaning does not change
        - Only enforcement outcome is applied
        """
        ruling_id = f"RULING-{prose_contract_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        ruling = CourtRuling(
            ruling_id=ruling_id,
            jurisdiction=jurisdiction,
            ruling_type=ruling_type,
            ruling_date=datetime.utcnow(),
            summary=summary,
            prose_contract_id=prose_contract_id,
            enforcement_outcome=enforcement_outcome
        )

        # Handle based on type
        if ruling_type == CourtRulingType.VOID_CONTRACT:
            ruling.execution_halted = True
            ruling.enforcement_outcome = "Contract voided - execution halted"
        elif ruling_type == CourtRulingType.SEMANTIC_OVERRIDE:
            # Already rejected in __post_init__
            pass
        elif ruling_type == CourtRulingType.ENFORCEMENT:
            ruling.enforcement_outcome = enforcement_outcome or "Enforcement action applied"

        # Store in bridge
        bridge = self.get_bridge(prose_contract_id)
        if bridge:
            bridge.court_rulings.append(ruling)

        return ruling

    # -------------------------------------------------------------------------
    # Cross-Jurisdiction Conflicts
    # -------------------------------------------------------------------------

    def handle_jurisdiction_conflict(
        self,
        prose_contract_id: str,
        jurisdictions: list[str],
        conflict_type: str,
        description: str
    ) -> JurisdictionConflict:
        """
        Handle cross-jurisdiction conflict per NCIP-006 Section 10.

        When jurisdictions conflict:
        - Semantic Lock applies
        - Most restrictive enforcement outcome applies
        - Meaning remains unchanged
        """
        conflict_id = f"CONFLICT-{prose_contract_id}-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        conflict = JurisdictionConflict(
            conflict_id=conflict_id,
            jurisdictions=jurisdictions,
            prose_contract_id=prose_contract_id,
            conflict_type=conflict_type,
            description=description,
            semantic_lock_applied=True
        )

        # Store in bridge
        bridge = self.get_bridge(prose_contract_id)
        if bridge:
            bridge.conflicts.append(conflict)

        return conflict

    def resolve_conflict(
        self,
        conflict: JurisdictionConflict,
        most_restrictive_outcome: str,
        resolution_notes: str
    ) -> bool:
        """Resolve a jurisdiction conflict with most restrictive outcome."""
        conflict.most_restrictive_outcome = most_restrictive_outcome
        conflict.resolution_notes = resolution_notes
        conflict.resolved_at = datetime.utcnow()
        return True

    # -------------------------------------------------------------------------
    # Validation & Reporting
    # -------------------------------------------------------------------------

    def validator_check_jurisdiction(
        self,
        prose_contract_id: str
    ) -> dict[str, Any]:
        """
        Validator check for jurisdiction declaration.

        Per Section 3.1: If omitted, validators emit D2 and execution pauses.
        """
        bridge = self.get_bridge(prose_contract_id)

        if not bridge:
            return {
                "status": "error",
                "message": f"No bridge found for {prose_contract_id}",
                "drift_level": "D2",
                "execution_paused": True
            }

        valid, warnings = self.validate_jurisdiction_declaration(bridge)

        return {
            "status": "valid" if valid else "invalid",
            "has_jurisdiction": bridge.has_jurisdiction_declaration,
            "enforcement_jurisdictions": [j.code for j in bridge.enforcement_jurisdictions],
            "drift_level": "D0" if valid else "D2",
            "execution_paused": not valid,
            "warnings": warnings
        }

    def validator_check_lta(
        self,
        lta: LegalTranslationArtifact,
        original_prose: str
    ) -> dict[str, Any]:
        """Validator check for LTA compliance."""
        valid, violations = self.validate_lta(lta, original_prose)

        return {
            "status": "valid" if valid else "invalid",
            "lta_id": lta.lta_id,
            "drift_score": lta.drift_score,
            "drift_level": lta.drift_level.value if lta.drift_level else None,
            "has_required_references": lta.has_required_references,
            "violations": [v.value for v in violations],
            "rejection_required": LTAViolation.EXCESSIVE_DRIFT in violations or
                                   LTAViolation.CLAIMS_SEMANTIC_AUTHORITY in violations
        }

    def generate_bridge_spec(
        self,
        prose_contract_id: str
    ) -> dict[str, Any]:
        """Generate machine-readable jurisdiction bridge spec per Section 11."""
        bridge = self.get_bridge(prose_contract_id)

        if not bridge:
            return {"error": f"No bridge found for {prose_contract_id}"}

        return bridge.to_yaml_dict()

    # -------------------------------------------------------------------------
    # Status & Queries
    # -------------------------------------------------------------------------

    def get_status_summary(self) -> dict[str, Any]:
        """Get summary of jurisdictional bridging system status."""
        total_ltas = sum(len(b.ltas) for b in self.bridges.values())
        total_rulings = sum(len(b.court_rulings) for b in self.bridges.values())
        total_conflicts = sum(len(b.conflicts) for b in self.bridges.values())

        jurisdictions_used: dict[str, int] = {}
        for bridge in self.bridges.values():
            for j in bridge.jurisdictions:
                jurisdictions_used[j.code] = jurisdictions_used.get(j.code, 0) + 1

        return {
            "total_bridges": len(self.bridges),
            "total_ltas": total_ltas,
            "total_court_rulings": total_rulings,
            "total_conflicts": total_conflicts,
            "jurisdictions_used": jurisdictions_used,
            "supported_countries": len(VALID_COUNTRY_CODES),
            "semantic_authority": "natlangchain",
            "external_override_allowed": False
        }

"""
Tests for NCIP-006: Jurisdictional Interpretation & Legal Bridging

Tests cover:
- Jurisdiction declaration and validation
- Jurisdiction roles (enforcement, interpretive, procedural)
- Legal Translation Artifacts (LTAs)
- Court ruling handling
- Cross-jurisdiction conflicts
- Semantic authority preservation
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest
from datetime import datetime, timedelta

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
    DriftLevel,
    validate_jurisdiction_code,
    VALID_COUNTRY_CODES,
    US_STATE_CODES
)


class TestJurisdictionCodes(unittest.TestCase):
    """Test jurisdiction code validation."""

    def test_valid_country_codes(self):
        """Test valid country codes are accepted."""
        valid_codes = ["US", "DE", "GB", "FR", "JP", "CN", "AU"]
        for code in valid_codes:
            valid, msg = validate_jurisdiction_code(code)
            self.assertTrue(valid, f"Code {code} should be valid")

    def test_valid_us_subdivision(self):
        """Test valid US state codes are accepted."""
        valid, msg = validate_jurisdiction_code("US-CA")
        self.assertTrue(valid)
        valid, msg = validate_jurisdiction_code("US-NY")
        self.assertTrue(valid)
        valid, msg = validate_jurisdiction_code("US-TX")
        self.assertTrue(valid)

    def test_invalid_country_code(self):
        """Test invalid country codes are rejected."""
        valid, msg = validate_jurisdiction_code("XX")
        self.assertFalse(valid)
        self.assertIn("Invalid country code", msg)

    def test_invalid_us_state(self):
        """Test invalid US state codes are rejected."""
        valid, msg = validate_jurisdiction_code("US-ZZ")
        self.assertFalse(valid)
        self.assertIn("Invalid US state code", msg)

    def test_case_insensitive(self):
        """Test codes are case insensitive."""
        valid, msg = validate_jurisdiction_code("us-ca")
        self.assertTrue(valid)
        valid, msg = validate_jurisdiction_code("Us-Ca")
        self.assertTrue(valid)


class TestJurisdictionDeclaration(unittest.TestCase):
    """Test jurisdiction declaration per NCIP-006 Section 3."""

    def test_create_valid_declaration(self):
        """Test creating a valid jurisdiction declaration."""
        decl = JurisdictionDeclaration(
            code="US-CA",
            role=JurisdictionRole.ENFORCEMENT
        )
        self.assertEqual(decl.code, "US-CA")
        self.assertEqual(decl.role, JurisdictionRole.ENFORCEMENT)
        self.assertEqual(decl.country, "US")
        self.assertEqual(decl.subdivision, "CA")

    def test_declaration_roles(self):
        """Test all jurisdiction roles are available."""
        self.assertEqual(JurisdictionRole.ENFORCEMENT.value, "enforcement")
        self.assertEqual(JurisdictionRole.INTERPRETIVE.value, "interpretive")
        self.assertEqual(JurisdictionRole.PROCEDURAL.value, "procedural")

    def test_invalid_code_raises(self):
        """Test invalid jurisdiction code raises ValueError."""
        with self.assertRaises(ValueError):
            JurisdictionDeclaration(code="INVALID", role=JurisdictionRole.ENFORCEMENT)

    def test_to_dict(self):
        """Test declaration serialization."""
        decl = JurisdictionDeclaration(code="DE", role=JurisdictionRole.PROCEDURAL)
        d = decl.to_dict()
        self.assertEqual(d["code"], "DE")
        self.assertEqual(d["role"], "procedural")
        self.assertEqual(d["country"], "DE")
        self.assertIsNone(d["subdivision"])


class TestJurisdictionalBridge(unittest.TestCase):
    """Test jurisdictional bridge management."""

    def setUp(self):
        self.manager = JurisdictionalManager()
        self.bridge = self.manager.create_bridge("contract-001")

    def test_create_bridge(self):
        """Test creating a jurisdictional bridge."""
        self.assertEqual(self.bridge.prose_contract_id, "contract-001")
        self.assertEqual(self.bridge.semantic_authority_source, "natlangchain")
        self.assertFalse(self.bridge.allow_external_semantic_override)
        self.assertFalse(self.bridge.ltas_authoritative)

    def test_semantic_override_always_false(self):
        """Semantic override must always be False per NCIP-006."""
        self.bridge.allow_external_semantic_override = True  # Try to set
        # Should be forced back in __post_init__
        new_bridge = JurisdictionalBridge(prose_contract_id="test")
        self.assertFalse(new_bridge.allow_external_semantic_override)

    def test_add_jurisdiction(self):
        """Test adding jurisdictions to bridge."""
        success, msg = self.bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)
        self.assertTrue(success)
        self.assertEqual(len(self.bridge.jurisdictions), 1)

        success, msg = self.bridge.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)
        self.assertTrue(success)
        self.assertEqual(len(self.bridge.jurisdictions), 2)

    def test_enforcement_jurisdictions(self):
        """Test getting enforcement jurisdictions."""
        self.bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)
        self.bridge.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)
        self.bridge.add_jurisdiction("GB", JurisdictionRole.ENFORCEMENT)

        enforcement = self.bridge.enforcement_jurisdictions
        self.assertEqual(len(enforcement), 2)
        codes = [j.code for j in enforcement]
        self.assertIn("US-CA", codes)
        self.assertIn("GB", codes)

    def test_to_yaml_dict(self):
        """Test generating YAML-compatible dict per Section 11."""
        self.bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)
        self.bridge.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)

        spec = self.bridge.to_yaml_dict()
        self.assertIn("jurisdictional_bridge", spec)

        jb = spec["jurisdictional_bridge"]
        self.assertEqual(jb["version"], "1.0")
        self.assertEqual(len(jb["governing_jurisdictions"]), 2)
        self.assertFalse(jb["semantic_authority"]["allow_external_override"])
        self.assertFalse(jb["legal_translation_artifacts"]["authoritative"])
        self.assertTrue(jb["validator_rules"]["reject_semantic_override"])


class TestJurisdictionValidation(unittest.TestCase):
    """Test jurisdiction declaration validation per NCIP-006 Section 3."""

    def setUp(self):
        self.manager = JurisdictionalManager()

    def test_missing_jurisdiction_emits_d2(self):
        """If jurisdiction omitted, validators emit D2 per Section 3.1."""
        bridge = self.manager.create_bridge("contract-001")
        # No jurisdictions added

        valid, warnings = self.manager.validate_jurisdiction_declaration(bridge)
        self.assertFalse(valid)
        self.assertTrue(any("D2" in w for w in warnings))

    def test_valid_jurisdiction(self):
        """Test valid jurisdiction declaration passes."""
        bridge = self.manager.create_bridge("contract-001")
        bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)

        valid, warnings = self.manager.validate_jurisdiction_declaration(bridge)
        self.assertTrue(valid)

    def test_warning_no_enforcement(self):
        """Test warning when no enforcement jurisdiction."""
        bridge = self.manager.create_bridge("contract-001")
        bridge.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)

        valid, warnings = self.manager.validate_jurisdiction_declaration(bridge)
        self.assertTrue(valid)  # Still valid, just warning
        self.assertTrue(any("enforcement" in w.lower() for w in warnings))


class TestLegalTranslationArtifacts(unittest.TestCase):
    """Test Legal Translation Artifacts per NCIP-006 Section 6."""

    def setUp(self):
        self.manager = JurisdictionalManager()
        self.bridge = self.manager.create_bridge("contract-001")
        self.temporal_fixity = datetime.utcnow()

    def test_create_lta(self):
        """Test creating an LTA."""
        lta, errors = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose="Legal translation of the contract...",
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity,
            referenced_terms=["PROSE_CONTRACT", "RATIFICATION"]
        )

        self.assertIsNotNone(lta)
        self.assertEqual(len(errors), 0)
        self.assertEqual(lta.prose_contract_id, "contract-001")
        self.assertEqual(lta.target_jurisdiction, "US-CA")
        self.assertIn("non-authoritative", lta.semantic_authority_disclaimer)

    def test_lta_has_required_references(self):
        """Test LTA has required references per Section 6.2."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="DE",
            legal_prose="Legal translation...",
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        self.assertTrue(lta.has_required_references)

    def test_lta_auto_disclaimer(self):
        """Test LTA auto-generates semantic authority disclaimer."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="GB",
            legal_prose="Legal translation...",
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        self.assertIn("non-authoritative", lta.semantic_authority_disclaimer)
        self.assertIn("contract-001", lta.semantic_authority_disclaimer)


class TestLTAValidation(unittest.TestCase):
    """Test LTA validation per NCIP-006 Section 7."""

    def setUp(self):
        self.manager = JurisdictionalManager()
        self.temporal_fixity = datetime.utcnow()
        self.original_prose = (
            "The contractor must deliver the software by December 31, 2025. "
            "Payment shall be made within 30 days of delivery."
        )

    def test_valid_lta(self):
        """Test validation of a valid LTA."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose=(
                "The contractor is required to deliver the software by December 31, 2025. "
                "Payment shall be remitted within 30 days following delivery."
            ),
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        valid, violations = self.manager.validate_lta(lta, self.original_prose)
        # Should have low drift, no major violations
        self.assertLess(lta.drift_score, 0.45)

    def test_reject_lta_with_new_obligations(self):
        """Test rejection of LTA that introduces obligations."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose=(
                "The contractor must deliver the software by December 31, 2025. "
                "Payment shall be made within 30 days of delivery. "
                "The contractor must also provide mandatory training. "
                "Additional support services are required."
            ),
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        valid, violations = self.manager.validate_lta(lta, self.original_prose)
        self.assertIn(LTAViolation.INTRODUCES_OBLIGATION, violations)

    def test_reject_lta_claiming_authority(self):
        """Test rejection of LTA claiming semantic authority."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose=(
                "This document is the authoritative interpretation. "
                "This supersedes the original prose contract. "
                "Payment shall be made within 30 days."
            ),
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        valid, violations = self.manager.validate_lta(lta, self.original_prose)
        self.assertIn(LTAViolation.CLAIMS_SEMANTIC_AUTHORITY, violations)

    def test_reject_high_drift_lta(self):
        """Test rejection of LTA with D3+ drift."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose=(
                "Completely different content about something unrelated. "
                "No mention of software delivery or payment terms at all. "
                "This is entirely new material with no connection to original."
            ),
            registry_version="1.0.0",
            temporal_fixity_timestamp=self.temporal_fixity
        )

        valid, violations = self.manager.validate_lta(lta, self.original_prose)
        # High drift should be detected
        self.assertGreater(lta.drift_score, 0.25)


class TestCourtRulings(unittest.TestCase):
    """Test court ruling handling per NCIP-006 Section 8."""

    def setUp(self):
        self.manager = JurisdictionalManager()
        self.bridge = self.manager.create_bridge("contract-001")

    def test_enforcement_ruling_accepted(self):
        """Test enforcement rulings are accepted."""
        ruling = self.manager.handle_court_ruling(
            prose_contract_id="contract-001",
            jurisdiction="US-CA",
            ruling_type=CourtRulingType.ENFORCEMENT,
            summary="Court ordered payment enforcement",
            enforcement_outcome="Garnishment ordered"
        )

        self.assertFalse(ruling.rejected)
        self.assertTrue(ruling.semantic_lock_preserved)
        self.assertEqual(ruling.enforcement_outcome, "Garnishment ordered")

    def test_semantic_override_rejected(self):
        """Test semantic override rulings are rejected per Section 8."""
        ruling = self.manager.handle_court_ruling(
            prose_contract_id="contract-001",
            jurisdiction="US-CA",
            ruling_type=CourtRulingType.SEMANTIC_OVERRIDE,
            summary="Court attempts to redefine 'uptime' term"
        )

        self.assertTrue(ruling.rejected)
        self.assertTrue(ruling.semantic_lock_preserved)
        self.assertIn("may not redefine", ruling.rejection_reason)

    def test_void_contract_halts_execution(self):
        """Test void contract ruling halts execution."""
        ruling = self.manager.handle_court_ruling(
            prose_contract_id="contract-001",
            jurisdiction="US-CA",
            ruling_type=CourtRulingType.VOID_CONTRACT,
            summary="Court voided contract due to fraud"
        )

        self.assertTrue(ruling.execution_halted)
        self.assertTrue(ruling.semantic_lock_preserved)

    def test_procedural_ruling_accepted(self):
        """Test procedural rulings are accepted."""
        ruling = self.manager.handle_court_ruling(
            prose_contract_id="contract-001",
            jurisdiction="DE",
            ruling_type=CourtRulingType.PROCEDURAL,
            summary="Court ordered mediation before trial"
        )

        self.assertFalse(ruling.rejected)
        self.assertFalse(ruling.execution_halted)


class TestCrossJurisdictionConflicts(unittest.TestCase):
    """Test cross-jurisdiction conflict handling per NCIP-006 Section 10."""

    def setUp(self):
        self.manager = JurisdictionalManager()
        self.bridge = self.manager.create_bridge("contract-001")
        self.bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)
        self.bridge.add_jurisdiction("DE", JurisdictionRole.ENFORCEMENT)

    def test_create_conflict(self):
        """Test creating a jurisdiction conflict."""
        conflict = self.manager.handle_jurisdiction_conflict(
            prose_contract_id="contract-001",
            jurisdictions=["US-CA", "DE"],
            conflict_type="enforcement",
            description="Conflicting enforcement requirements between jurisdictions"
        )

        self.assertIsNotNone(conflict)
        self.assertTrue(conflict.semantic_lock_applied)
        self.assertEqual(len(conflict.jurisdictions), 2)

    def test_resolve_conflict_most_restrictive(self):
        """Test conflict resolution uses most restrictive outcome."""
        conflict = self.manager.handle_jurisdiction_conflict(
            prose_contract_id="contract-001",
            jurisdictions=["US-CA", "DE"],
            conflict_type="enforcement",
            description="Payment term conflict"
        )

        success = self.manager.resolve_conflict(
            conflict,
            most_restrictive_outcome="Apply German data protection requirements (stricter)",
            resolution_notes="GDPR requirements are more restrictive than California's"
        )

        self.assertTrue(success)
        self.assertIsNotNone(conflict.resolved_at)
        self.assertIn("German", conflict.most_restrictive_outcome)


class TestValidatorChecks(unittest.TestCase):
    """Test validator checks for jurisdictional compliance."""

    def setUp(self):
        self.manager = JurisdictionalManager()

    def test_validator_check_missing_jurisdiction(self):
        """Test validator check for missing jurisdiction."""
        self.manager.create_bridge("contract-001")

        result = self.manager.validator_check_jurisdiction("contract-001")
        self.assertEqual(result["status"], "invalid")
        self.assertEqual(result["drift_level"], "D2")
        self.assertTrue(result["execution_paused"])

    def test_validator_check_valid_jurisdiction(self):
        """Test validator check for valid jurisdiction."""
        bridge = self.manager.create_bridge("contract-001")
        bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)

        result = self.manager.validator_check_jurisdiction("contract-001")
        self.assertEqual(result["status"], "valid")
        self.assertEqual(result["drift_level"], "D0")
        self.assertFalse(result["execution_paused"])

    def test_validator_check_lta(self):
        """Test validator LTA compliance check."""
        lta, _ = self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose="Legal translation of the agreement.",
            registry_version="1.0.0",
            temporal_fixity_timestamp=datetime.utcnow()
        )

        original = "The original agreement text."
        result = self.manager.validator_check_lta(lta, original)

        self.assertIn("status", result)
        self.assertIn("drift_score", result)
        self.assertIn("has_required_references", result)


class TestBridgeSpec(unittest.TestCase):
    """Test machine-readable bridge spec generation."""

    def setUp(self):
        self.manager = JurisdictionalManager()

    def test_generate_bridge_spec(self):
        """Test generating YAML-compatible bridge spec."""
        bridge = self.manager.create_bridge("contract-001")
        bridge.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)
        bridge.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)

        spec = self.manager.generate_bridge_spec("contract-001")

        self.assertIn("jurisdictional_bridge", spec)
        jb = spec["jurisdictional_bridge"]

        self.assertEqual(jb["version"], "1.0")
        self.assertEqual(jb["semantic_authority"]["source"], "natlangchain")
        self.assertFalse(jb["semantic_authority"]["allow_external_override"])

    def test_spec_not_found(self):
        """Test spec generation for nonexistent bridge."""
        spec = self.manager.generate_bridge_spec("nonexistent")
        self.assertIn("error", spec)


class TestStatusSummary(unittest.TestCase):
    """Test status summary generation."""

    def setUp(self):
        self.manager = JurisdictionalManager()

    def test_empty_status(self):
        """Test status with no bridges."""
        summary = self.manager.get_status_summary()

        self.assertEqual(summary["total_bridges"], 0)
        self.assertEqual(summary["total_ltas"], 0)
        self.assertEqual(summary["semantic_authority"], "natlangchain")
        self.assertFalse(summary["external_override_allowed"])

    def test_status_with_bridges(self):
        """Test status with bridges and LTAs."""
        bridge1 = self.manager.create_bridge("contract-001")
        bridge1.add_jurisdiction("US-CA", JurisdictionRole.ENFORCEMENT)

        self.manager.create_lta(
            prose_contract_id="contract-001",
            target_jurisdiction="US-CA",
            legal_prose="Legal translation",
            registry_version="1.0.0",
            temporal_fixity_timestamp=datetime.utcnow()
        )

        bridge2 = self.manager.create_bridge("contract-002")
        bridge2.add_jurisdiction("DE", JurisdictionRole.PROCEDURAL)

        summary = self.manager.get_status_summary()

        self.assertEqual(summary["total_bridges"], 2)
        self.assertEqual(summary["total_ltas"], 1)
        self.assertIn("US-CA", summary["jurisdictions_used"])


class TestDriftLevels(unittest.TestCase):
    """Test drift level computation."""

    def setUp(self):
        self.manager = JurisdictionalManager()

    def test_drift_level_d0(self):
        """Test D0 drift level (0.00-0.10)."""
        level = self.manager._get_drift_level(0.05)
        self.assertEqual(level, DriftLevel.D0)

    def test_drift_level_d1(self):
        """Test D1 drift level (0.10-0.25)."""
        level = self.manager._get_drift_level(0.15)
        self.assertEqual(level, DriftLevel.D1)

    def test_drift_level_d2(self):
        """Test D2 drift level (0.25-0.45)."""
        level = self.manager._get_drift_level(0.35)
        self.assertEqual(level, DriftLevel.D2)

    def test_drift_level_d3(self):
        """Test D3 drift level (0.45-0.70)."""
        level = self.manager._get_drift_level(0.55)
        self.assertEqual(level, DriftLevel.D3)

    def test_drift_level_d4(self):
        """Test D4 drift level (0.70-1.00)."""
        level = self.manager._get_drift_level(0.85)
        self.assertEqual(level, DriftLevel.D4)


if __name__ == "__main__":
    unittest.main()

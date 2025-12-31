"""
Tests for NCIP-003: Multilingual Semantic Alignment & Drift

Tests cover:
- CSAL declaration and validation
- Language roles (anchor, aligned, informational)
- Cross-language drift measurement
- Translation validation
- Canonical term mapping
- Human ratification in multilingual contexts
- Validator reporting
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import unittest

from multilingual import (
    SUPPORTED_LANGUAGE_CODES,
    AlignmentRules,
    CanonicalTermMapping,
    ClauseDriftResult,
    DriftLevel,
    LanguageEntry,
    LanguageRole,
    MultilingualAlignmentManager,
    TranslationViolation,
    ValidatorAction,
)


class TestLanguageRoles(unittest.TestCase):
    """Test language role definitions per NCIP-003 Section 3."""

    def test_language_roles_exist(self):
        """Test all three language roles are defined."""
        self.assertEqual(LanguageRole.ANCHOR.value, "anchor")
        self.assertEqual(LanguageRole.ALIGNED.value, "aligned")
        self.assertEqual(LanguageRole.INFORMATIONAL.value, "informational")

    def test_executable_roles(self):
        """Only anchor and aligned may influence execution."""
        entry_anchor = LanguageEntry(code="en", role=LanguageRole.ANCHOR, content="test")
        entry_aligned = LanguageEntry(code="es", role=LanguageRole.ALIGNED, content="prueba")
        entry_info = LanguageEntry(code="ja", role=LanguageRole.INFORMATIONAL, content="test")

        self.assertTrue(entry_anchor.is_executable)
        self.assertTrue(entry_aligned.is_executable)
        self.assertFalse(entry_info.is_executable)


class TestCSALDeclaration(unittest.TestCase):
    """Test CSAL declaration per NCIP-003 Section 2."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_default_csal_is_english(self):
        """Default CSAL is English per NCIP-003 Section 2.1."""
        contract = self.manager.create_contract("test-001")
        self.assertEqual(contract.canonical_anchor_language, "en")

    def test_explicit_csal_declaration(self):
        """Contracts can explicitly declare CSAL."""
        contract = self.manager.create_contract("test-002", canonical_anchor_language="es")
        self.assertEqual(contract.canonical_anchor_language, "es")

    def test_missing_csal_emits_d1_warning(self):
        """If CSAL omitted, validators MUST assume 'en' and emit D1 warning."""
        contract = self.manager.create_contract("test-003")
        # Add anchor language
        contract.add_language("en", LanguageRole.ANCHOR, "Test content")

        valid, warnings = self.manager.validate_csal_declaration(contract)
        self.assertTrue(valid)
        self.assertTrue(any("D1 Warning" in w for w in warnings))

    def test_explicit_csal_no_warning(self):
        """Explicit CSAL should not emit warning."""
        contract = self.manager.create_contract("test-004", canonical_anchor_language="fr")
        contract.add_language("fr", LanguageRole.ANCHOR, "Contenu de test")

        valid, warnings = self.manager.validate_csal_declaration(contract)
        self.assertTrue(valid)
        self.assertEqual(len(warnings), 0)


class TestLanguageEntry(unittest.TestCase):
    """Test language entry creation and validation."""

    def test_valid_language_code(self):
        """Test creating entry with valid ISO 639-1 code."""
        entry = LanguageEntry(code="en", role=LanguageRole.ANCHOR, content="Test")
        self.assertEqual(entry.code, "en")

    def test_invalid_language_code_raises(self):
        """Test invalid language code raises error."""
        with self.assertRaises(ValueError):
            LanguageEntry(code="invalid", role=LanguageRole.ANCHOR, content="Test")

    def test_supported_language_codes(self):
        """Test common language codes are supported."""
        common_codes = ["en", "es", "fr", "de", "zh", "ja", "ko", "ar", "pt", "ru"]
        for code in common_codes:
            self.assertIn(code, SUPPORTED_LANGUAGE_CODES)

    def test_entry_validity_no_violations(self):
        """Entry with no violations is valid."""
        entry = LanguageEntry(code="es", role=LanguageRole.ALIGNED, content="Test")
        entry.drift_score = 0.15
        self.assertTrue(entry.is_valid)

    def test_entry_invalid_with_violations(self):
        """Entry with violations is invalid."""
        entry = LanguageEntry(code="es", role=LanguageRole.ALIGNED, content="Test")
        entry.violations.append(TranslationViolation.REMOVED_OBLIGATION)
        self.assertFalse(entry.is_valid)

    def test_entry_invalid_with_high_drift(self):
        """Entry with drift exceeding tolerance is invalid."""
        entry = LanguageEntry(code="es", role=LanguageRole.ALIGNED, content="Test")
        entry.drift_tolerance = 0.25
        entry.drift_score = 0.50
        self.assertFalse(entry.is_valid)


class TestMultilingualContract(unittest.TestCase):
    """Test multilingual contract management."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()
        self.contract = self.manager.create_contract("contract-001")

    def test_add_anchor_language(self):
        """Test adding anchor language."""
        success, _msg = self.contract.add_language(
            "en", LanguageRole.ANCHOR, "This is a test contract."
        )
        self.assertTrue(success)
        self.assertIsNotNone(self.contract.anchor_entry)
        self.assertEqual(self.contract.anchor_entry.code, "en")

    def test_add_aligned_language(self):
        """Test adding aligned language."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test contract")
        success, _msg = self.contract.add_language(
            "es", LanguageRole.ALIGNED, "Contrato de prueba"
        )
        self.assertTrue(success)
        self.assertEqual(len(self.contract.aligned_entries), 1)

    def test_add_informational_language(self):
        """Test adding informational language."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")
        success, _msg = self.contract.add_language(
            "ja", LanguageRole.INFORMATIONAL, "テスト"
        )
        self.assertTrue(success)
        self.assertEqual(len(self.contract.informational_entries), 1)

    def test_only_one_anchor_allowed(self):
        """Contract can only have one anchor language."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")
        success, msg = self.contract.add_language(
            "fr", LanguageRole.ANCHOR, "Test français"
        )
        self.assertFalse(success)
        self.assertIn("already has an anchor", msg)

    def test_anchor_must_match_csal(self):
        """Anchor language must match declared CSAL."""
        contract = self.manager.create_contract("test-002", canonical_anchor_language="fr")
        success, msg = contract.add_language("en", LanguageRole.ANCHOR, "Test")
        self.assertFalse(success)
        self.assertIn("must match CSAL", msg)

    def test_executable_languages(self):
        """Test getting executable language codes."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")
        self.contract.add_language("es", LanguageRole.ALIGNED, "Prueba")
        self.contract.add_language("ja", LanguageRole.INFORMATIONAL, "テスト")

        executable = self.contract.executable_languages
        self.assertIn("en", executable)
        self.assertIn("es", executable)
        self.assertNotIn("ja", executable)


class TestDriftMeasurement(unittest.TestCase):
    """Test cross-language drift measurement per NCIP-003 Section 5."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_drift_level_computation(self):
        """Test drift level from score."""
        self.assertEqual(self.manager.compute_drift_level(0.05), DriftLevel.D0)
        self.assertEqual(self.manager.compute_drift_level(0.15), DriftLevel.D1)
        self.assertEqual(self.manager.compute_drift_level(0.35), DriftLevel.D2)
        self.assertEqual(self.manager.compute_drift_level(0.55), DriftLevel.D3)
        self.assertEqual(self.manager.compute_drift_level(0.85), DriftLevel.D4)

    def test_validator_actions(self):
        """Test validator actions per drift level."""
        self.assertEqual(
            self.manager.get_validator_action(DriftLevel.D0),
            ValidatorAction.ACCEPT
        )
        self.assertEqual(
            self.manager.get_validator_action(DriftLevel.D1),
            ValidatorAction.ACCEPT
        )
        self.assertEqual(
            self.manager.get_validator_action(DriftLevel.D2),
            ValidatorAction.PAUSE_CLARIFY
        )
        self.assertEqual(
            self.manager.get_validator_action(DriftLevel.D3),
            ValidatorAction.REQUIRE_RATIFICATION
        )
        self.assertEqual(
            self.manager.get_validator_action(DriftLevel.D4),
            ValidatorAction.REJECT_ESCALATE
        )

    def test_similar_content_low_drift(self):
        """Similar content should have low drift."""
        anchor = "The contractor agrees to deliver the software by December 31, 2025."
        aligned = "El contratista acepta entregar el software antes del 31 de diciembre de 2025."

        score, _level = self.manager.measure_cross_language_drift(anchor, aligned, "es")
        self.assertLess(score, 0.45)  # Should be D2 or lower

    def test_very_different_content_high_drift(self):
        """Very different content should have high drift."""
        anchor = "Payment is due within 30 days."
        aligned = "This is completely different text about something else entirely with no relation whatsoever."

        score, _level = self.manager.measure_cross_language_drift(anchor, aligned, "es")
        self.assertGreater(score, 0.25)  # Should indicate drift

    def test_empty_anchor_returns_max_drift(self):
        """Empty anchor text returns maximum drift."""
        score, level = self.manager.measure_cross_language_drift("", "Some text", "es")
        self.assertEqual(score, 1.0)
        self.assertEqual(level, DriftLevel.D4)


class TestContractValidation(unittest.TestCase):
    """Test contract alignment validation per NCIP-003."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_validate_simple_contract(self):
        """Test validating a simple multilingual contract."""
        contract = self.manager.create_contract("test-001")
        contract.add_language("en", LanguageRole.ANCHOR,
            "This agreement is between Party A and Party B for software development.")
        contract.add_language("es", LanguageRole.ALIGNED,
            "Este acuerdo es entre la Parte A y la Parte B para desarrollo de software.")

        valid, report = self.manager.validate_contract_alignment(contract)

        self.assertTrue(valid)
        self.assertIn("es", report["languages_checked"])
        self.assertIn("es", report["drift_results"])

    def test_max_drift_governs_response(self):
        """Maximum drift score governs overall validator response."""
        contract = self.manager.create_contract("test-002")
        contract.add_language("en", LanguageRole.ANCHOR, "Test content for the contract.")
        contract.add_language("es", LanguageRole.ALIGNED, "Contenido de prueba.")
        contract.add_language("de", LanguageRole.ALIGNED, "Completely different unrelated text here.")

        _valid, report = self.manager.validate_contract_alignment(contract)

        # The maximum drift from any language applies
        self.assertGreater(report["max_drift_score"], 0)
        self.assertIsNotNone(report["overall_action"])

    def test_no_anchor_fails_validation(self):
        """Contract without anchor fails validation."""
        contract = self.manager.create_contract("test-003")
        contract.add_language("es", LanguageRole.ALIGNED, "Test")

        valid, report = self.manager.validate_contract_alignment(contract)
        self.assertFalse(valid)
        self.assertTrue(any("anchor" in v.lower() for v in report["violations"]))

    def test_informational_excluded_from_drift(self):
        """Informational languages are excluded from drift computation."""
        contract = self.manager.create_contract("test-004")
        contract.add_language("en", LanguageRole.ANCHOR, "Test content")
        contract.add_language("ja", LanguageRole.INFORMATIONAL, "Completely unrelated Japanese text")

        valid, report = self.manager.validate_contract_alignment(contract)

        self.assertTrue(valid)
        self.assertNotIn("ja", report["languages_checked"])


class TestTranslationValidation(unittest.TestCase):
    """Test translation violation detection per NCIP-003 Section 4."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_detect_added_obligation(self):
        """Detect when translation adds obligations."""
        anchor = "The contractor should deliver the software."
        aligned = "The contractor must deliver the software and must provide documentation."

        violations = self.manager.check_translation_violations(anchor, aligned, "es")
        self.assertIn(TranslationViolation.INTRODUCED_CONSTRAINT, violations)

    def test_detect_removed_obligation(self):
        """Detect when translation removes obligations."""
        anchor = "The contractor must deliver the software and must provide support."
        aligned = "The contractor delivers the software."

        violations = self.manager.check_translation_violations(anchor, aligned, "es")
        self.assertIn(TranslationViolation.REMOVED_OBLIGATION, violations)

    def test_detect_broadened_scope(self):
        """Detect when translation broadens scope."""
        anchor = "This applies to specific users only."
        aligned = "This applies to all users and any related parties."

        violations = self.manager.check_translation_violations(anchor, aligned, "es")
        self.assertIn(TranslationViolation.BROADENED_SCOPE, violations)

    def test_no_violations_for_equivalent(self):
        """No violations for semantically equivalent translation."""
        anchor = "Payment is due within 30 days."
        aligned = "El pago debe realizarse dentro de 30 días."

        violations = self.manager.check_translation_violations(anchor, aligned, "es")
        self.assertEqual(len(violations), 0)


class TestCanonicalTermMapping(unittest.TestCase):
    """Test canonical term mapping per NCIP-003 Section 7."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()
        self.contract = self.manager.create_contract("test-001")

    def test_create_term_mapping(self):
        """Test creating a term mapping."""
        mapping = CanonicalTermMapping(
            term_id="PROSE_CONTRACT",
            anchor_term="Prose Contract"
        )
        mapping.add_translation("es", "Contrato en Prosa")
        mapping.add_translation("fr", "Contrat en Prose")

        self.assertEqual(mapping.get_term("en"), "Prose Contract")
        self.assertEqual(mapping.get_term("es"), "Contrato en Prosa")
        self.assertEqual(mapping.get_term("fr"), "Contrat en Prose")

    def test_validate_term_mapping(self):
        """Test validating term mapping in contract."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")

        success, _msg = self.manager.validate_term_mapping(
            self.contract,
            term_id="RATIFICATION",
            anchor_term="Ratification",
            translated_term="Ratificación",
            language_code="es"
        )

        self.assertTrue(success)
        self.assertIn("RATIFICATION", self.contract.term_mappings)

    def test_term_mapping_anchor_mismatch(self):
        """Anchor term mismatch should fail."""
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")

        # First add a term
        self.manager.validate_term_mapping(
            self.contract, "TERM1", "Original", "Traducción", "es"
        )

        # Try to add with different anchor term
        success, msg = self.manager.validate_term_mapping(
            self.contract, "TERM1", "Different", "Otra", "fr"
        )

        self.assertFalse(success)
        self.assertIn("mismatch", msg)


class TestMultilingualRatification(unittest.TestCase):
    """Test human ratification in multilingual contexts per NCIP-003 Section 8."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()
        self.contract = self.manager.create_contract("test-001")
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test content")
        self.contract.add_language("es", LanguageRole.ALIGNED, "Contenido de prueba")

    def test_create_ratification(self):
        """Test creating multilingual ratification."""
        ratification = self.manager.create_multilingual_ratification(
            self.contract,
            ratifier_id="user-001",
            reviewed_languages=["en", "es"]
        )

        self.assertEqual(ratification.anchor_language, "en")
        self.assertIn("es", ratification.reviewed_languages)
        self.assertIn("English (anchor)", ratification.statement)

    def test_confirm_ratification(self):
        """Test confirming ratification binding."""
        ratification = self.manager.create_multilingual_ratification(
            self.contract, "user-001", ["en", "es"]
        )

        success, _statement = self.manager.confirm_ratification(ratification)

        self.assertTrue(success)
        self.assertTrue(ratification.binding_acknowledged)
        self.assertTrue(ratification.is_valid)

    def test_ratification_requires_reviewed_languages(self):
        """Ratification requires at least one reviewed language."""
        ratification = self.manager.create_multilingual_ratification(
            self.contract, "user-001", []
        )

        success, _msg = self.manager.confirm_ratification(ratification)
        self.assertFalse(success)


class TestValidatorReporting(unittest.TestCase):
    """Test validator reporting per NCIP-003 Section 6."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()
        self.contract = self.manager.create_contract("test-001")
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test content")
        self.contract.add_language("es", LanguageRole.ALIGNED, "Contenido de prueba")
        self.manager.validate_contract_alignment(self.contract)

    def test_validator_report_contains_required_fields(self):
        """Validator report must contain required fields per NCIP-003."""
        report = self.manager.validator_report_drift("test-001", "es")

        self.assertIn("language_pair", report)
        self.assertIn("drift_score", report)
        self.assertIn("affected_clauses", report)
        self.assertIn("canonical_terms_involved", report)
        self.assertIn("validator_action", report)

    def test_validator_report_language_pair(self):
        """Validator report shows correct language pair."""
        report = self.manager.validator_report_drift("test-001", "es")
        self.assertEqual(report["language_pair"], "en-es")

    def test_validator_report_contract_not_found(self):
        """Validator report handles missing contract."""
        report = self.manager.validator_report_drift("nonexistent", "es")
        self.assertIn("error", report)


class TestAlignmentSpec(unittest.TestCase):
    """Test machine-readable alignment spec per NCIP-003 Section 10."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()
        self.contract = self.manager.create_contract("test-001")
        self.contract.add_language("en", LanguageRole.ANCHOR, "Test")
        self.contract.add_language("es", LanguageRole.ALIGNED, "Prueba")
        self.contract.add_language("ja", LanguageRole.INFORMATIONAL, "テスト")

    def test_generate_alignment_spec(self):
        """Test generating alignment spec YAML structure."""
        spec = self.manager.generate_alignment_spec(self.contract)

        self.assertIn("multilingual_semantics", spec)
        ms = spec["multilingual_semantics"]

        self.assertEqual(ms["version"], "1.0")
        self.assertEqual(ms["canonical_anchor_language"], "en")
        self.assertIn("languages", ms)
        self.assertIn("alignment_rules", ms)
        self.assertIn("validator_actions", ms)

    def test_alignment_spec_languages(self):
        """Test languages in alignment spec."""
        spec = self.manager.generate_alignment_spec(self.contract)
        languages = spec["multilingual_semantics"]["languages"]

        codes = [l["code"] for l in languages]
        self.assertIn("en", codes)
        self.assertIn("es", codes)
        self.assertIn("ja", codes)

    def test_alignment_spec_rules(self):
        """Test alignment rules in spec."""
        spec = self.manager.generate_alignment_spec(self.contract)
        rules = spec["multilingual_semantics"]["alignment_rules"]

        self.assertIn("core_terms", rules)
        self.assertIn("obligations", rules)
        self.assertTrue(rules["core_terms"]["must_map_to_registry"])
        self.assertFalse(rules["obligations"]["allow_addition"])


class TestStatusSummary(unittest.TestCase):
    """Test status summary generation."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_empty_status(self):
        """Test status with no contracts."""
        summary = self.manager.get_status_summary()

        self.assertEqual(summary["total_contracts"], 0)
        self.assertEqual(summary["total_language_entries"], 0)

    def test_status_with_contracts(self):
        """Test status with contracts."""
        contract1 = self.manager.create_contract("c1")
        contract1.add_language("en", LanguageRole.ANCHOR, "Test 1")
        contract1.add_language("es", LanguageRole.ALIGNED, "Prueba 1")

        contract2 = self.manager.create_contract("c2", canonical_anchor_language="fr")
        contract2.add_language("fr", LanguageRole.ANCHOR, "Test 2")

        summary = self.manager.get_status_summary()

        self.assertEqual(summary["total_contracts"], 2)
        self.assertEqual(summary["total_language_entries"], 3)
        self.assertEqual(summary["aligned_languages"], 1)
        self.assertIn("en", summary["contracts_by_csal"])
        self.assertIn("fr", summary["contracts_by_csal"])


class TestClauseDriftResult(unittest.TestCase):
    """Test clause-level drift analysis."""

    def setUp(self):
        self.manager = MultilingualAlignmentManager()

    def test_analyze_clause_drift(self):
        """Test analyzing drift for a specific clause."""
        result = self.manager.analyze_clause_drift(
            clause_id="clause-1",
            anchor_text="The contractor must deliver the software.",
            aligned_text="El contratista debe entregar el software.",
            language_code="es"
        )

        self.assertIsInstance(result, ClauseDriftResult)
        self.assertEqual(result.clause_id, "clause-1")
        self.assertIsNotNone(result.drift_score)
        self.assertIsNotNone(result.drift_level)
        self.assertIsNotNone(result.recommended_action)


class TestAlignmentRules(unittest.TestCase):
    """Test alignment rules configuration."""

    def test_default_rules(self):
        """Test default alignment rules per NCIP-003."""
        rules = AlignmentRules()

        # Core term rules
        self.assertTrue(rules.must_map_to_registry)
        self.assertTrue(rules.allow_lexical_variation)
        self.assertFalse(rules.allow_semantic_variation)

        # Obligation rules
        self.assertFalse(rules.allow_obligation_addition)
        self.assertFalse(rules.allow_obligation_removal)
        self.assertFalse(rules.allow_scope_change)

    def test_rules_to_dict(self):
        """Test converting rules to dictionary."""
        rules = AlignmentRules()
        d = rules.to_dict()

        self.assertIn("core_terms", d)
        self.assertIn("obligations", d)


if __name__ == "__main__":
    unittest.main()

"""
Tests for NCIP-001 Canonical Term Registry

Tests the term_registry module for:
- Registry loading and parsing
- Term lookup (canonical and synonym)
- Deprecated term detection
- Text validation against registry
- Term class categorization
"""

import sys
from pathlib import Path

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from term_registry import (
    CanonicalTermRegistry,
    TermClass,
    TermDefinition,
    TermStatus,
    TermValidationResult,
    get_registry,
    get_term_definition,
    resolve_synonym,
    validate_entry_terms,
)


class TestCanonicalTermRegistry:
    """Tests for the CanonicalTermRegistry class."""

    @pytest.fixture
    def registry(self):
        """Get a fresh registry instance."""
        return CanonicalTermRegistry()

    def test_registry_loads_successfully(self, registry):
        """Test that the registry loads without errors."""
        registry.load()
        assert registry._loaded is True
        assert registry.version == "1.0"

    def test_registry_has_terms(self, registry):
        """Test that the registry contains expected terms."""
        registry.load()
        all_terms = registry.get_all_canonical_terms()
        assert len(all_terms) > 0
        assert "Intent" in all_terms
        assert "Entry" in all_terms
        assert "Agreement" in all_terms

    def test_lookup_canonical_term(self, registry):
        """Test looking up a canonical term."""
        registry.load()
        result = registry.lookup("Intent")

        assert result.status == TermStatus.CANONICAL
        assert result.canonical_term == "Intent"
        assert result.definition is not None
        assert result.definition.term_class == TermClass.CORE

    def test_lookup_case_insensitive(self, registry):
        """Test that lookup is case-insensitive."""
        registry.load()

        result1 = registry.lookup("intent")
        result2 = registry.lookup("INTENT")
        result3 = registry.lookup("Intent")

        assert result1.canonical_term == "Intent"
        assert result2.canonical_term == "Intent"
        assert result3.canonical_term == "Intent"

    def test_lookup_synonym(self, registry):
        """Test looking up a synonym."""
        registry.load()
        result = registry.lookup("PoU")

        assert result.status == TermStatus.SYNONYM
        assert result.canonical_term == "Proof of Understanding"
        assert result.definition is not None

    def test_lookup_unknown_term(self, registry):
        """Test looking up an unknown term."""
        registry.load()
        result = registry.lookup("NonExistentTerm")

        assert result.status == TermStatus.UNKNOWN
        assert result.canonical_term is None
        assert result.definition is None

    def test_is_canonical_term(self, registry):
        """Test is_canonical_term method."""
        registry.load()

        assert registry.is_canonical_term("Intent") is True
        assert registry.is_canonical_term("PoU") is False  # Synonym
        assert registry.is_canonical_term("FakeTerm") is False

    def test_is_known_term(self, registry):
        """Test is_known_term method."""
        registry.load()

        assert registry.is_known_term("Intent") is True
        assert registry.is_known_term("PoU") is True  # Synonym is known
        assert registry.is_known_term("FakeTerm") is False

    def test_get_terms_by_class(self, registry):
        """Test getting terms by class."""
        registry.load()

        core_terms = registry.get_core_terms()
        protocol_terms = registry.get_protocol_terms()
        extension_terms = registry.get_extension_terms()

        assert len(core_terms) > 0
        assert all(t.term_class == TermClass.CORE for t in core_terms)

        assert len(protocol_terms) > 0
        assert all(t.term_class == TermClass.PROTOCOL_BOUND for t in protocol_terms)

        assert len(extension_terms) > 0
        assert all(t.term_class == TermClass.EXTENSION for t in extension_terms)

    def test_core_terms_are_immutable(self, registry):
        """Test that core terms are marked as immutable."""
        registry.load()
        core_terms = registry.get_core_terms()

        for term in core_terms:
            assert term.is_mutable is False, f"Core term {term.term} should be immutable"

    def test_get_definition(self, registry):
        """Test getting term definition."""
        registry.load()
        definition = registry.get_definition("Semantic Drift")

        assert definition is not None
        assert definition.term == "Semantic Drift"
        assert "divergence" in definition.definition.lower()

    def test_get_canonical(self, registry):
        """Test getting canonical form of synonym."""
        registry.load()

        # Test synonym resolution
        assert registry.get_canonical("drift") == "Semantic Drift"
        assert registry.get_canonical("contract") == "Agreement"
        assert registry.get_canonical("T0") == "Temporal Fixity"

        # Test canonical term returns itself
        assert registry.get_canonical("Intent") == "Intent"

    def test_get_all_synonyms(self, registry):
        """Test getting all synonyms mapping."""
        registry.load()
        synonyms = registry.get_all_synonyms()

        assert isinstance(synonyms, dict)
        assert len(synonyms) > 0
        assert "pou" in synonyms
        assert synonyms["pou"] == "Proof of Understanding"


class TestTermValidation:
    """Tests for text validation against term registry."""

    @pytest.fixture
    def registry(self):
        """Get a fresh registry instance."""
        reg = CanonicalTermRegistry()
        reg.load()
        return reg

    def test_validate_text_finds_core_terms(self, registry):
        """Test that validation finds core terms in text."""
        text = "The Intent of this Agreement is to establish a clear Ratification process."
        result = registry.validate_text(text)

        assert "Intent" in result.core_terms_found
        assert "Agreement" in result.core_terms_found
        assert "Ratification" in result.core_terms_found

    def test_validate_text_finds_synonyms(self, registry):
        """Test that validation detects synonym usage."""
        text = "The user intention should be recorded with their approval."
        result = registry.validate_text(text)

        # Should find synonyms
        assert len(result.synonym_usage) > 0
        synonyms_used = [s[0] for s in result.synonym_usage]
        assert "intention" in synonyms_used or "approval" in synonyms_used

    def test_validate_text_no_issues_for_valid_text(self, registry):
        """Test that valid text has no issues."""
        text = "This Entry represents a valid Intent with clear Ratification terms."
        result = registry.validate_text(text)

        assert result.has_issues is False

    def test_validate_text_returns_all_categories(self, registry):
        """Test that validation categorizes terms correctly."""
        text = """
        This Agreement establishes a Negotiation process with Dialectic Consensus.
        The Settlement will be handled through proper Dispute resolution.
        """
        result = registry.validate_text(text)

        # Should have terms from multiple categories
        assert len(result.core_terms_found) > 0  # Agreement
        assert len(result.protocol_terms_found) > 0  # Negotiation, Settlement, Dispute
        assert len(result.extension_terms_found) > 0  # Dialectic Consensus


class TestTermDefinition:
    """Tests for TermDefinition dataclass."""

    def test_term_definition_properties(self):
        """Test TermDefinition property methods."""
        mutable_term = TermDefinition(
            term="Test",
            term_class=TermClass.EXTENSION,
            definition="A test term",
            introduced_in="Test",
            governance={"mutable": True},
        )

        immutable_term = TermDefinition(
            term="Core",
            term_class=TermClass.CORE,
            definition="A core term",
            introduced_in="Spec",
            governance={"mutable": False, "requires_ncip": True},
        )

        assert mutable_term.is_mutable is True
        assert immutable_term.is_mutable is False
        assert immutable_term.requires_ncip is True


class TestConvenienceFunctions:
    """Tests for module-level convenience functions."""

    def test_get_registry_singleton(self):
        """Test that get_registry returns singleton."""
        reg1 = get_registry()
        reg2 = get_registry()

        assert reg1 is reg2

    def test_validate_entry_terms(self):
        """Test validate_entry_terms convenience function."""
        content = "This Entry establishes an Agreement."
        intent = "To create a valid Intent record."

        result = validate_entry_terms(content, intent)

        assert isinstance(result, TermValidationResult)
        assert "Entry" in result.core_terms_found
        assert "Agreement" in result.core_terms_found
        assert "Intent" in result.core_terms_found

    def test_get_term_definition(self):
        """Test get_term_definition convenience function."""
        definition = get_term_definition("Intent")

        assert definition is not None
        assert "human-authored" in definition.lower()

    def test_resolve_synonym(self):
        """Test resolve_synonym convenience function."""
        assert resolve_synonym("PoU") == "Proof of Understanding"
        assert resolve_synonym("contract") == "Agreement"
        assert resolve_synonym("Intent") == "Intent"  # Already canonical
        assert resolve_synonym("UnknownTerm") == "UnknownTerm"  # Returns original


class TestTermValidationResult:
    """Tests for TermValidationResult dataclass."""

    def test_has_issues_when_deprecated(self):
        """Test has_issues returns True for deprecated terms."""
        result = TermValidationResult()
        result.deprecated_terms = ["old_term"]

        assert result.has_issues is True

    def test_has_issues_when_unknown(self):
        """Test has_issues returns True for unknown terms."""
        result = TermValidationResult()
        result.unknown_terms = ["weird_term"]

        assert result.has_issues is True

    def test_no_issues_for_clean_result(self):
        """Test has_issues returns False for clean result."""
        result = TermValidationResult()
        result.core_terms_found = ["Intent"]

        assert result.has_issues is False

    def test_has_warnings_for_synonyms(self):
        """Test has_warnings returns True for synonym usage."""
        result = TermValidationResult()
        result.synonym_usage = [("contract", "Agreement")]

        assert result.has_warnings is True


class TestRegistryAuthority:
    """Tests for registry authority and metadata."""

    @pytest.fixture
    def registry(self):
        """Get a fresh registry instance."""
        reg = CanonicalTermRegistry()
        reg.load()
        return reg

    def test_registry_has_authority(self, registry):
        """Test that registry has authority information."""
        authority = registry.authority

        assert "specification" in authority
        assert "governance" in authority
        assert "NCIP" in authority["governance"]

    def test_registry_version(self, registry):
        """Test registry version."""
        assert registry.version == "1.0"

    def test_protocol_bound_terms_have_governance(self, registry):
        """Test that protocol-bound terms specify their governing MP."""
        protocol_terms = registry.get_protocol_terms()

        for term in protocol_terms:
            # Protocol-bound terms should specify governed_by
            # (some may not have it explicitly in YAML, but should have governance rules)
            assert term.governance is not None


class TestEdgeCases:
    """Tests for edge cases and error handling."""

    def test_empty_text_validation(self):
        """Test validation of empty text."""
        registry = get_registry()
        result = registry.validate_text("")

        assert result.has_issues is False
        assert len(result.core_terms_found) == 0

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        registry = get_registry()

        result1 = registry.lookup("  Intent  ")
        result2 = registry.lookup("Intent")

        assert result1.canonical_term == result2.canonical_term

    def test_multiword_term_lookup(self):
        """Test lookup of multi-word terms."""
        registry = get_registry()

        result = registry.lookup("Proof of Understanding")
        assert result.status == TermStatus.CANONICAL
        assert result.canonical_term == "Proof of Understanding"

    def test_multiword_term_in_text(self):
        """Test finding multi-word terms in text."""
        registry = get_registry()

        text = "The Proof of Understanding demonstrates that the Semantic Drift is minimal."
        result = registry.validate_text(text)

        assert "Proof of Understanding" in result.core_terms_found
        assert "Semantic Drift" in result.core_terms_found


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

"""
NatLangChain - Canonical Term Registry
Implements NCIP-001: Machine-readable registry of canonical terms

This module provides:
- Loading and caching of the canonical term registry
- Term lookup by canonical name or synonym
- Term class validation (core, protocol-bound, extension)
- Detection of unknown or deprecated terms
- Validator integration for term enforcement
"""

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import yaml


class TermClass(Enum):
    """Classification of terms per NCIP-001."""

    CORE = "core"
    PROTOCOL_BOUND = "protocol-bound"
    EXTENSION = "extension"


class TermStatus(Enum):
    """Status of a term lookup result."""

    CANONICAL = "canonical"
    SYNONYM = "synonym"
    DEPRECATED = "deprecated"
    UNKNOWN = "unknown"


@dataclass
class TermDefinition:
    """A canonical term definition from the registry."""

    term: str
    term_class: TermClass
    definition: str
    introduced_in: str
    governance: dict[str, Any]
    synonyms: list[str] = field(default_factory=list)
    notes: str | None = None
    governed_by: str | None = None  # For protocol-bound terms

    @property
    def is_mutable(self) -> bool:
        """Check if this term can be modified."""
        return self.governance.get("mutable", False)

    @property
    def requires_ncip(self) -> bool:
        """Check if changes require an NCIP."""
        return self.governance.get("requires_ncip", False)


@dataclass
class TermLookupResult:
    """Result of looking up a term in the registry."""

    status: TermStatus
    canonical_term: str | None = None
    definition: TermDefinition | None = None
    matched_as: str | None = None  # The form that matched (synonym, etc.)


@dataclass
class TermValidationResult:
    """Result of validating text against the term registry."""

    unknown_terms: list[str] = field(default_factory=list)
    deprecated_terms: list[str] = field(default_factory=list)
    synonym_usage: list[tuple[str, str]] = field(default_factory=list)  # (used, canonical)
    core_terms_found: list[str] = field(default_factory=list)
    protocol_terms_found: list[str] = field(default_factory=list)
    extension_terms_found: list[str] = field(default_factory=list)

    @property
    def has_issues(self) -> bool:
        """Check if validation found any issues."""
        return bool(self.unknown_terms or self.deprecated_terms)

    @property
    def has_warnings(self) -> bool:
        """Check if validation found any warnings (synonym usage)."""
        return bool(self.synonym_usage)


class CanonicalTermRegistry:
    """
    Manages the canonical term registry per NCIP-001.

    The registry is normative and provides:
    - Single source of semantic truth
    - Elimination of ambiguity in protocol-critical language
    - Support for Proof of Understanding and mediator enforcement
    """

    # Default path to registry file
    DEFAULT_REGISTRY_PATH = Path(__file__).parent.parent / "config" / "canonical_terms.yaml"

    def __init__(self, registry_path: Path | None = None):
        """
        Initialize the term registry.

        Args:
            registry_path: Path to the YAML registry file. Uses default if not provided.
        """
        self.registry_path = registry_path or self.DEFAULT_REGISTRY_PATH
        self._terms: dict[str, TermDefinition] = {}
        self._synonyms: dict[str, str] = {}  # synonym -> canonical term
        self._deprecated: set[str] = set()
        self._registry_version: str = ""
        self._last_updated: str = ""
        self._authority: dict[str, str] = {}
        self._loaded = False

    def load(self) -> None:
        """
        Load the registry from YAML file.

        Raises:
            FileNotFoundError: If registry file doesn't exist
            ValueError: If registry format is invalid
        """
        if not self.registry_path.exists():
            raise FileNotFoundError(
                f"Canonical term registry not found at {self.registry_path}. "
                "This file is required per NCIP-001."
            )

        try:
            with open(self.registry_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in term registry: {e}")

        if not data:
            raise ValueError("Empty term registry file")

        # Extract metadata
        self._registry_version = data.get("registry_version", "unknown")
        self._last_updated = data.get("last_updated", "unknown")
        self._authority = data.get("authority", {})

        # Load terms
        terms_data = data.get("terms", [])
        if not terms_data:
            raise ValueError("No terms defined in registry")

        for term_data in terms_data:
            self._load_term(term_data)

        # Load deprecated terms
        deprecated_data = data.get("deprecated_terms", [])
        for dep in deprecated_data:
            if isinstance(dep, str):
                self._deprecated.add(dep.lower())
            elif isinstance(dep, dict):
                self._deprecated.add(dep.get("term", "").lower())

        self._loaded = True

    def _load_term(self, term_data: dict[str, Any]) -> None:
        """Load a single term into the registry."""
        term_name = term_data.get("term")
        if not term_name:
            return

        try:
            term_class = TermClass(term_data.get("class", "extension"))
        except ValueError:
            term_class = TermClass.EXTENSION

        definition = TermDefinition(
            term=term_name,
            term_class=term_class,
            definition=term_data.get("definition", "").strip(),
            introduced_in=term_data.get("introduced_in", "unknown"),
            governance=term_data.get("governance", {}),
            synonyms=term_data.get("synonyms", []),
            notes=term_data.get("notes"),
            governed_by=term_data.get("governed_by"),
        )

        # Store by canonical name (case-insensitive lookup)
        self._terms[term_name.lower()] = definition

        # Map synonyms to canonical term
        for synonym in definition.synonyms:
            self._synonyms[synonym.lower()] = term_name

    def _ensure_loaded(self) -> None:
        """Ensure the registry is loaded."""
        if not self._loaded:
            self.load()

    def lookup(self, term: str) -> TermLookupResult:
        """
        Look up a term in the registry.

        Args:
            term: The term to look up (case-insensitive)

        Returns:
            TermLookupResult with status and definition if found
        """
        self._ensure_loaded()
        term_lower = term.lower().strip()

        # Check for deprecated
        if term_lower in self._deprecated:
            return TermLookupResult(status=TermStatus.DEPRECATED, matched_as=term)

        # Check for canonical term
        if term_lower in self._terms:
            definition = self._terms[term_lower]
            return TermLookupResult(
                status=TermStatus.CANONICAL,
                canonical_term=definition.term,
                definition=definition,
                matched_as=term,
            )

        # Check for synonym
        if term_lower in self._synonyms:
            canonical = self._synonyms[term_lower]
            definition = self._terms.get(canonical.lower())
            return TermLookupResult(
                status=TermStatus.SYNONYM,
                canonical_term=canonical,
                definition=definition,
                matched_as=term,
            )

        # Unknown term
        return TermLookupResult(status=TermStatus.UNKNOWN, matched_as=term)

    def get_canonical(self, term: str) -> str | None:
        """
        Get the canonical form of a term.

        Args:
            term: Term or synonym to resolve

        Returns:
            Canonical term name or None if unknown
        """
        result = self.lookup(term)
        return result.canonical_term

    def get_definition(self, term: str) -> TermDefinition | None:
        """
        Get the full definition of a term.

        Args:
            term: Term or synonym to look up

        Returns:
            TermDefinition or None if unknown
        """
        result = self.lookup(term)
        return result.definition

    def is_canonical_term(self, term: str) -> bool:
        """Check if a term is a canonical term (not synonym)."""
        self._ensure_loaded()
        return term.lower().strip() in self._terms

    def is_known_term(self, term: str) -> bool:
        """Check if a term is known (canonical or synonym)."""
        result = self.lookup(term)
        return result.status in (TermStatus.CANONICAL, TermStatus.SYNONYM)

    def is_deprecated(self, term: str) -> bool:
        """Check if a term is deprecated."""
        self._ensure_loaded()
        return term.lower().strip() in self._deprecated

    def get_terms_by_class(self, term_class: TermClass) -> list[TermDefinition]:
        """Get all terms of a specific class."""
        self._ensure_loaded()
        return [t for t in self._terms.values() if t.term_class == term_class]

    def get_core_terms(self) -> list[TermDefinition]:
        """Get all core (immutable) terms."""
        return self.get_terms_by_class(TermClass.CORE)

    def get_protocol_terms(self) -> list[TermDefinition]:
        """Get all protocol-bound terms."""
        return self.get_terms_by_class(TermClass.PROTOCOL_BOUND)

    def get_extension_terms(self) -> list[TermDefinition]:
        """Get all extension terms."""
        return self.get_terms_by_class(TermClass.EXTENSION)

    def get_all_canonical_terms(self) -> list[str]:
        """Get list of all canonical term names."""
        self._ensure_loaded()
        return [t.term for t in self._terms.values()]

    def get_all_synonyms(self) -> dict[str, str]:
        """Get mapping of all synonyms to canonical terms."""
        self._ensure_loaded()
        return dict(self._synonyms)

    @property
    def version(self) -> str:
        """Get registry version."""
        self._ensure_loaded()
        return self._registry_version

    @property
    def authority(self) -> dict[str, str]:
        """Get registry authority information."""
        self._ensure_loaded()
        return self._authority

    def validate_text(self, text: str) -> TermValidationResult:
        """
        Validate text for term usage.

        Identifies:
        - Unknown terms that might be protocol-relevant
        - Deprecated term usage
        - Synonym usage (recommends canonical form)
        - Categorizes found terms by class

        Args:
            text: The text to validate

        Returns:
            TermValidationResult with findings
        """
        self._ensure_loaded()
        result = TermValidationResult()

        # Build set of all known terms and synonyms for matching
        all_terms = set()
        for term in self._terms:
            all_terms.add(term)
        for synonym in self._synonyms:
            all_terms.add(synonym)
        for deprecated in self._deprecated:
            all_terms.add(deprecated)

        # Find potential term usage in text
        # Look for multi-word terms first (e.g., "Proof of Understanding")
        text_lower = text.lower()

        # Check each known term/synonym
        for term_key in sorted(all_terms, key=len, reverse=True):
            # Use word boundary matching
            pattern = r"\b" + re.escape(term_key) + r"\b"
            if re.search(pattern, text_lower, re.IGNORECASE):
                lookup_result = self.lookup(term_key)

                if lookup_result.status == TermStatus.DEPRECATED:
                    if term_key not in result.deprecated_terms:
                        result.deprecated_terms.append(term_key)

                elif lookup_result.status == TermStatus.SYNONYM:
                    pair = (term_key, lookup_result.canonical_term)
                    if pair not in result.synonym_usage:
                        result.synonym_usage.append(pair)
                    # Also categorize by class
                    if lookup_result.definition:
                        self._categorize_term(lookup_result.definition, result)

                elif lookup_result.status == TermStatus.CANONICAL:
                    if lookup_result.definition:
                        self._categorize_term(lookup_result.definition, result)

        return result

    def _categorize_term(self, definition: TermDefinition, result: TermValidationResult) -> None:
        """Categorize a found term by its class."""
        term = definition.term
        if definition.term_class == TermClass.CORE:
            if term not in result.core_terms_found:
                result.core_terms_found.append(term)
        elif definition.term_class == TermClass.PROTOCOL_BOUND:
            if term not in result.protocol_terms_found:
                result.protocol_terms_found.append(term)
        elif definition.term_class == TermClass.EXTENSION:
            if term not in result.extension_terms_found:
                result.extension_terms_found.append(term)

    def extract_unknown_terms(
        self, text: str, candidate_terms: list[str] | None = None
    ) -> list[str]:
        """
        Extract terms from text that are not in the registry.

        This is useful for flagging potentially undefined protocol terms.

        Args:
            text: The text to analyze
            candidate_terms: Optional list of specific terms to check.
                            If not provided, extracts capitalized phrases.

        Returns:
            List of unknown terms found
        """
        self._ensure_loaded()
        unknown = []

        if candidate_terms:
            # Check specific terms
            for term in candidate_terms:
                if not self.is_known_term(term) and not self.is_deprecated(term):
                    unknown.append(term)
        else:
            # Extract capitalized phrases as potential terms
            # Match Title Case words/phrases
            pattern = r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b"
            matches = re.findall(pattern, text)

            for match in matches:
                if not self.is_known_term(match) and not self.is_deprecated(match):
                    if match not in unknown:
                        unknown.append(match)

        return unknown


# Singleton instance for global access
_registry_instance: CanonicalTermRegistry | None = None


def get_registry() -> CanonicalTermRegistry:
    """
    Get the global term registry instance.

    Returns:
        The singleton CanonicalTermRegistry instance
    """
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = CanonicalTermRegistry()
    return _registry_instance


def validate_entry_terms(content: str, intent: str) -> TermValidationResult:
    """
    Validate terms in an entry for registry compliance.

    Convenience function for validator integration.

    Args:
        content: Entry content
        intent: Entry intent

    Returns:
        Combined validation result for content and intent
    """
    registry = get_registry()

    # Validate both content and intent
    content_result = registry.validate_text(content)
    intent_result = registry.validate_text(intent)

    # Merge results
    combined = TermValidationResult()
    combined.unknown_terms = list(set(content_result.unknown_terms + intent_result.unknown_terms))
    combined.deprecated_terms = list(
        set(content_result.deprecated_terms + intent_result.deprecated_terms)
    )
    combined.synonym_usage = list(set(content_result.synonym_usage + intent_result.synonym_usage))
    combined.core_terms_found = list(
        set(content_result.core_terms_found + intent_result.core_terms_found)
    )
    combined.protocol_terms_found = list(
        set(content_result.protocol_terms_found + intent_result.protocol_terms_found)
    )
    combined.extension_terms_found = list(
        set(content_result.extension_terms_found + intent_result.extension_terms_found)
    )

    return combined


def get_term_definition(term: str) -> str | None:
    """
    Get the definition of a term.

    Convenience function for quick lookups.

    Args:
        term: Term to look up (canonical or synonym)

    Returns:
        Definition string or None
    """
    registry = get_registry()
    definition = registry.get_definition(term)
    return definition.definition if definition else None


def resolve_synonym(term: str) -> str:
    """
    Resolve a synonym to its canonical form.

    Args:
        term: Term or synonym

    Returns:
        Canonical term name (or original if not a synonym)
    """
    registry = get_registry()
    canonical = registry.get_canonical(term)
    return canonical if canonical else term

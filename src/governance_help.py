"""
NatLangChain - Governance Help System

Provides programmatic access to governance documentation (NCIPs, MPs, design philosophy)
from within the application. Makes NatLangChain's unique governance framework accessible
to users without overwhelming them.

This is a key differentiator: NatLangChain has 15+ NCIPs defining comprehensive governance,
unlike most blockchain projects that lack formal governance specs.
"""

from dataclasses import dataclass, field
from typing import Any
from pathlib import Path
import os

# =============================================================================
# Constants
# =============================================================================

DOCS_DIR = Path(__file__).parent.parent / "docs"

# NCIP Categories for organization
NCIP_CATEGORIES = {
    "foundation": {
        "title": "Foundation & Terminology",
        "description": "Core concepts, terms, and semantic governance",
        "ncips": ["NCIP-000", "NCIP-001"]
    },
    "semantic_integrity": {
        "title": "Semantic Integrity",
        "description": "Drift detection, thresholds, and multilingual support",
        "ncips": ["NCIP-002", "NCIP-003", "NCIP-004"]
    },
    "dispute_resolution": {
        "title": "Dispute Resolution",
        "description": "Escalation, locking, appeals, and precedent",
        "ncips": ["NCIP-005", "NCIP-008"]
    },
    "trust_reputation": {
        "title": "Trust & Reputation",
        "description": "Validator scoring, mediator dynamics, and coupling",
        "ncips": ["NCIP-007", "NCIP-010", "NCIP-011"]
    },
    "jurisdiction_compliance": {
        "title": "Jurisdiction & Compliance",
        "description": "Legal bridging and regulatory interfaces",
        "ncips": ["NCIP-006", "NCIP-009"]
    },
    "human_experience": {
        "title": "Human Experience",
        "description": "UX, cognitive load, and emergency handling",
        "ncips": ["NCIP-012", "NCIP-013"]
    },
    "protocol_evolution": {
        "title": "Protocol Evolution",
        "description": "Amendments, sunset clauses, and historical semantics",
        "ncips": ["NCIP-014", "NCIP-015"]
    }
}


# =============================================================================
# NCIP Registry
# =============================================================================

@dataclass
class NCIPEntry:
    """A single NCIP entry."""
    id: str
    title: str
    summary: str
    status: str = "Final"
    category: str = ""
    key_concepts: list[str] = field(default_factory=list)
    related: list[str] = field(default_factory=list)
    doc_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "category": self.category,
            "key_concepts": self.key_concepts,
            "related": self.related,
            "doc_file": self.doc_file
        }


# The complete NCIP registry with summaries
NCIP_REGISTRY: dict[str, NCIPEntry] = {
    "NCIP-000": NCIPEntry(
        id="NCIP-000",
        title="Terminology & Semantics Governance",
        summary="Establishes the canonical vocabulary for NatLangChain. Defines core terms like 'Entry', 'Intent', 'Agreement', and 'Ratification'. All protocol documents must use these terms consistently.",
        category="foundation",
        key_concepts=["Canonical Terms", "Semantic Authority", "Term Evolution"],
        related=["NCIP-001"],
        doc_file="NCIP-000.md"
    ),
    "NCIP-001": NCIPEntry(
        id="NCIP-001",
        title="Canonical Term Registry",
        summary="The official registry of defined terms. Each term has a precise definition, usage context, and examples. New terms require formal proposal and community consensus.",
        category="foundation",
        key_concepts=["Entry", "Intent", "Agreement", "Ratification", "Settlement", "Mediator"],
        related=["NCIP-000", "NCIP-002"],
        doc_file="NCIP-001.md"
    ),
    "NCIP-002": NCIPEntry(
        id="NCIP-002",
        title="Semantic Drift Thresholds & Validator Responses",
        summary="Defines how semantic drift is measured (0-100%) and categorized into bands: D0 (Stable), D1 (Soft Drift), D2 (Ambiguous), D3 (Hard Drift), D4 (Semantic Break). Each band triggers specific validator responses.",
        category="semantic_integrity",
        key_concepts=["Drift Score", "D0-D4 Bands", "Validator Response", "Semantic Break"],
        related=["NCIP-003", "NCIP-007"],
        doc_file="NCIP-002.md"
    ),
    "NCIP-003": NCIPEntry(
        id="NCIP-003",
        title="Multilingual Semantic Alignment & Drift",
        summary="Handles semantic preservation across languages. When contracts are translated, this NCIP ensures meaning is preserved and drift is detected even across language boundaries.",
        category="semantic_integrity",
        key_concepts=["Cross-Language Drift", "Translation Integrity", "Semantic Equivalence"],
        related=["NCIP-002", "NCIP-004"],
        doc_file="NCIP-003.md"
    ),
    "NCIP-004": NCIPEntry(
        id="NCIP-004",
        title="Proof of Understanding (PoU) Generation & Verification",
        summary="Defines how parties demonstrate they understand an agreement. PoU is semantic, not cryptographic - it proves comprehension of meaning, not just possession of keys.",
        category="semantic_integrity",
        key_concepts=["Paraphrase Generation", "Understanding Score", "Semantic Verification"],
        related=["NCIP-002", "NCIP-012"],
        doc_file="NCIP-004.md"
    ),
    "NCIP-005": NCIPEntry(
        id="NCIP-005",
        title="Dispute Escalation, Cooling Periods & Semantic Locking",
        summary="Governs how disputes are raised and escalated. Includes mandatory cooling periods (24-72h) before escalation and semantic locks that freeze interpretation at a point in time.",
        category="dispute_resolution",
        key_concepts=["Cooling Period", "Semantic Lock", "Escalation Path", "Dispute Initiation"],
        related=["NCIP-008", "NCIP-013"],
        doc_file="NCIP-005.md"
    ),
    "NCIP-006": NCIPEntry(
        id="NCIP-006",
        title="Jurisdictional Interpretation & Legal Bridging",
        summary="Bridges NatLangChain agreements to real-world legal systems. Defines how jurisdiction is determined and how protocol outcomes interface with courts and arbitration.",
        category="jurisdiction_compliance",
        key_concepts=["Jurisdiction Selection", "Legal Bridge", "Arbitration Interface"],
        related=["NCIP-009"],
        doc_file="NCIP-006.md"
    ),
    "NCIP-007": NCIPEntry(
        id="NCIP-007",
        title="Validator Trust Scoring & Reliability Weighting",
        summary="Validators earn trust through accurate drift detection and consistent behavior. Trust scores weight their influence in consensus. Poor performance reduces influence.",
        category="trust_reputation",
        key_concepts=["Trust Score", "Validator Weight", "Historical Accuracy", "Appeal Survival"],
        related=["NCIP-010", "NCIP-011"],
        doc_file="NCIP-007.md"
    ),
    "NCIP-008": NCIPEntry(
        id="NCIP-008",
        title="Semantic Appeals, Precedent & Case Law Encoding",
        summary="Defines the appeals process for disputed interpretations. Successful appeals create precedent that influences future interpretations - building semantic case law.",
        category="dispute_resolution",
        key_concepts=["Appeal Process", "Precedent Recording", "Case Law", "Semantic Precedent"],
        related=["NCIP-005", "NCIP-007"],
        doc_file="NCIP-008.md"
    ),
    "NCIP-009": NCIPEntry(
        id="NCIP-009",
        title="Regulatory Interface Modules & Compliance Proofs",
        summary="Defines how NatLangChain interfaces with regulatory requirements (KYC, AML, GDPR, etc.). Compliance modules can be attached without changing core protocol.",
        category="jurisdiction_compliance",
        key_concepts=["Compliance Module", "Regulatory Interface", "Audit Trail", "Privacy Preservation"],
        related=["NCIP-006"],
        doc_file="NCIP-009.md"
    ),
    "NCIP-010": NCIPEntry(
        id="NCIP-010",
        title="Mediator Reputation, Slashing & Market Dynamics",
        summary="Mediators stake bonds and earn reputation through successful mediations. Poor performance triggers slashing. Creates a market for quality mediation services.",
        category="trust_reputation",
        key_concepts=["Mediator Bond", "Slashing", "Reputation Score", "Market Selection"],
        related=["NCIP-007", "NCIP-011"],
        doc_file="NCIP-010.md"
    ),
    "NCIP-011": NCIPEntry(
        id="NCIP-011",
        title="Validator–Mediator Interaction & Weight Coupling",
        summary="Validators measure meaning, mediators surface alignment. This NCIP ensures neither can substitute for the other. Authority is orthogonal, not hierarchical.",
        category="trust_reputation",
        key_concepts=["Role Separation", "Influence Gate", "Weight Coupling", "Collusion Resistance"],
        related=["NCIP-007", "NCIP-010"],
        doc_file="NCIP-011.md"
    ),
    "NCIP-012": NCIPEntry(
        id="NCIP-012",
        title="Human Ratification UX & Cognitive Load Limits",
        summary="Humans must actually understand what they're agreeing to. This NCIP sets limits on complexity, requires plain language summaries, and enforces reading time minimums.",
        category="human_experience",
        key_concepts=["Cognitive Load", "Plain Language", "Reading Time", "Comprehension Check"],
        related=["NCIP-004", "NCIP-013"],
        doc_file="NCIP-012.md"
    ),
    "NCIP-013": NCIPEntry(
        id="NCIP-013",
        title="Emergency Overrides, Force Majeure & Semantic Fallbacks",
        summary="Handles exceptional circumstances: natural disasters, system failures, or unforeseen events. Defines how agreements can be suspended or modified under force majeure.",
        category="human_experience",
        key_concepts=["Force Majeure", "Emergency Override", "Semantic Fallback", "Circuit Breaker"],
        related=["NCIP-005", "NCIP-012"],
        doc_file="NCIP-013.md"
    ),
    "NCIP-014": NCIPEntry(
        id="NCIP-014",
        title="Protocol Amendments & Constitutional Change",
        summary="How the protocol itself evolves. Major changes require supermajority consensus and extended discussion periods. Prevents hasty modifications to core governance.",
        category="protocol_evolution",
        key_concepts=["Amendment Process", "Supermajority", "Discussion Period", "Ratification"],
        related=["NCIP-015"],
        doc_file="NCIP-014.md"
    ),
    "NCIP-015": NCIPEntry(
        id="NCIP-015",
        title="Sunset Clauses, Archival Finality & Historical Semantics",
        summary="Agreements don't last forever. This NCIP governs expiration, archival, and how historical agreements are interpreted using contemporaneous meaning.",
        category="protocol_evolution",
        key_concepts=["Sunset Clause", "Archival", "Historical Context", "Temporal Interpretation"],
        related=["NCIP-014"],
        doc_file="NCIP-015.md"
    ),
}


# =============================================================================
# Mediator Protocol Specs
# =============================================================================

@dataclass
class MPSpec:
    """Mediator Protocol specification."""
    id: str
    title: str
    summary: str
    key_features: list[str] = field(default_factory=list)
    doc_file: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "summary": self.summary,
            "key_features": self.key_features,
            "doc_file": self.doc_file
        }


MP_REGISTRY: dict[str, MPSpec] = {
    "MP-02": MPSpec(
        id="MP-02",
        title="Proof-of-Effort Receipts",
        summary="Defines how work is recorded and verified. Effort receipts prove that parties fulfilled their obligations, creating an audit trail for dispute resolution.",
        key_features=["Effort Recording", "Receipt Verification", "Audit Trail"],
        doc_file="MP-02-spec.md"
    ),
    "MP-03": MPSpec(
        id="MP-03",
        title="Dispute & Escalation",
        summary="Comprehensive dispute handling protocol. Evidence freezing, clarification phase, escalation declarations, and transfer of record to external authorities.",
        key_features=["Evidence Freezing", "Clarification Phase", "Escalation Path", "Record Transfer"],
        doc_file="MP-03-spec.md"
    ),
    "MP-04": MPSpec(
        id="MP-04",
        title="Licensing & Delegation",
        summary="How rights and authority can be delegated. Defines licensing terms, delegation chains, and revocation procedures.",
        key_features=["License Types", "Delegation Chains", "Revocation", "Authority Limits"],
        doc_file="MP-04-spec.md"
    ),
    "MP-05": MPSpec(
        id="MP-05",
        title="Settlement & Capitalization",
        summary="Final resolution of agreements. Defines how economic value is distributed, finality is declared, and settlements become binding.",
        key_features=["Economic Finality", "Settlement Declaration", "Value Distribution"],
        doc_file="MP-05-spec.md"
    ),
}


# =============================================================================
# Core Concepts (Quick Reference)
# =============================================================================

CORE_CONCEPTS: dict[str, dict[str, str]] = {
    "entry": {
        "term": "Entry",
        "definition": "A discrete, timestamped record containing prose, metadata, and signatures. The fundamental unit of the NatLangChain ledger.",
        "example": "Alice's intent to provide consulting services, recorded at 2025-01-15 10:30 UTC."
    },
    "intent": {
        "term": "Intent",
        "definition": "A human-authored expression of desired outcome or commitment. The primary semantic input to the system.",
        "example": "'I agree to deliver the software by March 1st for $10,000.'"
    },
    "agreement": {
        "term": "Agreement",
        "definition": "Mutually ratified intents establishing shared understanding and obligations between parties.",
        "example": "A consulting contract where both parties have confirmed understanding via PoU."
    },
    "ratification": {
        "term": "Ratification",
        "definition": "An explicit act of consent confirming understanding and acceptance. Must be human-initiated.",
        "example": "Alice clicks 'I Accept' after paraphrasing the agreement to prove understanding."
    },
    "semantic_drift": {
        "term": "Semantic Drift",
        "definition": "Divergence between original meaning and subsequent interpretation. Measured 0-100%.",
        "example": "A contract about 'cloud storage' may drift as technology evolves."
    },
    "proof_of_understanding": {
        "term": "Proof of Understanding (PoU)",
        "definition": "Evidence that a party comprehends an agreement's meaning, not just its text. Semantic, not cryptographic.",
        "example": "Party generates their own paraphrase that captures the same obligations."
    },
    "semantic_lock": {
        "term": "Semantic Lock",
        "definition": "A binding freeze of interpretive meaning at a specific time, against which disputes are evaluated.",
        "example": "When a dispute is raised, meaning is locked at T0 to prevent reinterpretation."
    },
    "cooling_period": {
        "term": "Cooling Period",
        "definition": "Mandatory delay (24-72h) preventing immediate escalation, allowing clarification or settlement.",
        "example": "After filing a dispute, parties have 48 hours to attempt direct resolution."
    },
    "mediator": {
        "term": "Mediator",
        "definition": "Entity that helps surface alignment between parties. MAY clarify positions but MUST NOT render judgments.",
        "example": "An AI-assisted mediator helps parties identify where their intents diverge."
    },
    "validator": {
        "term": "Validator",
        "definition": "Entity that measures semantic validity and drift. Does NOT propose terms or negotiate outcomes.",
        "example": "A validator scores a proposed interpretation as 85% aligned with original intent."
    },
    "temporal_fixity": {
        "term": "Temporal Fixity",
        "definition": "Binding of meaning to a specific point in time (T0). Interpretations evaluated against contemporaneous context.",
        "example": "A 2020 contract about 'AI' is interpreted using 2020's understanding of AI."
    },
    "settlement": {
        "term": "Settlement",
        "definition": "Final resolution resulting in binding obligations, compensation, or closure. Declared by humans.",
        "example": "Parties agree Bob pays Alice $5,000 in full satisfaction of the contract."
    }
}


# =============================================================================
# Design Philosophy
# =============================================================================

DESIGN_PHILOSOPHY = {
    "title": "NatLangChain Design Philosophy",
    "subtitle": "Why Non-Determinism is a Feature",
    "principles": [
        {
            "name": "Human-Centered Recording",
            "summary": "The blockchain provides immutability. Humans provide judgment.",
            "detail": "Unlike deterministic smart contracts, NatLangChain doesn't pretend to 'compute' the right answer. It preserves evidence for humans to decide."
        },
        {
            "name": "Semantic, Not Syntactic",
            "summary": "Meaning matters, not exact text matching.",
            "detail": "Two statements can use different words but mean the same thing. The protocol understands semantics, not just strings."
        },
        {
            "name": "Multiple Valid Interpretations",
            "summary": "Disagreement is valuable information.",
            "detail": "When multiple LLMs interpret a contract differently, that reveals ambiguity humans should resolve."
        },
        {
            "name": "The Refusal Doctrine",
            "summary": "What we explicitly refuse to automate.",
            "detail": "Consent, Agreement, Authority, Value Finality, Dispute Resolution, and Moral Judgment are NEVER automated. Humans decide."
        },
        {
            "name": "Temporal Context",
            "summary": "Meaning is bound to time.",
            "detail": "A contract's meaning is interpreted using the context from when it was created, not when it's disputed."
        },
        {
            "name": "Decentralized Validation",
            "summary": "Multiple LLM providers prevent centralization.",
            "detail": "Claude, GPT, Gemini, Grok, and local models (Ollama, llama.cpp) all participate in validation."
        }
    ],
    "refusal_doctrine": {
        "will_not_automate": [
            "Consent - Only humans can consent to agreements",
            "Agreement - Only humans can agree to terms",
            "Authority - Only humans can grant or delegate power",
            "Value Finality - Only humans can declare economic closure",
            "Dispute Resolution - Only humans can judge right and wrong",
            "Moral Judgment - No automated ethics enforcement"
        ],
        "will_automate": [
            "Possibility Expansion - Surfacing interpretations",
            "Consistency Checking - Flagging clause conflicts",
            "Evidence Collection - Immutable timestamped records",
            "Provenance - Who said what, when",
            "Risk Surfacing - Identifying ambiguity",
            "Mediation Support - Structured negotiation aids"
        ]
    }
}


# =============================================================================
# Help System API
# =============================================================================

class GovernanceHelpSystem:
    """
    Provides access to NatLangChain's governance documentation.

    Makes the unique governance framework accessible without overwhelming users.
    """

    def __init__(self, docs_dir: Path | None = None):
        self.docs_dir = docs_dir or DOCS_DIR
        self.ncip_registry = NCIP_REGISTRY
        self.mp_registry = MP_REGISTRY
        self.core_concepts = CORE_CONCEPTS
        self.design_philosophy = DESIGN_PHILOSOPHY
        self.categories = NCIP_CATEGORIES

    def get_ncip_list(self) -> list[dict[str, Any]]:
        """Get list of all NCIPs with summaries."""
        return [ncip.to_dict() for ncip in self.ncip_registry.values()]

    def get_ncip(self, ncip_id: str) -> dict[str, Any] | None:
        """Get a specific NCIP by ID."""
        ncip = self.ncip_registry.get(ncip_id)
        return ncip.to_dict() if ncip else None

    def get_ncip_full_text(self, ncip_id: str) -> str | None:
        """Get full markdown content of an NCIP."""
        ncip = self.ncip_registry.get(ncip_id)
        if not ncip or not ncip.doc_file:
            return None

        doc_path = self.docs_dir / ncip.doc_file
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        return None

    def get_ncips_by_category(self) -> dict[str, Any]:
        """Get NCIPs organized by category."""
        result = {}
        for cat_id, cat_info in self.categories.items():
            ncips = [
                self.ncip_registry[ncip_id].to_dict()
                for ncip_id in cat_info["ncips"]
                if ncip_id in self.ncip_registry
            ]
            result[cat_id] = {
                "title": cat_info["title"],
                "description": cat_info["description"],
                "ncips": ncips
            }
        return result

    def get_mp_list(self) -> list[dict[str, Any]]:
        """Get list of all MP specs."""
        return [mp.to_dict() for mp in self.mp_registry.values()]

    def get_mp(self, mp_id: str) -> dict[str, Any] | None:
        """Get a specific MP by ID."""
        mp = self.mp_registry.get(mp_id)
        return mp.to_dict() if mp else None

    def get_mp_full_text(self, mp_id: str) -> str | None:
        """Get full markdown content of an MP spec."""
        mp = self.mp_registry.get(mp_id)
        if not mp or not mp.doc_file:
            return None

        doc_path = self.docs_dir / mp.doc_file
        if doc_path.exists():
            return doc_path.read_text(encoding="utf-8")
        return None

    def get_core_concepts(self) -> dict[str, dict[str, str]]:
        """Get all core concepts for quick reference."""
        return self.core_concepts

    def get_concept(self, concept_id: str) -> dict[str, str] | None:
        """Get a specific concept definition."""
        return self.core_concepts.get(concept_id)

    def get_design_philosophy(self) -> dict[str, Any]:
        """Get design philosophy overview."""
        return self.design_philosophy

    def search_governance(self, query: str) -> list[dict[str, Any]]:
        """Search across all governance docs."""
        query_lower = query.lower()
        results = []

        # Search NCIPs
        for ncip in self.ncip_registry.values():
            if (query_lower in ncip.title.lower() or
                query_lower in ncip.summary.lower() or
                any(query_lower in kc.lower() for kc in ncip.key_concepts)):
                results.append({
                    "type": "ncip",
                    "id": ncip.id,
                    "title": ncip.title,
                    "summary": ncip.summary,
                    "relevance": "high" if query_lower in ncip.title.lower() else "medium"
                })

        # Search MPs
        for mp in self.mp_registry.values():
            if (query_lower in mp.title.lower() or
                query_lower in mp.summary.lower()):
                results.append({
                    "type": "mp",
                    "id": mp.id,
                    "title": mp.title,
                    "summary": mp.summary,
                    "relevance": "high" if query_lower in mp.title.lower() else "medium"
                })

        # Search concepts
        for concept_id, concept in self.core_concepts.items():
            if (query_lower in concept["term"].lower() or
                query_lower in concept["definition"].lower()):
                results.append({
                    "type": "concept",
                    "id": concept_id,
                    "title": concept["term"],
                    "summary": concept["definition"],
                    "relevance": "high" if query_lower in concept["term"].lower() else "medium"
                })

        # Sort by relevance
        results.sort(key=lambda x: 0 if x["relevance"] == "high" else 1)
        return results

    def get_help_overview(self) -> dict[str, Any]:
        """Get overview for help landing page."""
        return {
            "title": "NatLangChain Governance",
            "subtitle": "Comprehensive governance framework for semantic contracts",
            "stats": {
                "ncip_count": len(self.ncip_registry),
                "mp_count": len(self.mp_registry),
                "concept_count": len(self.core_concepts),
                "category_count": len(self.categories)
            },
            "highlights": [
                {
                    "title": "15 NCIPs",
                    "description": "NatLangChain Improvement Proposals define protocol governance"
                },
                {
                    "title": "4 Mediator Protocols",
                    "description": "Specifications for mediation, disputes, and settlement"
                },
                {
                    "title": "Human-Centered",
                    "description": "Automation assists, humans decide"
                },
                {
                    "title": "Semantic Validation",
                    "description": "Multi-LLM consensus for meaning, not just syntax"
                }
            ],
            "categories": [
                {"id": cat_id, **cat_info, "ncip_count": len(cat_info["ncips"])}
                for cat_id, cat_info in self.categories.items()
            ]
        }


# =============================================================================
# Module-level singleton
# =============================================================================

_help_system: GovernanceHelpSystem | None = None


def get_help_system() -> GovernanceHelpSystem:
    """Get the governance help system singleton."""
    global _help_system
    if _help_system is None:
        _help_system = GovernanceHelpSystem()
    return _help_system


def reset_help_system() -> None:
    """Reset the help system (for testing)."""
    global _help_system
    _help_system = None

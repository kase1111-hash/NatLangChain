NCIP-003: Multilingual Semantic Alignment & Drift

Status: Canonical
Type: Protocol Semantics / Internationalization
Version: 1.0
Created: December 22, 2025
Applies To:

Prose Contracts

Validators

LLM Agents

Mediators

Registry maintainers

Depends On:

NatLangChain Technical Specification v3.0

NCIP-001: Canonical Term Registry

NCIP-002: Semantic Drift Thresholds & Validator Responses

1. Purpose

This NCIP defines how multiple natural languages are supported in NatLangChain without semantic divergence.

It establishes:

A single Canonical Semantic Anchor Language

Rules for translation, alignment, and verification

How cross-language semantic drift is measured

Mandatory validator behavior when multilingual meaning diverges

2. Canonical Semantic Anchor Language (CSAL)
2.1 Definition (Normative)

NatLangChain designates one anchor language per Prose Contract as the Canonical Semantic Anchor Language (CSAL).

The CSAL is the source of truth for meaning

All translations are derived, never peer-authoritative

Drift is always computed relative to the CSAL

Default CSAL: English (en)
(Other languages MAY be used if explicitly declared.)

2.2 CSAL Declaration (Required)

Every multilingual Prose Contract MUST declare:

Canonical Semantic Anchor Language: <ISO 639-1 code>


Example:

Canonical Semantic Anchor Language: en


If omitted:

Validators MUST assume en

Emit a D1 warning

3. Language Roles (Normative)

Each language instance MUST declare exactly one role:

Role	Meaning
anchor	Canonical meaning source
aligned	Verified semantic equivalent
informational	Human convenience only (non-executable)

Only anchor and aligned languages MAY influence execution.

4. Translation & Alignment Rules
4.1 Alignment Requirement

For each aligned language:

Meaning MUST be semantically equivalent to the CSAL

Lexical differences are allowed

Added or missing obligations are NOT allowed

4.2 Prohibited Behaviors

An aligned translation MUST NOT:

Introduce new constraints

Remove obligations

Narrow or broaden scope

Replace canonical terms with non-registry concepts

Violations trigger drift scoring.

5. Multilingual Drift Measurement
5.1 Cross-Language Drift Score

For each aligned language Lᵢ:

drift(Lᵢ) = semantic_distance(anchor, Lᵢ)


Drift scores use the same thresholds defined in NCIP-002.

5.2 Aggregation Rule (Normative)

Drift is computed per clause and per term

The maximum drift score governs validator response

Drift in any aligned language applies to the whole contract

6. Mandatory Validator Responses (Multilingual)

Validator responses map directly to NCIP-002:

Drift Level	Response
D0–D1	Accept translation
D2	Pause execution, request clarification
D3	Require human ratification
D4	Reject translation, escalate dispute

Validators MUST report:

Language pair

Affected clauses

Drift score

Canonical terms involved

7. Canonical Term Registry Interaction
7.1 Term Anchoring Rule

All core terms from NCIP-001:

MUST remain semantically identical across languages

MAY be translated lexically

MUST map to the same registry ID

Example:

Prose Contract (en)

Contrato en Prosa (es)
→ Same canonical term ID

7.2 Registry Extension (Multilingual Labels)

The registry MAY include:

Language-specific labels

Explanatory glosses

Usage notes

These do not change meaning.

8. Human Ratification in Multilingual Contexts

Human ratification MUST:

Reference the CSAL explicitly

Acknowledge reviewed aligned languages

Bind all translations to the anchor meaning

Example:

“I ratify the English (anchor) meaning and accept aligned translations as equivalent.”

9. Informational Languages (Non-Executable)

Languages marked informational:

Are excluded from drift computation

Do not affect execution

Are ignored by validators beyond format checks

They exist purely for human accessibility.

10. Machine-Readable Multilingual Alignment Spec (YAML)

Validators MUST support this structure.

multilingual_semantics:
  version: 1.0

  canonical_anchor_language: en

  languages:
    - code: en
      role: anchor
      drift_tolerance: 0.25

    - code: es
      role: aligned
      drift_tolerance: 0.25

    - code: fr
      role: aligned
      drift_tolerance: 0.25

    - code: ja
      role: informational

  alignment_rules:
    core_terms:
      must_map_to_registry: true
      allow_lexical_variation: true
      allow_semantic_variation: false

    obligations:
      allow_addition: false
      allow_removal: false
      allow_scope_change: false

  validator_actions:
    on_drift:
      use_ncip_002_thresholds: true
      log_language_pair: true
      require_anchor_reference: true

11. Security & Attack Considerations
Prevented Attacks

Translation laundering (softening obligations)

Language asymmetry exploits

Jurisdictional reinterpretation via translation

Remaining Risks

Cultural nuance misalignment (handled via D2/D3)

Poor-quality translation models (mitigated by human ratification)

12. Final Statement

NCIP-003 guarantees that:

NatLangChain is multilingual, not multi-meaning

One meaning exists, many expressions allowed

Validators behave identically across languages

Humans always know which language binds

Language diversity is a feature.
Semantic plurality is not.

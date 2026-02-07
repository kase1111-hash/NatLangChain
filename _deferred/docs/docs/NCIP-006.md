NCIP-006: Jurisdictional Interpretation & Legal Bridging

Status: Canonical
Type: Legal Interface / Governance
Version: 1.0
Created: December 22, 2025
Applies To:

Prose Contracts with legal or economic effect

Validators

Mediators

Legal interfaces and compliance modules

Depends On:

NatLangChain Technical Specification v3.0

NCIP-001: Canonical Term Registry

NCIP-002: Semantic Drift Thresholds & Validator Responses

NCIP-003: Multilingual Semantic Alignment & Drift

NCIP-004: Proof of Understanding (PoU)

NCIP-005: Dispute Escalation, Cooling Periods & Semantic Locking

1. Purpose

This NCIP defines how NatLangChain interfaces with external legal jurisdictions while preserving:

Canonical meaning

Temporal Fixity

Semantic Lock integrity

Proof of Understanding guarantees

It explicitly prevents:

Courts or statutes from retroactively redefining protocol semantics

Jurisdiction shopping via translation or reinterpretation

Silent legal overrides of canonical terms

2. Core Principle (Normative)

Law constrains enforcement, not meaning.

NatLangChain semantics are:

Defined internally

Fixed at ratification time (T₀)

Locked during disputes (Tₗ)

External legal systems may:

Affect remedies

Affect enforceability

Affect procedure

They may not redefine meaning.

3. Jurisdiction Declaration
3.1 Required Jurisdiction Clause

Any Prose Contract with legal or economic impact MUST declare:

Governing Jurisdiction(s): <ISO 3166-1 country code(s)>


Example:

Governing Jurisdiction(s): US-CA, DE


If omitted:

Validators emit D2

Execution pauses until declared

4. Jurisdiction Roles

Each declared jurisdiction has exactly one role:

Role	Description
enforcement	Where remedies may be sought
interpretive	Where courts may interpret facts (not semantics)
procedural	Governs process only

A jurisdiction MUST NOT be granted semantic authority.

5. Legal Bridging Model
5.1 Semantic–Legal Boundary (Normative)

NatLangChain semantics determine what was agreed

Jurisdiction determines what can be enforced

Mapping is one-way:

Prose Meaning → Legal Claim


Reverse mapping is prohibited.

6. Legal Translation Artifacts (LTAs)
6.1 Definition

A Legal Translation Artifact (LTA) is a jurisdiction-specific rendering of a Prose Contract into legal prose.

LTAs:

Are derived

Are non-authoritative

Must reference canonical semantics

6.2 LTA Constraints

An LTA MUST:

Cite Prose Contract ID

Reference Canonical Term Registry IDs

Include Temporal Fixity timestamp

Explicitly disclaim semantic authority

7. Validator Behavior (Normative)

Validators MUST:

Reject LTAs that introduce new obligations

Reject LTAs that narrow or broaden scope

Detect semantic drift between Prose Contract and LTA

Treat LTA drift ≥ D3 as invalid

8. Courts & External Findings
8.1 Handling Court Rulings

If a court ruling conflicts with canonical semantics:

Semantic Lock remains intact

Meaning does not change

Only enforcement outcome is applied

Example:

Court voids payment → execution halts

Court redefines “uptime” → ignored

9. Proof of Understanding in Legal Contexts

Verified PoUs are admissible evidence of comprehension

Lack of PoU weakens claims of mutual understanding

Post-dispute PoUs are inadmissible

10. Cross-Jurisdiction Conflicts

If jurisdictions conflict:

Semantic Lock applies

Most restrictive enforcement outcome applies

Meaning remains unchanged

Parties may terminate or amend via new Prose Contract

11. Machine-Readable Jurisdiction Bridge (YAML)

Validators MUST support this structure.

jurisdictional_bridge:
  version: 1.0

  governing_jurisdictions:
    - code: US-CA
      role: enforcement

    - code: DE
      role: procedural

  semantic_authority:
    source: natlangchain
    allow_external_override: false

  legal_translation_artifacts:
    allowed: true
    authoritative: false
    require_reference:
      - prose_contract_id
      - registry_version
      - temporal_fixity

  validator_rules:
    reject_semantic_override: true
    max_allowed_drift: 0.25
    escalate_on_violation: true

12. Security & Abuse Resistance
Prevented:

Jurisdiction shopping

Legal reinterpretation attacks

Translation laundering via legal prose

Retroactive meaning changes

Remaining Risks:

Conflicting sovereign enforcement (handled procedurally)

Regulatory bans (out of scope)

13. Final Statement

NCIP-006 ensures that:

NatLangChain can operate in the real world

Courts can enforce without redefining

Meaning remains stable across borders

Law and language are cleanly separated

Law may decide what happens.
NatLangChain decides what was meant.

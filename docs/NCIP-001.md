NCIP-001: Canonical Term Registry

Status: Canonical
Type: Governance / Registry
Version: 1.0
Created: December 22, 2025
Applies To: All NatLangChain repositories, mediators, validators, and agents
Depends On:

NatLangChain Technical Specification v3.0

NCIP-000: Terminology & Semantics Governance

1. Purpose

This NCIP defines a machine-readable registry of canonical terms used across the NatLangChain ecosystem.

The registry exists to:

Eliminate ambiguity in protocol-critical language

Enable automated validation and drift detection

Provide a single source of semantic truth for humans and machines

Support Proof of Understanding and mediator enforcement

The registry is normative.

2. Authority & Precedence

The NatLangChain Technical Specification defines core concepts

NCIP-000 defines how terms may evolve

This registry encodes those terms in enforceable form

In the event of conflict:

Human-readable specifications prevail

The registry MUST be updated to reflect the authoritative prose

3. Registry Format (Normative)

The Canonical Term Registry SHALL be expressed as YAML and versioned.

Required properties:

Deterministic keys

Explicit semantic class

Human-readable definition

Governance constraints

Machine-consumable metadata

4. Term Classes

Each term MUST declare exactly one class:

core — immutable, consensus-critical

protocol-bound — governed by a Mediator Protocol (MP)

extension — optional or experimental

5. Semantic Constraints (Enforced)

For every term:

Definitions may be clarified, never broadened

Synonyms MAY exist, but are non-canonical

Deprecated terms MUST remain resolvable

Every change MUST be traceable via NCIP reference

6. Mandatory Fields

Each registry entry MUST include:

Field	Description
term	Canonical string
class	core / protocol-bound / extension
definition	Normative human-readable meaning
introduced_in	Spec or NCIP
governance	Change rules
synonyms	Optional, non-authoritative
notes	Optional clarifications
7. Enforcement & Usage
7.1 Validators

Validators MAY:

Reject unknown canonical terms

Warn on deprecated or overloaded usage

Flag semantic collisions

7.2 LLM Agents

Agents MUST:

Prefer canonical terms in output

Map synonyms internally

Log uncertainty when terms are missing or ambiguous

7.3 Semantic Drift Detection

The registry is the baseline for drift comparison across:

Specs

Code

NCIPs

Derived schemas

8. Amendment Process

Changes to this registry require:

A new NCIP referencing NCIP-001

Explicit diff of semantic impact

Backward compatibility analysis

Human ratification

9. Canonical Term Registry (YAML)

Below is the initial authoritative registry.

registry_version: 1.0
last_updated: 2025-12-22
authority:
  specification: "NatLangChain Technical Specification v3.0"
  governance: "NCIP-000"

terms:

  - term: Intent
    class: core
    definition: >
      A human-authored expression of desired outcome or commitment,
      recorded as prose and treated as the primary semantic input
      to the NatLangChain protocol.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
      rule: "Clarification only; no redefinition"
    synonyms:
      - intention
      - user intent
    notes: >
      Intent is not executable by itself; execution is always derived.

  - term: Entry
    class: core
    definition: >
      A discrete, timestamped record containing prose, metadata,
      and signatures within the NatLangChain system.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - record
    notes: >
      Entries form the canonical audit trail.

  - term: Agreement
    class: core
    definition: >
      A mutually ratified Intent or set of Intents establishing
      shared understanding and obligations between parties.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - contract
    notes: >
      Agreement does not imply automation or smart contract execution.

  - term: Ratification
    class: core
    definition: >
      An explicit act of consent confirming understanding and acceptance
      of an Intent or Agreement.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - approval
      - acceptance

  - term: Proof of Understanding
    class: core
    definition: >
      Evidence that a party has demonstrably comprehended the meaning
      and implications of an Intent or Agreement.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - PoU
    notes: >
      Proof of Understanding is semantic, not cryptographic alone.

  - term: Semantic Drift
    class: core
    definition: >
      The divergence between original intended meaning and subsequent
      interpretation, usage, or derived execution.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - meaning drift

  - term: Temporal Fixity
    class: core
    definition: >
      The binding of meaning to a specific point in time, ensuring
      interpretations are evaluated against contemporaneous context.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false
    synonyms:
      - T0

  - term: Mediator
    class: core
    definition: >
      A human or authorized entity responsible for interpretation,
      dispute resolution, or enforcement within defined bounds.
    introduced_in: "Technical Specification v3.0"
    governance:
      mutable: false

  - term: Dispute
    class: protocol-bound
    governed_by: "MP-03"
    definition: >
      A formally raised challenge asserting misinterpretation,
      non-compliance, or unresolved ambiguity in an Agreement.
    introduced_in: "MP-03"
    governance:
      mutable: restricted
      requires_nc_ip: true
    synonyms:
      - challenge

  - term: Settlement
    class: protocol-bound
    governed_by: "MP-05"
    definition: >
      The resolution of an Agreement or Dispute resulting in
      final obligations, compensation, or closure.
    introduced_in: "MP-05"
    governance:
      mutable: restricted
    synonyms:
      - resolution

  - term: Extension Term
    class: extension
    definition: >
      A non-core term introduced by a module or experimental feature,
      explicitly scoped and non-consensus-critical.
    introduced_in: "NCIP-001"
    governance:
      mutable: true
    notes: >
      Extension terms must never collide with core terms.

10. Final Statement

This registry makes language enforceable without freezing meaning.

Humans remain the source of truth.
Machines gain clarity.
Ambiguity becomes governable.

NCIP-000: Terminology & Semantics Governance

Status: Canonical
Type: Governance / Meta-Specification
Version: 1.0
Created: December 22, 2025
Applies To: All NatLangChain repositories and dependent systems
Author: Kase Branham, NatLangChain Originator
License: CC BY-SA 4.0
Supersedes: None (foundational)

1. Purpose

This NCIP establishes authoritative governance over terminology and semantics within the NatLangChain ecosystem.

NatLangChain is a prose-first, intent-native protocol. Because human language is the canonical substrate, terminology is not cosmetic — it directly affects validation, consensus, auditability, dispute resolution, and legal defensibility.

Uncontrolled semantic drift would fracture interoperability and undermine Proof of Understanding.
This document exists to prevent that outcome.

2. Source of Authority
2.1 Canonical Reference Specification

All terminology defined or constrained by this NCIP derives its authority from:

NatLangChain Technical Specification v3.0
Last Updated: January 1, 2026
Maintained By: kase1111-hash

In the event of conflict:

The Technical Specification prevails

This NCIP governs how terms evolve, not what the system is

3. Scope

This NCIP governs:

Core protocol terminology

Cross-repository shared semantics

Meanings used by validators, mediators, and LLMs

Human-readable terms that carry protocol meaning

This NCIP does not govern:

UI labels (except where mapped to canonical terms)

Branding or marketing language

Natural-language prose inside individual contracts, except where explicitly defined

4. Core Principles
4.1 Prose Is Canonical

Natural language entries are the primary record of truth.
All code, schemas, and execution artifacts are derived.

4.2 Semantics Are Consensus-Critical

A term’s meaning must be:

Stable

Auditable

Interpretable by humans and machines

4.3 No Inferred Meaning

Meaning is never inferred from context alone.
If a term matters, it must be defined.

5. Terminology Classes
5.1 Immutable Core Terms

Terms defined in the Technical Specification and used by protocol logic are immutable.

Examples (non-exhaustive):

Intent

Entry

Agreement

Ratification

Settlement

Dispute

Proof of Understanding

Semantic Drift

Temporal Fixity (T0)

Mediator

Effort Receipt

Licensing

Delegation

Rule:
An immutable term’s meaning may be clarified but never broadened, redefined, or repurposed.

5.2 Protocol-Bound Terms

Terms bound to a Mediator Protocol (MP-01…MP-05) inherit governance from that MP.

Example:

“Settlement” is governed by MP-05

“Dispute” is governed by MP-03

Changes to these terms require:

An NCIP referencing the relevant MP

Explicit backward-compatibility analysis

5.3 Extension Terms

New terms introduced by:

Modules

Extensions

Experimental features

Must:

Be explicitly scoped

Avoid collision with existing terms

Declare whether they are advisory, normative, or experimental

6. Semantic Stability Rule (Normative)

Once a term is ratified, its meaning may only be narrowed or clarified — never expanded.

If a new concept does not fit existing semantics:

Create a new term

Do not overload an existing one

This rule is enforceable by:

Semantic Drift Detection

Validator warnings

NCIP rejection

7. Language & Style Requirements
7.1 Human-Readable First

Canonical terms must be:

Understandable without protocol context

Free of acronyms unless unavoidable

Stable across legal, technical, and conversational use

7.2 No Synonym Proliferation

A single canonical term MUST exist per concept.

User-facing systems MAY map synonyms internally, but:

Only the canonical term is stored on-chain

Only the canonical term is used in specs

8. Enforcement Mechanisms
8.1 Validation Layer Integration

Validators MAY flag:

Ambiguous terminology

Deprecated or conflicting usage

Semantic overload attempts

8.2 Semantic Drift Detection

Existing drift detection mechanisms apply to:

Spec changes

Cross-repo schemas

NCIP proposals

8.3 NCIP Gatekeeping

Any proposal that:

Renames a core term

Reuses a term with altered semantics

Introduces ambiguous synonyms

MUST be rejected unless it also proposes a migration strategy and backward-compatibility guarantees.

9. Amendment Process

Changes to terminology governance require:

A new NCIP referencing NCIP-000

Explicit comparison against the Technical Specification

Semantic impact analysis

Human ratification (per MP-01)

No automated agent may unilaterally redefine terms.

10. Relationship to Automation Doctrine

In accordance with the Refusal Doctrine:

Meaning is not automated

Consent is not inferred

Authority is not delegated to LLMs

LLMs may assist with:

Clarification

Comparison

Drift detection

But never with final semantic authority.

11. Genesis Declaration

This NCIP is hereby declared the foundational semantic governance document of NatLangChain.

All future NCIPs, modules, validators, mediators, and agents are expected to comply.

12. Final Statement

NatLangChain does not seek to eliminate ambiguity.
It seeks to make ambiguity explicit, bounded, and governable.

Clear language is infrastructure.

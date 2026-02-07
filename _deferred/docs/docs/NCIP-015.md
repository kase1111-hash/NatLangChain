NCIP-015: Sunset Clauses, Archival Finality & Historical Semantics

Status: Canonical
Type: Temporal Governance / Semantic Preservation
Version: 1.0
Created: December 22, 2025
Applies To:

Prose Contracts

Licenses (MP-04)

Settlements (MP-05)

Validators

Mediators

Archivists / Legal Interfaces

Depends On:

NatLangChain Technical Specification v3.0

NCIP-001: Canonical Term Registry

NCIP-002: Semantic Drift Thresholds

NCIP-004: Proof of Understanding

NCIP-005: Semantic Locking

NCIP-006: Jurisdictional Bridging

NCIP-010–014 (Reputation, Amendments, Emergencies)

1. Purpose

This NCIP defines:

How agreements and meanings end

When records become historically immutable

How expired semantics are preserved without remaining operative

How NatLangChain prevents retroactive reinterpretation of the past

It draws a hard line between:

Active meaning

Expired meaning

Historical meaning

2. Core Principle (Normative)

Meaning may expire. History must not.

Sunset does not mean deletion.
Expiration does not mean reinterpretation.
Archival does not mean semantic drift.

3. Sunset Clauses
3.1 Definition

A Sunset Clause defines the conditions under which an entry’s operative force ends.

Sunsets MAY apply to:

Contracts

Licenses

Delegations

Obligations

Settlement rights

Sunsets MUST NOT:

Alter historical semantics

Delete or redact records

Enable reinterpretation

3.2 Sunset Trigger Types
Trigger Type	Description
time_based	Fixed datetime or duration
event_based	External or oracle-verified event
condition_fulfilled	Explicit semantic completion
exhaustion	Finite-use depletion
revocation	Explicit revocation under allowed terms
constitutional	Triggered by NCIP-014 amendment
3.3 Required Declaration (Normative)

All sunset clauses MUST be explicit.

Example:

This license sunsets 24 months after ratification or upon acquisition of Company X, whichever occurs first.


Implicit sunsets are invalid.

4. Sunset State Machine

Each entry transitions through immutable states:

DRAFT → RATIFIED → ACTIVE → SUNSET_PENDING → SUNSET → ARCHIVED


Rules:

SUNSET_PENDING allows notice & cooling

SUNSET ends enforceability

ARCHIVED locks semantics permanently

No backward transitions are permitted.

5. Archival Finality
5.1 Definition

Archival Finality is the irreversible state where:

Semantics are frozen forever

Drift detection is disabled

No reinterpretation is permitted

Entry is admissible as historical fact only

5.2 Archival Triggers

An entry MUST be archived when:

Sunset completes

Final settlement declared

Constitutional sunset applies

20-year default horizon expires (if unspecified)

6. Historical Semantics
6.1 Canonical Rule

Historical entries retain their original meaning as understood at T₀, regardless of:

Later amendments

Term registry evolution

Legal reclassification

Cultural shifts

Language drift

6.2 Interpretation Guardrail

Validators MUST reject:

Attempts to “reinterpret” archived entries

Applying new definitions retroactively

Using historical text as active precedent unless explicitly referenced

7. Temporal Context Binding

All archived entries are bound to:

Registry version at ratification

Language variant used

Jurisdiction context

Proofs of Understanding

Validator consensus snapshot

This bundle is immutable.

8. Validator Behavior (Normative)

Validators MUST:

Enforce sunset triggers exactly as declared

Transition state deterministically

Disable semantic drift checks post-archive

Reject new obligations referencing archived semantics unless restated

9. Mediator Constraints

Mediators:

MAY cite archived entries as context

MUST NOT propose actions based on expired authority

MUST restate any historical semantics they wish to reactivate

History can inform.
It cannot compel.

10. Machine-Readable Sunset & Archive Schema (YAML)
sunset_and_archive:
  version: 1.0

  sunset:
    type: time_based
    trigger:
      datetime: "2030-01-01T00:00:00Z"
    notice_period_days: 30

  post_sunset_state:
    enforceable: false
    negotiable: false
    referential_only: true

  archival:
    auto_archive: true
    archive_after_days: 90
    preserve:
      - prose_content
      - registry_version
      - language
      - jurisdiction
      - proof_of_understanding
      - validator_snapshot

  validator_rules:
    reject_reactivation_without_restatement: true
    disable_drift_detection: true

11. Force Majeure & Emergency Interaction

If NCIP-013 emergency overrides occur:

Sunset timers MAY pause

Semantics MUST remain unchanged

Archive eligibility resumes post-emergency

Emergency never rewrites history.

12. Legal & Evidentiary Standing

Archived entries:

Are admissible as historical evidence

Demonstrate intent at time of agreement

Do not imply current obligation

Cannot be “updated” to reflect modern law

13. Abuse Resistance
Prevented:

Retroactive contract rewriting

Semantic laundering via amendments

Zombie obligations

Eternal licenses by omission

Allowed:

Explicit restatement

New agreements informed by history

Scholarly and legal reference

14. Default Sunset Policy

If no sunset is specified:

Entry Type	Default
Contracts	20 years
Licenses	10 years
Delegations	2 years
Standing Intents	1 year
Disputes	On resolution
Settlements	Immediate archive

Defaults MAY be overridden explicitly.

15. Final Statement (Protocol-Level)

NCIP-015 guarantees that NatLangChain:

Has a memory that cannot be altered

Allows agreements to end cleanly

Prevents history from being weaponized

Preserves meaning without eternal force

Meaning lives.
Meaning ends.
History remains.

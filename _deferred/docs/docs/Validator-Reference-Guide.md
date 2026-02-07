Validator Reference Implementation Guide

NatLangChain Canonical Validator Architecture

Status: Canonical
Applies To:

Entry Validators

Contract Validators

Dispute Validators

Mediator & Reputation Weighting

Multilingual & Legal Interfaces

Depends On:
NCIP-000 → NCIP-015
NatLangChain Technical Specification v3.0

1. Validator Role (Non-Negotiable)

A validator answers exactly one question:

“Is this entry semantically valid, stable, and admissible under the protocol?”

Validators:

❌ Do NOT decide outcomes

❌ Do NOT enforce settlements

❌ Do NOT infer consent

✅ Do assess meaning, coherence, drift, and compliance

2. Validator Architecture Overview
┌─────────────────────────────┐
│ Incoming Entry / Action     │
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Structural Validation       │  (Schema, required fields)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Canonical Term Resolution   │  (NCIP-001)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Proof of Understanding      │  (NCIP-004)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Semantic Drift Analysis     │  (NCIP-002 / 003)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Jurisdiction & Compliance   │  (NCIP-006 / 009)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Contextual Constraints      │  (Dispute locks, cooling)
│                              (NCIP-005 / 013)
└──────────────┬──────────────┘
               ▼
┌─────────────────────────────┐
│ Weighted Consensus Output   │  (NCIP-007 / 011)
└─────────────────────────────┘

3. Core Validation Pipeline (Step-by-Step)
3.1 Structural Validation (Hard Fail)

Reject immediately if:

Missing content, author, intent

Invalid schema (Common Schema Definitions)

Timestamp malformed

Metadata contradicts intent (e.g., is_contract=false with contract syntax)

➡️ Failure Class: INVALID_STRUCTURAL

3.2 Canonical Term Resolution (NCIP-001)

Process:

Tokenize prose

Resolve registered canonical terms

Flag unregistered but repeated terms

Outcomes:

RESOLVED

UNREGISTERED_TERM_WARNING

TERM_CONFLICT_ERROR

➡️ Validators MUST NOT invent definitions.

3.3 Proof of Understanding (NCIP-004)

Validator MUST generate:

Neutral paraphrase

Obligation extraction

Uncertainty acknowledgment

Reject if:

Paraphrase introduces obligations

Omits constraints

Collapses uncertainty

➡️ Output stored immutably.

3.4 Semantic Drift Evaluation (NCIP-002 / 003)

Compute drift against:

Prior contract versions

Multilingual anchors (if applicable)

Locked semantic baselines

Drift bands:

D0–D1 → auto-accept

D2 → warn + human review

D3 → escalation required

D4 → reject

➡️ Drift ≥ D3 freezes affected entries.

3.5 Jurisdiction & Regulatory Check (NCIP-006 / 009)

Verify:

Governing jurisdiction declared (if required)

No semantic authority delegated externally

Regulatory modules referenced (if applicable)

Reject if:

Jurisdiction attempts semantic override

LTA contradicts canonical meaning

3.6 Contextual Constraints

Check:

Dispute locks

Cooling periods

Emergency override states

Sunset / archival state

Reject if:

Entry attempts mutation under semantic lock

Violates cooling window

Bypasses ratification UX constraints

4. Consensus & Weighting (NCIP-007 / 011)

Validators output:

validation_result:
  status: valid | invalid | escalated
  confidence: 0.0 - 1.0
  drift_score: 0.00
  notes: "Concise explanation"


Final decision uses weighted aggregation:

Validator trust score

Model diversity bonus

Historical accuracy

Mediator coupling (when applicable)

➡️ No single validator may unilaterally finalize.

5. Validator Trust Scoring (Summary)

Validators accrue reputation via:

Agreement with post-dispute outcomes

Drift accuracy

False positive / false negative rates

Appeal reversals

Trust decay applies automatically.

6. Appeals & Precedent Handling (NCIP-008)

Validators MUST:

Reference precedent hashes

Explain deviations explicitly

Never retroactively alter precedent meaning

Precedent influences confidence, not authority.

7. Mediator Interaction Rules

Validators:

Evaluate mediator proposals

Score semantic fidelity

NEVER optimize for settlement speed or value

Mediators with repeated validator conflict are penalized.

8. Emergency & Force Majeure Handling (NCIP-013)

During emergency state:

Validators may accept fallback semantics

Must annotate TEMPORARY_OVERRIDE

Require post-event reconciliation

9. Archival & Sunset Validation (NCIP-015)

Once archived:

Meaning is immutable

Validators operate read-only

Historical semantics preserved even if obsolete

10. Minimal Validator Implementation Checklist

✅ Schema validation
✅ Canonical term resolver
✅ PoU generator
✅ Drift scoring engine
✅ Lock & cooling enforcement
✅ Weighted consensus output
✅ Immutable audit logs

11. Explicit Non-Responsibilities

Validators MUST NOT:

Decide disputes

Enforce payment

Interpret moral intent

Infer consent

Optimize outcomes

12. Final Principle

Validators protect meaning, not power.

They are the immune system—not the brain, not the judge, not the executioner.

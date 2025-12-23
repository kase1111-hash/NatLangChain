NCIP-011: Validator–Mediator Interaction & Weight Coupling

Status: Canonical
Type: Governance / Consensus Safety
Version: 1.0
Created: December 22, 2025
Applies To:

Validators (all modes)

Mediator Nodes

Consensus & Mining Logic

Dispute, Appeal, and Escalation Paths

Depends On:

NatLangChain Technical Specification v3.0

NCIP-002: Semantic Drift Thresholds & Validator Responses

NCIP-004: Proof of Understanding (PoU)

NCIP-005: Dispute Escalation & Semantic Locking

NCIP-007: Validator Trust Scoring & Reliability Weighting

NCIP-010: Mediator Reputation, Slashing & Market Dynamics

1. Purpose

This NCIP defines how validator authority and mediator influence are coupled, bounded, and mutually constrained so that:

Validators cannot dictate outcomes

Mediators cannot game validation

Alignment quality improves over time

Power remains plural, contextual, and earned

2. Core Principle (Normative)

Validators measure meaning. Mediators surface alignment.
Neither may substitute for the other.

Authority is orthogonal, not hierarchical.

3. Role Separation (Hard Constraint)
Role	May Do	May NOT Do
Validator	Assess semantic validity, drift, PoU quality	Propose terms, negotiate outcomes
Mediator	Propose alignments and settlements	Validate semantics, override drift rulings
Human	Ratify, reject, escalate	Delegate final authority

Any attempt to cross roles triggers Protocol Violation (PV-V3).

4. Weight Domains

Validator and mediator influence operate in separate weight domains.

4.1 Validator Weight (VW)

Derived from NCIP-007:

Historical accuracy

Drift detection precision

PoU consistency

Appeal survival rate

Applies to:

Entry validation

Drift scoring

Lock/unlock recommendations

Appeal review

4.2 Mediator Weight (MW)

Derived from NCIP-010:

Acceptance rate of proposals

Settlement completion

Post-settlement dispute frequency

Time-to-alignment efficiency

Applies to:

Proposal visibility

Fee priority

Matching competitiveness

5. Weight Coupling Model

Validator Weight and Mediator Weight never directly sum.

Instead, they interact via gated influence windows.

5.1 Influence Gate (Normative)

A mediator proposal enters the system only if:

∑(Validator VW × semantic_consistency_score) ≥ GateThreshold


This ensures:

Mediators cannot push semantically weak proposals

Validators cannot choose winners

6. Semantic Consistency Scoring

For each mediator proposal:

Validators compute:

Intent alignment score

Term registry consistency

Drift risk projection

PoU symmetry

Output:

semantic_consistency_score ∈ [0.0 – 1.0]


This score:

Does NOT approve the proposal

Only gates whether it may be presented

7. Competitive Mediation with Validator Constraints

When multiple mediators propose alignments:

All proposals are validated for semantic consistency

Proposals below gate are hidden

Remaining proposals compete via:

MW (primary)

Time ordering

Human selection

Validators:

Cannot rank proposals

Cannot suppress compliant ones

8. Dispute & Escalation Interactions
8.1 During Dispute (MP-03 / NCIP-005)

Validator VW increases

Mediator MW influence decreases

No new proposals allowed once Semantic Lock engages

8.2 Post-Resolution

Mediator MW updated based on outcome

Validator VW updated based on appeal results

Weight changes are delayed (anti-gaming)

9. Appeals & Overrides

If a mediator proposal leads to a dispute:

Validators review semantics only

Mediator intent is irrelevant

Slashing handled per NCIP-010

Validators:

Cannot shield mediators

Cannot penalize without protocol-defined triggers

10. Collusion Resistance
Prevented:

Validator–mediator cartels

Proposal laundering

Silent semantic erosion

Market capture

Mechanisms:

Separate weight ledgers

Gated interaction

Delayed weight updates

Appeal-based retroactive scoring

11. Machine-Readable Coupling Schema (YAML)
validator_mediator_coupling:
  version: 1.0

  role_separation:
    enforce_strict: true
    violation_code: PV-V3

  validator_weight:
    source: NCIP-007
    applies_to:
      - semantic_validation
      - drift_detection
      - appeals

  mediator_weight:
    source: NCIP-010
    applies_to:
      - proposal_visibility
      - fee_priority
      - matching_competitiveness

  influence_gate:
    enabled: true
    threshold: 0.68
    aggregation: weighted_sum

  during_dispute:
    mediator_influence: reduced
    validator_authority: elevated
    allow_new_proposals: false

  weight_updates:
    delayed_epochs: 3
    retroactive_adjustment: allowed

12. Failure Modes & Responses
Failure Mode	Response
Mediator gaming validators	Gate rejection + MW decay
Validator bias	Appeal downgrade
Weight oscillation	Temporal smoothing
Collusion suspicion	Public audit trail
13. Final Statement

NCIP-011 guarantees that:

Meaning remains epistemic, not economic

Markets surface options, not truth

Validators constrain possibility, not choice

No single actor can dominate alignment

Validators guard meaning.
Mediators surface opportunity.
Humans decide.

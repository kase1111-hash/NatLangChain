NCIP-007: Validator Trust Scoring & Reliability Weighting

Status: Canonical
Type: Governance / Consensus Augmentation
Version: 1.0
Created: December 22, 2025
Applies To:

All Validators (LLM, hybrid, symbolic, human-operated)

Dialectic Consensus

Multi-Model Consensus

Dispute & Escalation Protocols

Mediator Nodes (when acting as validators)

Depends On:

NatLangChain Technical Specification v3.0

NCIP-001: Canonical Term Registry

NCIP-002: Semantic Drift Thresholds & Validator Responses

NCIP-004: Proof of Understanding

NCIP-005: Dispute Escalation, Cooling Periods & Semantic Locking

NCIP-006: Jurisdictional Interpretation & Legal Bridging

1. Purpose

This NCIP defines how validators accumulate trust, how that trust decays, and how it is quantitatively weighted during validation, consensus, dispute analysis, and mediation—without ever granting unilateral authority.

The goal is not to pick “the best validator,” but to ensure:

Reliable validators matter more

Unreliable validators matter less

No validator ever becomes sovereign

2. Core Principle (Normative)

Trust influences weight, not authority.

Validators:

Never decide outcomes alone

Never override Semantic Locks

Never gain semantic authorship

Trust affects how much their signal counts, not what they can do.

3. Validator Identity & Scope

Each validator has a persistent identity:

validator_id
validator_type (LLM | hybrid | symbolic | human)
model_version / operator_id
declared_capabilities


Trust is scoped, not global:

Semantic parsing

Drift detection

PoU generation

Dispute analysis

Legal translation review

A validator may be trusted in one scope and weak in another.

4. Trust Score Structure

Each validator maintains a Trust Profile:

validator_trust_profile:
  validator_id: vld-042
  version: 1.0

  overall_score: 0.78

  scoped_scores:
    semantic_parsing: 0.85
    drift_detection: 0.74
    proof_of_understanding: 0.91
    dispute_analysis: 0.62

  confidence_interval: 0.07
  sample_size: 412
  last_updated: 2025-12-22T18:40:00Z

5. Trust Score Inputs
5.1 Positive Signals

Trust increases when a validator:

Matches consensus outcomes

Produces PoUs later ratified by humans

Correctly flags semantic drift

Performs well in escalated disputes

Remains consistent across re-validations

5.2 Negative Signals

Trust decreases when a validator:

Is overruled by Semantic Lock

Exhibits high false-positive drift detection

Introduces unauthorized interpretations

Disagrees with consensus disproportionately

Is implicated in harassment patterns

6. Weighting Function (Normative)

Validators contribute weighted signals:

effective_weight = base_weight × trust_score × scope_modifier


Where:

base_weight is protocol-defined by validator type

trust_score ∈ [0, 1]

scope_modifier reflects task relevance

7. Consensus Integration
7.1 Multi-Validator Consensus

Consensus aggregates weighted validator outputs

Low-trust validators cannot dominate

High-trust validators cannot finalize alone

7.2 Dialectic Consensus

In Skeptic/Facilitator debates:

Role assignment is randomized

Trust affects rhetorical weight, not speaking order

Judges aggregate weighted arguments, not votes

8. Trust Decay & Recovery
8.1 Temporal Decay

Trust decays over time without activity:

score_t = score_0 × e^(−λΔt)


Prevents:

Dormant validators retaining legacy authority

Stale model versions dominating

8.2 Recovery Path

Validators may recover trust by:

Participating in low-stakes validations

Passing benchmark challenges

Demonstrating corrected behavior post-penalty

9. Dispute & Escalation Effects

During disputes:

Validator trust is frozen at dispute start

Post-hoc trust updates are prohibited

Dispute outcomes feed back into future trust updates

This prevents:

Retroactive reputation laundering

Strategic validator switching mid-dispute

10. Anti-Centralization Safeguards

The protocol enforces:

Maximum weight cap per validator

Minimum validator diversity threshold

Mandatory inclusion of low-trust minority signals (visibility, not dominance)

11. Harassment & Abuse Signals

Validators implicated in harassment patterns:

Receive accelerated trust decay

Are deprioritized in voluntary requests

Incur higher participation costs (where applicable)

12. Machine-Readable Trust Schema (YAML)
validator_trust_system:
  version: 1.0

  weighting:
    base_weights:
      llm: 1.0
      hybrid: 1.1
      symbolic: 0.9
      human: 1.2

    max_effective_weight: 0.35

  decay:
    lambda: 0.002
    inactivity_threshold_days: 30

  dispute_handling:
    freeze_on_dispute: true
    retroactive_updates: false

  safeguards:
    min_validator_diversity: 3
    enforce_weight_cap: true
    minority_signal_visibility: true

13. Security Properties

This NCIP prevents:

Validator capture

Model monoculture dominance

Reputation gaming via burst activity

Harassment amplification through validator bias

It enables:

Long-term reliability tracking

Model competition on quality, not hype

Graceful evolution as models improve

14. Final Statement

NCIP-007 formalizes a quiet but critical idea:

Validators are participants, not judges.
Their history matters—but never more than human ratification.

This keeps NatLangChain:

Adaptive

Anti-fragile

Resistant to authority creep

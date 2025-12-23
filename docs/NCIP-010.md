NCIP-010: Mediator Reputation, Slashing & Market Dynamics

Status: Canonical
Type: Economic Safety / Market Governance
Version: 1.0
Created: December 22, 2025
Applies To:

Mediator Nodes

Validator Weighting Engines

Treasury System

MP-01 Negotiation & Ratification

Escalation Forks

Depends On:

NatLangChain Technical Specification v3.0

MP-01: Negotiation & Ratification

NCIP-002: Semantic Drift Thresholds

NCIP-005: Dispute Escalation & Semantic Locking

NCIP-007: Validator Trust Scoring

NCIP-008: Semantic Appeals & Precedent

1. Purpose

This NCIP defines a market-based trust system for mediators that:

Rewards accurate, aligned mediation

Penalizes harmful, sloppy, or adversarial behavior

Prevents mediator capture or authority creep

Preserves the doctrine: mediators propose, humans decide

It explicitly avoids:

Subjective moderation

Human governance committees

Reputation based on popularity or volume alone

2. Core Principle (Normative)

Mediators earn influence only by being repeatedly correct, aligned, and non-coercive.

No mediator:

Has authority

Can finalize agreements

Can override parties or validators

Reputation only affects:

Proposal visibility

Validator weighting

Market selection probability

3. Mediator Identity & Bonding
3.1 Mediator Registration (Required)

All mediator nodes MUST:

Register a persistent mediator ID

Post a reputation bond (stake)

Declare supported domains (optional)

mediator_registration:
  mediator_id: mediator_node_alpha
  stake_bond: 50_000 NLC
  supported_domains:
    - software
    - licensing
    - employment
  models_used:
    - claude
    - gpt-5


Unbonded mediators MAY observe but MAY NOT submit proposals.

4. Reputation Score Components

Mediator reputation is a vector, not a scalar.

4.1 Reputation Dimensions
Component	Symbol	Description
Acceptance Rate	AR	% of proposals ratified by both parties
Semantic Accuracy	SA	Validator-measured drift score
Appeal Survival	AS	% surviving NCIP-008 appeals
Dispute Avoidance	DA	Low downstream dispute frequency
Coercion Signal	CS	Penalizes pressure tactics
Latency Discipline	LD	Responsiveness within protocol windows
5. Composite Trust Score (CTS)
5.1 Calculation (Illustrative)
CTS = w1·AR + w2·SA + w3·AS + w4·DA − w5·CS − w6·Late


Weights are protocol-defined and may evolve via NCIP-008 precedent.

CTS affects:

Proposal ranking

Validator attention

Eligibility for high-value disputes

6. Slashing Conditions (Normative)

Slashing is automatic, deterministic, and non-discretionary.

6.1 Slashable Offenses
Offense	Trigger	Penalty
Semantic Manipulation	Drift ≥ D4	10–30% bond
Repeated Invalid Proposals	3× rejected	5–15%
Coercive Framing	Validator flag + evidence	15%
Appeal Reversal	Successful NCIP-008 appeal	5–20%
Collusion Signals	Statistical correlation	Progressive

Slashed funds flow to:

Treasury

Affected parties (if applicable)

7. Cooldowns & Market Throttling

Post-slashing effects:

Temporary proposal cap reduction

Reduced visibility weighting

Mandatory cooldown periods

cooldown:
  reason: appeal_reversal
  duration_days: 14
  max_active_proposals: 1

8. Market Dynamics & Competition
8.1 Proposal Market Rules

Multiple mediators may propose simultaneously

Parties see proposals ranked by CTS (optionally anonymized)

Validators sample proposals proportional to trust

8.2 Anti-Capture Safeguards

Diminishing returns on volume

Diversity-weighted sampling

Randomized proposal ordering for low-stakes cases

9. Treasury & Subsidy Interaction

Mediator slashing contributes to:

Defensive dispute subsidies

Escalation bounty pools

Harassment-mitigation reserves

This creates a closed accountability loop:
Bad mediation funds protection against bad mediation.

10. Appeals & Precedent Interaction

Mediator behavior is appealable under NCIP-008

Successful appeals create negative precedent

Precedent updates future slashing thresholds

11. Machine-Readable Mediator Reputation Schema (YAML)
mediator_reputation:
  mediator_id: mediator_node_alpha

  bond:
    amount: 50000
    token: NLC
    locked: true

  scores:
    acceptance_rate: 0.81
    semantic_accuracy: 0.93
    appeal_survival: 0.88
    dispute_avoidance: 0.90
    coercion_signal: 0.05
    latency_discipline: 0.97

  composite_trust_score: 0.86

  penalties:
    active_cooldowns: []
    total_slashed: 7500

12. Security & Abuse Resistance
Prevented:

Mediator authority creep

Proposal spam

Coercive negotiation tactics

Reputation laundering

Remaining Risks:

Sophisticated collusion (mitigated statistically)

Model bias leakage (tracked via NCIP-007)

13. Canonical Boundary

This NCIP does not:

Grant mediators decision power

Allow reputation transfer

Permit off-chain reputation injection

Trust is earned only through on-chain behavior.

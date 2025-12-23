NCIP-002: Semantic Drift Thresholds & Validator Responses

Status: Canonical
Type: Protocol Safety / Validation
Version: 1.0
Created: December 22, 2025
Applies To:

Validators

Mediators

LLM Agents

Prose Contract compilers

Dispute resolution protocols

Depends On:

NatLangChain Technical Specification v3.0

NCIP-000: Terminology & Semantics Governance

NCIP-001: Canonical Term Registry

1. Purpose

This NCIP defines:

What Semantic Drift is in operational terms

How drift is measured

Thresholds at which drift becomes unsafe

Mandatory validator responses at each threshold

The goal is not to eliminate ambiguity, but to prevent silent meaning corruption.

2. Definitions (Normative)

Semantic Drift
A measurable divergence between:

the canonical meaning of a term or Intent at time T₀

and its current interpretation or derived execution

Drift Score
A normalized value ∈ [0.0, 1.0] representing semantic divergence.

0.0 → identical meaning

1.0 → unrelated or contradictory meaning

3. Drift Measurement Sources

Validators and agents MAY compute drift using one or more:

Canonical Term Registry (NCIP-001)

Historical Prose Contracts

Temporal Fixity context

LLM semantic similarity models

Structural mismatch in derived execution

Human annotations (Mediator input)

Important:
Measurement technique is implementation-defined; response is not.

4. Normative Drift Thresholds

Drift thresholds are absolute, not advisory.

Level	Drift Score	Classification	Description
D0	0.00 – 0.10	Stable	Meaning preserved
D1	0.10 – 0.25	Soft Drift	Minor lexical or stylistic variation
D2	0.25 – 0.45	Ambiguous Drift	Meaning overlap but execution risk
D3	0.45 – 0.70	Hard Drift	Substantive semantic deviation
D4	0.70 – 1.00	Semantic Break	Meaning no longer aligned
5. Mandatory Validator Responses
D0 — Stable

Required Action:

Proceed normally

No logging required

D1 — Soft Drift

Required Action:

Proceed

Emit non-fatal warning

Record occurrence for trend analysis

Example Message:

“Minor semantic variation detected; meaning remains aligned.”

D2 — Ambiguous Drift

Required Action:

Pause derived execution

Emit clarification request

Log to Uncertainty Log

Example Message:

“Intent meaning partially ambiguous; clarification required before execution.”

LLM Agents MUST:

Ask clarifying questions

Avoid speculative completion

D3 — Hard Drift

Required Action:

Reject derived execution

Require explicit human ratification

Flag for mediator review

Example Message:

“Semantic deviation exceeds safe threshold; human ratification required.”

D4 — Semantic Break

Required Action:

Reject

Invalidate current interpretation

Escalate to Dispute or NCIP process

Prevent auto-retry

Example Message:

“Semantic break detected; interpretation rejected as unsafe.”

6. Drift Aggregation Rules

Drift MUST be evaluated per:

Term

Clause

Whole Intent

The maximum drift score governs response.

Example:

Term A = 0.2

Clause B = 0.5
→ D3 applies

7. Temporal Fixity & Drift

Drift MUST be evaluated against T₀ context:

Canonical registry at time of ratification

Contemporaneous norms and definitions

Versioned specifications

Validators MUST NOT reinterpret older contracts using newer semantics without explicit upgrade.

8. Human Override Constraints

Humans MAY override:

D2 (Ambiguous Drift)

D3 (Hard Drift)

Humans MUST NOT override:

D4 (Semantic Break) without formal Dispute resolution

Overrides MUST:

Be explicit

Be logged

Bind future interpretations

9. Logging Requirements (Normative)

For D2 and above, logs MUST include:

Drift score

Affected terms

Source of divergence

Time (Tₙ)

Reference to NCIP-001 terms

Validator identity

10. Machine-Readable Threshold Definition (YAML)

This file MUST be referenced by validators.

semantic_drift:
  version: 1.0
  thresholds:
    D0:
      min: 0.00
      max: 0.10
      classification: stable
      action:
        proceed: true
        log: false

    D1:
      min: 0.10
      max: 0.25
      classification: soft_drift
      action:
        proceed: true
        warn: true
        log: true

    D2:
      min: 0.25
      max: 0.45
      classification: ambiguous_drift
      action:
        proceed: false
        request_clarification: true
        log_uncertainty: true

    D3:
      min: 0.45
      max: 0.70
      classification: hard_drift
      action:
        proceed: false
        require_human_ratification: true
        mediator_review: true
        log: true

    D4:
      min: 0.70
      max: 1.00
      classification: semantic_break
      action:
        proceed: false
        invalidate_interpretation: true
        escalate_dispute: true
        lock_autoretry: true
        log: true

11. Security Considerations

Drift inflation attacks are mitigated by:

Maximum-score aggregation

Mandatory human checkpoints

Drift suppression (lying low) is mitigated by:

Registry anchoring

Temporal Fixity enforcement

12. Final Statement

NCIP-002 ensures that:

Meaning does not silently mutate

Automation halts before damage occurs

Humans remain the ultimate arbiters of intent

Validators behave consistently across implementations

Ambiguity is tolerated.
Silent reinterpretation is not.
